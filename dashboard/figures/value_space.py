"""PCA value-space figure with radar glyphs (Value Space tab, ESS11).

Countries are projected onto two principal components; each country is
drawn as a small radar glyph of its raw variable profile, coloured by
K-Means cluster membership.
"""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

import theme
from data_pipeline import COUNTRIES, COUNTRY_FLAGS, ESS_ROUND, ESS_YEAR

CLUSTER_COLORS = theme.CLUSTER_COLORS


def _hull_traces(result) -> list[go.Scatter]:
    """Filled convex hull polygon per cluster (skipped if < 3 points)."""
    from scipy.spatial import ConvexHull

    traces = []
    for cid in sorted(result['cluster'].unique()):
        pts = result[result['cluster'] == cid][['pc1', 'pc2']].values
        color = CLUSTER_COLORS[int(cid) % len(CLUSTER_COLORS)]
        if len(pts) < 3:
            continue
        try:
            verts = pts[ConvexHull(pts).vertices]
        except Exception:   # collinear points etc. - hull is cosmetic only
            continue
        traces.append(go.Scatter(
            x=list(verts[:, 0]) + [verts[0, 0]],
            y=list(verts[:, 1]) + [verts[0, 1]],
            mode='lines',
            line=dict(width=0, color='rgba(0,0,0,0)'),
            fill='toself',
            fillcolor=theme.hex_to_rgba(color, 0.13),
            showlegend=False,
            hoverinfo='skip',
        ))
    return traces


def _glyph_traces(result, glyph_size: float, max_abs: dict,
                  data_cols: list[str]) -> list[go.Scatter]:
    """One closed radar polygon per country (per-column normalisation)."""
    traces = []
    n = len(data_cols)
    for _, row in result.iterrows():
        cx, cy = float(row['pc1']), float(row['pc2'])
        color = CLUSTER_COLORS[int(row['cluster']) % len(CLUSTER_COLORS)]
        xs, ys = [], []
        for i, col in enumerate(data_cols):
            try:
                v = float(row[col])
            except (TypeError, ValueError, KeyError):
                v = np.nan
            if np.isnan(v):
                continue   # skip missing spokes - don't collapse to centre
            col_max = max_abs.get(col, 1.0)
            angle = math.pi / 2 - 2 * math.pi * i / n
            xs.append(cx + glyph_size * (v / col_max) * math.cos(angle))
            ys.append(cy + glyph_size * (v / col_max) * math.sin(angle))
        if len(xs) < 2:
            continue
        traces.append(go.Scatter(
            x=xs + [xs[0]], y=ys + [ys[0]],
            mode='lines',
            line=dict(color=color, width=1.5),
            fill='toself',
            fillcolor=theme.hex_to_rgba(color, 0.25),
            showlegend=False,
            hoverinfo='skip',
        ))
    return traces


def _label_traces(result) -> list[go.Scatter]:
    """Country name + flag label below each glyph centre."""
    return [go.Scatter(
        x=[float(row['pc1'])], y=[float(row['pc2'])],
        mode='text',
        text=[f"{COUNTRY_FLAGS.get(row['cntry'], '')}<br>"
              f"{COUNTRIES.get(row['cntry'], row['cntry'])}"],
        textfont=dict(size=10, color=theme.INK),
        textposition='bottom center',
        showlegend=False,
        hoverinfo='skip',
    ) for _, row in result.iterrows()]


def _hover_traces(result, data_cols: list[str],
                  spoke_labels: list[str]) -> list[go.Scatter]:
    """Invisible hit-targets with per-variable values in the hover card."""
    traces = []
    for _, row in result.iterrows():
        var_lines = []
        for col, lbl in zip(data_cols, spoke_labels):
            v = row.get(col)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                var_lines.append(f'{lbl}: {float(v):.2f}')
        hover = (f"<b>{COUNTRY_FLAGS.get(row['cntry'], '')} "
                 f"{COUNTRIES.get(row['cntry'], row['cntry'])}</b><br>"
                 f"Cluster {int(row['cluster']) + 1}<br><br>"
                 + '<br>'.join(var_lines))
        traces.append(go.Scatter(
            x=[float(row['pc1'])], y=[float(row['pc2'])],
            mode='markers',
            marker=dict(size=20, opacity=0, color='rgba(0,0,0,0)'),
            hovertemplate=hover + '<extra></extra>',
            showlegend=False,
        ))
    return traces


def make_value_space_figure(result, explained, pc1_label, pc2_label,
                            n_clusters, data_cols=None, spoke_labels=None,
                            dim_group_label='Value Orientations') -> go.Figure:
    """Build the Value Space figure from precomputed PCA / cluster data.

    Args:
        result: DataFrame from compute_pca_clustering (or None).
        explained: Explained-variance ratios for PC1/PC2.
        pc1_label: Interpretation label for PC1.
        pc2_label: Interpretation label for PC2.
        n_clusters: Number of clusters (display only).
        data_cols: Columns drawn as glyph spokes.
        spoke_labels: Display names for the spokes.
        dim_group_label: Title fragment for the chosen dimension group.

    Returns:
        Plotly figure (empty-state if result is None/empty).
    """
    if result is None or result.empty:
        fig = go.Figure()
        fig.add_annotation(
            text='No data available for this selection.',
            x=0.5, y=0.5, showarrow=False, xref='paper', yref='paper',
            font=dict(size=14, color=theme.MUTED))
        fig.update_layout(height=650, margin=dict(t=60, l=80, r=40, b=60))
        return fig

    data_cols = data_cols or []
    spoke_labels = spoke_labels or data_cols
    avail = [c for c in data_cols if c in result.columns]

    # Per-column normalisation keeps differently scaled spokes legible
    max_abs = {c: (float(result[c].abs().max()) or 1.0) for c in avail}
    x_span = float(result['pc1'].max() - result['pc1'].min())
    y_span = float(result['pc2'].max() - result['pc2'].min())
    glyph_size = 0.12 * max(x_span, y_span, 0.01)

    fig = go.Figure()
    for trace in (_hull_traces(result)
                  + _glyph_traces(result, glyph_size, max_abs, avail)
                  + _label_traces(result)
                  + _hover_traces(result, avail, spoke_labels[:len(avail)])):
        fig.add_trace(trace)

    fig.update_layout(
        height=650,
        margin=dict(t=60, l=80, r=40, b=60),
        showlegend=False,
        hovermode='closest',
        title=dict(
            text=(f'ESS Round {ESS_ROUND} ({ESS_YEAR})  ·  {dim_group_label}'
                  f'  ·  N={len(result)}'),
            font=dict(size=14, color=theme.INK),
        ),
        xaxis=dict(
            title=f'{pc1_label}  (PC1, {explained[0]:.1%} variance)',
            showgrid=False, zeroline=False, showticklabels=False,
            title_font=dict(size=11, color=theme.MUTED),
        ),
        yaxis=dict(
            title=f'{pc2_label}  (PC2, {explained[1]:.1%} variance)',
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor='x', scaleratio=1,
            title_font=dict(size=11, color=theme.MUTED),
        ),
    )
    return fig
