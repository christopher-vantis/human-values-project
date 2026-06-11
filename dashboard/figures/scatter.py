"""Correlation figures (Correlations tab): heatmap + scatter with OLS fit.

All correlations are computed on the ESS Round 11 (2023) country
cross-section. Significance stars are based on Benjamini-Hochberg adjusted
q-values across the full predictor x dimension test family, so the heatmap
controls the false-discovery rate at 5 % instead of inflating Type-I error
over ~76 simultaneous tests.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

import theme
from data_pipeline import COUNTRY_FLAGS, SCATTER_X_META, SCATTER_Y_META

# Quick lookups
_X_LABEL = {col: lbl for col, lbl, _ in SCATTER_X_META}
_Y_LABEL = {col: lbl for col, lbl in SCATTER_Y_META}
_Y_COLOR = {col: theme.DIM_COLORS[lbl] for col, lbl in SCATTER_Y_META}

_MIN_N = 5   # minimum countries for a cell to be reported


def _regress_ci(x: np.ndarray, y: np.ndarray, n_pts: int = 200) -> dict | None:
    """OLS regression line + 95 % parametric CI band.

    Args:
        x: Predictor values (may contain NaN).
        y: Outcome values (may contain NaN).
        n_pts: Resolution of the fitted line.

    Returns:
        Dict with fit arrays and r/p/n/slope, or None if fewer than 4
        complete pairs.
    """
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4:
        return None

    slope, intercept, r, p, _ = stats.linregress(x, y)
    x_fit = np.linspace(x.min(), x.max(), n_pts)
    y_fit = slope * x_fit + intercept

    mse     = np.sum((y - (slope * x + intercept)) ** 2) / (n - 2)
    x_bar   = x.mean()
    ss_x    = np.sum((x - x_bar) ** 2)
    t_crit  = stats.t.ppf(0.975, df=n - 2)
    se_band = np.sqrt(mse) * np.sqrt(1 / n + (x_fit - x_bar) ** 2 / ss_x)

    return dict(x_fit=x_fit, y_fit=y_fit,
                ci_lo=y_fit - t_crit * se_band, ci_hi=y_fit + t_crit * se_band,
                r=r, p=p, n=n, slope=slope)


def _bh_qvalues(p_values: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR-adjusted q-values.

    Args:
        p_values: 1-D array of raw p-values (NaN allowed).

    Returns:
        Array of q-values, NaN where the input was NaN.
    """
    q = np.full_like(p_values, np.nan, dtype=float)
    valid = np.where(np.isfinite(p_values))[0]
    if valid.size == 0:
        return q
    p = p_values[valid]
    m = p.size
    order = np.argsort(p)
    ranked = p[order] * m / (np.arange(m) + 1)
    # Enforce monotonicity from the largest p downwards
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q_valid = np.empty(m)
    q_valid[order] = np.clip(ranked, 0, 1)
    q[valid] = q_valid
    return q


def compute_test_family(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """All predictor x dimension correlation tests with BH q-values.

    Args:
        df: Country cross-section (df_scatter).

    Returns:
        {(x_col, y_col): {'r', 'p', 'q', 'n'}} for every testable pair.
    """
    keys, results = [], []
    for x_col, _, _ in SCATTER_X_META:
        for y_col, _ in SCATTER_Y_META:
            if x_col not in df.columns or y_col not in df.columns:
                continue
            reg = _regress_ci(df[x_col].values.astype(float),
                              df[y_col].values.astype(float), n_pts=2)
            if reg and reg['n'] >= _MIN_N:
                keys.append((x_col, y_col))
                results.append({'r': reg['r'], 'p': reg['p'], 'n': reg['n']})
    qs = _bh_qvalues(np.array([res['p'] for res in results]))
    for res, q in zip(results, qs):
        res['q'] = float(q)
    return dict(zip(keys, results))


def _sig_label(q: float) -> str:
    """Significance stars from the FDR-adjusted q-value."""
    if q < 0.001:
        return '***'
    if q < 0.01:
        return '**'
    if q < 0.05:
        return '*'
    return ''


def _hclust_order(matrix: np.ndarray) -> list[int]:
    """Row order from hierarchical clustering (average linkage, NaN -> 0)."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import pdist
    m = np.nan_to_num(matrix, nan=0.0)
    if m.shape[0] < 2:
        return list(range(m.shape[0]))
    return list(leaves_list(linkage(pdist(m, metric='euclidean'),
                                    method='average')))


def make_corr_heatmap(df: pd.DataFrame) -> go.Figure:
    """Correlation heatmap: all predictors x 4 Schwartz dimensions.

    Rows are reordered by hierarchical clustering; stars reflect BH
    FDR-adjusted q-values (the legend in the sidebar explains this).

    Args:
        df: Country cross-section (df_scatter).

    Returns:
        Plotly heatmap figure.
    """
    family   = compute_test_family(df)
    x_cols   = [col for col, _, _ in SCATTER_X_META]
    x_labels = [lbl for _, lbl, _ in SCATTER_X_META]
    y_cols   = [col for col, _ in SCATTER_Y_META]
    y_labels = [lbl for _, lbl in SCATTER_Y_META]

    z_raw, text_raw, hover_raw = [], [], []
    for x_col, x_lbl in zip(x_cols, x_labels):
        row_z, row_t, row_h = [], [], []
        for y_col, y_lbl in zip(y_cols, y_labels):
            res = family.get((x_col, y_col))
            if res:
                sig = _sig_label(res['q'])
                row_z.append(res['r'])
                row_t.append(f"{res['r']:+.2f}{sig}")
                row_h.append(
                    f"<b>{x_lbl}</b> x <b>{y_lbl}</b><br>"
                    f"r = {res['r']:+.3f}{sig}   N = {res['n']}<br>"
                    f"p = {res['p']:.3f}   q (FDR) = {res['q']:.3f}"
                )
            else:
                row_z.append(None)
                row_t.append('n/a')
                row_h.append(f'<b>{x_lbl}</b> x <b>{y_lbl}</b><br>Insufficient data')
        z_raw.append(row_z)
        text_raw.append(row_t)
        hover_raw.append(row_h)

    z_np  = np.array([[v if v is not None else np.nan for v in row]
                      for row in z_raw])
    order = _hclust_order(z_np)

    fig = go.Figure(go.Heatmap(
        z=[z_raw[i] for i in order],
        x=y_labels,
        y=[x_labels[i] for i in order],
        text=[text_raw[i] for i in order],
        customdata=[hover_raw[i] for i in order],
        texttemplate='%{text}',
        textfont=dict(size=10, color=theme.INK),
        colorscale=theme.HEATMAP_SCALE,
        zmid=0, zmin=-1, zmax=1,
        showscale=True,
        colorbar=dict(title=dict(text='Pearson r', side='right'),
                      thickness=12, len=0.7, tickfont=dict(size=9)),
        hovertemplate='%{customdata}<extra></extra>',
    ))
    fig.update_layout(
        height=max(560, 28 * len(x_cols) + 80),
        margin=dict(t=30, b=10, l=220, r=60),
        xaxis=dict(side='top', tickfont=dict(size=11, color=theme.INK),
                   tickangle=0),
        yaxis=dict(autorange='reversed',
                   tickfont=dict(size=10, color=theme.INK)),
    )
    return fig


def _add_scatter_to(fig: go.Figure, df: pd.DataFrame, x_col: str, y_col: str,
                    color: str, row: int | None = None,
                    col: int | None = None) -> dict | None:
    """Add country flag scatter + regression band to a (sub)figure."""
    x = df[x_col].values.astype(float)
    y = df[y_col].values.astype(float)
    codes = df['cntry'].values
    names = df['country_name'].values
    flags = np.array([COUNTRY_FLAGS.get(c, c) for c in codes])
    sk = dict(row=row, col=col) if row is not None else {}

    reg = _regress_ci(x, y)
    if reg:
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_hi']),
            mode='lines', line=dict(width=0),
            showlegend=False, hoverinfo='skip'), **sk)
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_lo']),
            mode='lines', line=dict(width=0),
            fill='tonexty', fillcolor=theme.hex_to_rgba(color, 0.10),
            showlegend=False, hoverinfo='skip'), **sk)
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['y_fit']),
            mode='lines',
            line=dict(color=theme.hex_to_rgba(color, 0.85), width=2.2),
            showlegend=False, hoverinfo='skip'), **sk)

    valid = np.isfinite(x) & np.isfinite(y)
    # Flag emoji as the visual layer, invisible markers as the hover layer
    fig.add_trace(go.Scatter(
        x=x[valid], y=y[valid],
        mode='text',
        text=flags[valid].tolist(),
        textfont=dict(size=11),
        hoverinfo='skip', showlegend=False), **sk)
    fig.add_trace(go.Scatter(
        x=x[valid], y=y[valid],
        mode='markers',
        marker=dict(size=14, opacity=0, color='rgba(0,0,0,0)'),
        customdata=np.stack([names[valid], flags[valid],
                             x[valid], y[valid]], axis=1),
        hovertemplate=(
            '%{customdata[1]}  <b>%{customdata[0]}</b><br>'
            f'{_X_LABEL.get(x_col, x_col)}: %{{customdata[2]:.3f}}<br>'
            f'{_Y_LABEL.get(y_col, y_col)} (Δ): %{{customdata[3]:.3f}}'
            '<extra></extra>'),
        showlegend=False), **sk)
    return reg


def _stats_annotation(family: dict, x_col: str, y_col: str) -> str:
    """One-line r / p / q / N annotation for one test."""
    res = family.get((x_col, y_col))
    if not res:
        return ''
    sig = _sig_label(res['q'])
    return (f"r = {res['r']:+.2f}{sig}   p = {res['p']:.3f}   "
            f"q = {res['q']:.3f}   N = {res['n']}")


def make_scatter_single(df: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    """Single scatter: one predictor vs. one Schwartz dimension.

    Args:
        df: Country cross-section (df_scatter).
        x_col: Predictor column.
        y_col: Dimension column.

    Returns:
        Plotly scatter figure with OLS fit, CI band, and FDR-aware stats.
    """
    family = compute_test_family(df)
    color  = _Y_COLOR.get(y_col, theme.PRIMARY)

    fig = go.Figure()
    _add_scatter_to(fig, df, x_col, y_col, color)
    note = _stats_annotation(family, x_col, y_col)
    if note:
        fig.add_annotation(
            text=note, xref='paper', yref='paper', x=0.98, y=0.98,
            xanchor='right', yanchor='top', showarrow=False,
            font=dict(size=10.5, color=theme.MUTED),
            bgcolor='rgba(241,244,250,0.9)', borderpad=4)

    fig.update_xaxes(title_text=_X_LABEL.get(x_col, x_col))
    fig.update_yaxes(title_text=f'{_Y_LABEL.get(y_col, y_col)} (Δ-score)',
                     title_font=dict(color=color),
                     zeroline=True, zerolinewidth=1.5)
    fig.update_layout(height=520, margin=dict(t=30, b=60, l=80, r=40))
    return fig


def make_scatter_all(df: pd.DataFrame, x_col: str) -> go.Figure:
    """2x2 grid: one predictor vs. all four Schwartz dimensions.

    Args:
        df: Country cross-section (df_scatter).
        x_col: Predictor column.

    Returns:
        Plotly subplot figure.
    """
    family = compute_test_family(df)
    fig = make_subplots(rows=2, cols=2,
                        horizontal_spacing=0.12, vertical_spacing=0.16)

    for (y_col, y_lbl), (r, c) in zip(SCATTER_Y_META,
                                      [(1, 1), (1, 2), (2, 1), (2, 2)]):
        color = _Y_COLOR[y_col]
        _add_scatter_to(fig, df, x_col, y_col, color, r, c)
        note = _stats_annotation(family, x_col, y_col)
        if note:
            ax_i = (r - 1) * 2 + c
            ref  = '' if ax_i == 1 else str(ax_i)
            fig.add_annotation(
                text=note, font=dict(size=9, color=theme.MUTED),
                showarrow=False,
                xref=f'x{ref} domain', yref=f'y{ref} domain',
                x=0.98, y=0.98, xanchor='right', yanchor='top',
                bgcolor='rgba(241,244,250,0.9)', borderpad=3)
        fig.update_xaxes(title_text=_X_LABEL.get(x_col, x_col),
                         title_font=dict(size=10), row=r, col=c)
        fig.update_yaxes(title_text=f'{y_lbl} (Δ)',
                         title_font=dict(size=10, color=color),
                         zeroline=True, zerolinewidth=1.2, row=r, col=c)

    fig.update_layout(height=720, margin=dict(t=30, b=50, l=80, r=40))
    return fig
