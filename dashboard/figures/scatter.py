import numpy as np
import pandas as pd
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_pipeline import (
    SCATTER_X_META, SCATTER_Y_META,
    COUNTRIES, COUNTRY_FLAGS, BG_COLOR, hex_to_rgba,
)

# Quick lookup: col → (label, description)
_X_LABEL = {col: lbl for col, lbl, _ in SCATTER_X_META}
_X_DESC  = {col: desc for col, _, desc in SCATTER_X_META}
_Y_LABEL = {col: lbl for col, lbl, _ in SCATTER_Y_META}
_Y_COLOR = {col: clr for col, _, clr in SCATTER_Y_META}


def _regress_ci(x: np.ndarray, y: np.ndarray, n_pts: int = 200):
    """OLS regression line + 95 % parametric CI band."""
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4:
        return None

    slope, intercept, r, p, _ = stats.linregress(x, y)
    x_fit  = np.linspace(x.min(), x.max(), n_pts)
    y_fit  = slope * x_fit + intercept

    # Parametric 95 % CI around the regression line
    mse   = np.sum((y - (slope * x + intercept)) ** 2) / (n - 2)
    se_y  = np.sqrt(mse)
    x_bar = x.mean()
    ss_x  = np.sum((x - x_bar) ** 2)
    t_crit = stats.t.ppf(0.975, df=n - 2)
    se_band = se_y * np.sqrt(1 / n + (x_fit - x_bar) ** 2 / ss_x)
    ci_lo  = y_fit - t_crit * se_band
    ci_hi  = y_fit + t_crit * se_band

    return dict(x_fit=x_fit, y_fit=y_fit, ci_lo=ci_lo, ci_hi=ci_hi,
                r=r, p=p, n=n, slope=slope)


def _sig_label(p: float) -> str:
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < 0.05:
        return '*'
    return ''


def _add_scatter_to(fig, df: pd.DataFrame, x_col: str, y_col: str,
                    color: str, row=None, col=None,
                    show_reg: bool = True):
    """Add country scatter + regression. row/col=None → plain figure (no subplot grid)."""
    x = df[x_col].values.astype(float)
    y = df[y_col].values.astype(float)
    codes  = df['cntry'].values
    names  = df['country_name'].values
    flags  = np.array([COUNTRY_FLAGS.get(c, '') for c in codes])

    # Subplot kwargs - omit row/col for plain figures
    sk = dict(row=row, col=col) if row is not None else {}

    # CI band + regression line
    reg = _regress_ci(x, y) if show_reg else None
    if reg:
        band_color = hex_to_rgba(color, 0.10)
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_hi']),
            mode='lines', line=dict(width=0),
            showlegend=False, hoverinfo='skip',
        ), **sk)
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_lo']),
            mode='lines', line=dict(width=0),
            fill='tonexty', fillcolor=band_color,
            showlegend=False, hoverinfo='skip',
        ), **sk)
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['y_fit']),
            mode='lines',
            line=dict(color=hex_to_rgba(color, 0.85), width=2.2),
            showlegend=False, hoverinfo='skip',
        ), **sk)

    # Country points: flag emoji as visual, transparent marker for hover
    valid = np.isfinite(x) & np.isfinite(y)
    x_lbl = _X_LABEL.get(x_col, x_col)
    y_lbl = _Y_LABEL.get(y_col, y_col)

    # Emoji flags (visual layer - no hover)
    fig.add_trace(go.Scatter(
        x=x[valid], y=y[valid],
        mode='text',
        text=flags[valid].tolist(),
        textfont=dict(size=10),
        textposition='middle center',
        hoverinfo='skip',
        showlegend=False,
    ), **sk)

    # Invisible markers on top (hover layer only)
    fig.add_trace(go.Scatter(
        x=x[valid], y=y[valid],
        mode='markers',
        marker=dict(size=12, opacity=0, color='rgba(0,0,0,0)'),
        customdata=np.stack([names[valid], flags[valid],
                             x[valid], y[valid]], axis=1),
        hovertemplate=(
            '%{customdata[1]}  <b>%{customdata[0]}</b><br>'
            f'{x_lbl}: %{{customdata[2]:.3f}}<br>'
            f'{y_lbl} (Δ): %{{customdata[3]:.3f}}'
            '<extra></extra>'
        ),
        showlegend=False,
    ), **sk)

    # r / p annotation for subplot grids (row/col provided)
    if reg and row is not None:
        sig   = _sig_label(reg['p'])
        ax_i  = (row - 1) * 2 + col
        xref  = 'x domain'       if ax_i == 1 else f'x{ax_i} domain'
        yref  = 'y domain'       if ax_i == 1 else f'y{ax_i} domain'
        fig.add_annotation(
            text=f"r = {reg['r']:+.2f}{sig}  p = {reg['p']:.3f}",
            font=dict(size=9, color='#4a5568'),
            showarrow=False,
            xref=xref, yref=yref,
            x=0.98, y=0.98,
            xanchor='right', yanchor='top',
            bgcolor='rgba(237,240,247,0.85)',
            borderpad=3,
        )

    return reg


def _hclust_order(matrix: np.ndarray) -> list[int]:
    """Return row indices reordered by hierarchical clustering (average linkage).

    NaN values are replaced with 0 before clustering so missing data doesn't
    break the distance computation.
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    from scipy.spatial.distance import pdist
    m = np.nan_to_num(matrix, nan=0.0)
    if m.shape[0] < 2:
        return list(range(m.shape[0]))
    dist = pdist(m, metric='euclidean')
    Z    = linkage(dist, method='average')
    return list(leaves_list(Z))


def make_corr_heatmap(df: pd.DataFrame, year) -> go.Figure:
    """Correlation heatmap: all X predictors × 4 Schwartz dimensions.

    Rows (predictors) are reordered by hierarchical clustering so that
    predictors with similar correlation patterns appear together.
    Cells show Pearson r with significance stars.
    """
    sub = _prepare(df, year)

    x_cols   = [col for col, _, _ in SCATTER_X_META]
    x_labels = [lbl for _, lbl, _ in SCATTER_X_META]
    y_cols   = [col for col, _, _ in SCATTER_Y_META]
    y_labels = [lbl for _, lbl, _ in SCATTER_Y_META]

    # Build the full r-matrix first (rows = predictors, cols = Schwartz dims)
    z_raw, text_raw, hover_raw = [], [], []
    for x_col, x_lbl in zip(x_cols, x_labels):
        row_z, row_t, row_h = [], [], []
        for y_col, y_lbl in zip(y_cols, y_labels):
            xv = sub[x_col].values.astype(float) if x_col in sub.columns else np.array([])
            yv = sub[y_col].values.astype(float) if y_col in sub.columns else np.array([])
            reg = _regress_ci(xv, yv, n_pts=2)
            if reg and reg['n'] >= 5:
                sig = _sig_label(reg['p'])
                row_z.append(reg['r'])
                row_t.append(f"{reg['r']:+.2f}{sig}" if sig else f"{reg['r']:+.2f}")
                row_h.append(
                    f"<b>{x_lbl}</b> x <b>{y_lbl}</b><br>"
                    f"r = {reg['r']:+.3f}{sig}   p = {reg['p']:.3f}   N = {reg['n']}"
                )
            else:
                row_z.append(None)
                row_t.append('n/a')
                row_h.append(f"<b>{x_lbl}</b> x <b>{y_lbl}</b><br>Insufficient data")
        z_raw.append(row_z)
        text_raw.append(row_t)
        hover_raw.append(row_h)

    # Reorder rows by hierarchical clustering on the r-matrix
    z_np  = np.array([[v if v is not None else np.nan for v in row] for row in z_raw])
    order = _hclust_order(z_np)

    z         = [z_raw[i]    for i in order]
    text_mat  = [text_raw[i] for i in order]
    hover_mat = [hover_raw[i] for i in order]
    y_labels_ordered = [x_labels[i] for i in order]

    colorscale = [
        [0.00, '#2166ac'],
        [0.25, '#92c5de'],
        [0.50, '#f7f7f7'],
        [0.75, '#f4a582'],
        [1.00, '#d6604d'],
    ]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=y_labels,
        y=y_labels_ordered,
        text=text_mat,
        customdata=hover_mat,
        texttemplate='%{text}',
        textfont=dict(size=10, color='#1a2840'),
        colorscale=colorscale,
        zmid=0, zmin=-1, zmax=1,
        showscale=True,
        colorbar=dict(
            title=dict(text='Pearson r', side='right'),
            thickness=12, len=0.7, tickfont=dict(size=9),
        ),
        hovertemplate='%{customdata}<extra></extra>',
    ))

    n_rows = len(x_cols)
    fig.update_layout(
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        height=max(560, 28 * n_rows + 80),  # ~28px per row
        margin=dict(t=30, b=10, l=220, r=60),
        xaxis=dict(
            side='top',
            tickfont=dict(size=11, color='#1a2840'),
            tickangle=0,
        ),
        yaxis=dict(
            autorange='reversed',
            tickfont=dict(size=10, color='#1a2840'),
        ),
        hoverlabel=dict(bgcolor='white', font_size=12),
    )
    return fig


def _prepare(df: pd.DataFrame, year) -> pd.DataFrame:
    """Filter to one ESS round or aggregate country means across all rounds."""
    if year == 'all':
        return df.groupby('cntry').agg(
            country_name=('country_name', 'first'),
            **{col: (col, 'mean') for col, _, _ in SCATTER_X_META if col in df.columns},
            **{col: (col, 'mean') for col, _, _ in SCATTER_Y_META if col in df.columns},
        ).reset_index()
    return df[df['year'] == year].copy()


def make_scatter_single(df: pd.DataFrame, x_col: str, y_col: str,
                        year=2023) -> go.Figure:
    """Single scatter: one X variable vs. one Schwartz dimension for one ESS round."""
    sub    = _prepare(df, year)
    color  = _Y_COLOR.get(y_col, '#1a5fb4')
    x_lbl  = _X_LABEL.get(x_col, x_col)
    y_lbl  = _Y_LABEL.get(y_col, y_col)

    fig = go.Figure()
    reg = _add_scatter_to(fig, sub, x_col, y_col, color)

    if reg:
        sig = _sig_label(reg['p'])
        fig.add_annotation(
            text=f"r = {reg['r']:+.2f}{sig}   p = {reg['p']:.3f}   N = {reg['n']}",
            xref='paper', yref='paper', x=0.98, y=0.98,
            xanchor='right', yanchor='top',
            showarrow=False,
            font=dict(size=10.5, color='#4a5568'),
            bgcolor='rgba(237,240,247,0.85)',
            borderpad=4,
        )

    fig.update_xaxes(
        title_text=x_lbl,
        title_font=dict(size=12, color='#1a2840'),
        gridcolor='#e8edf5', zerolinecolor='#e8edf5',
    )
    fig.update_yaxes(
        title_text=f'{y_lbl} (Δ-score)',
        title_font=dict(size=12, color=color),
        gridcolor='#e8edf5', zerolinecolor='#d0d8e8',
        zeroline=True, zerolinewidth=1.5,
    )
    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor='#edf1f8',
        height=520, margin=dict(t=30, b=60, l=80, r=40),
        hoverlabel=dict(bgcolor='white', font_size=12),
    )
    return fig


def make_scatter_all(df: pd.DataFrame, x_col: str, year=2023) -> go.Figure:
    """2×2 subplot grid: one X variable vs. all 4 Schwartz dimensions."""
    sub   = _prepare(df, year)
    x_lbl = _X_LABEL.get(x_col, x_col)

    fig = make_subplots(rows=2, cols=2, shared_xaxes=False,
                        horizontal_spacing=0.12, vertical_spacing=0.16)

    for (y_col, y_lbl, color), (r, c) in zip(SCATTER_Y_META, [(1,1),(1,2),(2,1),(2,2)]):
        _add_scatter_to(fig, sub, x_col, y_col, color, r, c)
        fig.update_xaxes(title_text=x_lbl, title_font=dict(size=10),
                         gridcolor='#e8edf5', row=r, col=c)
        fig.update_yaxes(title_text=f'{y_lbl} (Δ)',
                         title_font=dict(size=10, color=color),
                         gridcolor='#e8edf5', zerolinecolor='#d0d8e8',
                         zeroline=True, zerolinewidth=1.2, row=r, col=c)

    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor='#edf1f8',
        height=720, margin=dict(t=30, b=50, l=80, r=40),
        hoverlabel=dict(bgcolor='white', font_size=12),
    )
    for i in range(1, 5):
        s = '' if i == 1 else str(i)
        fig.layout[f'xaxis{s}'].update(gridcolor='#e8edf5')
        fig.layout[f'yaxis{s}'].update(gridcolor='#e8edf5')

    return fig
