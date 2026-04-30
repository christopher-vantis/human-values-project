import math
import numpy as np
import plotly.graph_objects as go

from data_pipeline import (
    COUNTRIES, COUNTRY_FLAGS, VALUE_KEYS, VALUE_LABELS,
    BG_COLOR, YEAR_TO_ROUND, hex_to_rgba,
)

CLUSTER_COLORS = ['#3584e4', '#e01b24', '#2ec27e', '#f5c211', '#9141ac', '#ed5c00']

_DIM_DCOLS = {
    'Openness to Change': ['d_SD', 'd_HE', 'd_ST'],
    'Self-Transcendence': ['d_UN', 'd_BE'],
    'Conservation':       ['d_TR', 'd_CO', 'd_SE'],
    'Self-Enhancement':   ['d_PO', 'd_AC'],
}


def _hull_traces(result):
    """Filled convex hull polygon per cluster (skipped if < 3 points)."""
    from scipy.spatial import ConvexHull

    traces = []
    for cid in sorted(result['cluster'].unique()):
        grp = result[result['cluster'] == cid]
        pts = grp[['pc1', 'pc2']].values
        color = CLUSTER_COLORS[int(cid) % len(CLUSTER_COLORS)]
        if len(pts) < 3:
            continue
        try:
            hull = ConvexHull(pts)
            verts = pts[hull.vertices]
            xs = list(verts[:, 0]) + [verts[0, 0]]
            ys = list(verts[:, 1]) + [verts[0, 1]]
            traces.append(go.Scatter(
                x=xs, y=ys,
                mode='lines',
                line=dict(width=0, color='rgba(0,0,0,0)'),
                fill='toself',
                fillcolor=hex_to_rgba(color, 0.15),
                showlegend=False,
                hoverinfo='skip',
            ))
        except Exception:
            pass
    return traces


def _glyph_traces(result, glyph_size, max_abs, data_cols):
    """One closed radar polygon per country for an arbitrary set of data columns."""
    traces = []
    n = len(data_cols)
    for _, row in result.iterrows():
        cx, cy = float(row['pc1']), float(row['pc2'])
        color = CLUSTER_COLORS[int(row['cluster']) % len(CLUSTER_COLORS)]

        xs, ys = [], []
        for i, col in enumerate(data_cols):
            v = float(row[col]) if col in row.index and not np.isnan(float(row[col])) else 0.0
            delta_norm = v / max_abs if max_abs > 0 else 0
            angle = math.pi / 2 - 2 * math.pi * i / n
            xs.append(cx + glyph_size * delta_norm * math.cos(angle))
            ys.append(cy + glyph_size * delta_norm * math.sin(angle))

        xs.append(xs[0])
        ys.append(ys[0])

        traces.append(go.Scatter(
            x=xs, y=ys,
            mode='lines',
            line=dict(color=color, width=1.5),
            fill='toself',
            fillcolor=hex_to_rgba(color, 0.25),
            showlegend=False,
            hoverinfo='skip',
        ))
    return traces


def _label_traces(result):
    """Country name + flag label below each glyph center."""
    traces = []
    for _, row in result.iterrows():
        cntry = row['cntry']
        flag  = COUNTRY_FLAGS.get(cntry, '')
        name  = COUNTRIES.get(cntry, cntry)
        traces.append(go.Scatter(
            x=[float(row['pc1'])],
            y=[float(row['pc2'])],
            mode='text',
            text=[f'{flag}<br>{name}'],
            textfont=dict(size=10, color='#1a2840', family='sans-serif'),
            textposition='bottom center',
            showlegend=False,
            hoverinfo='skip',
        ))
    return traces


def _hover_traces(result, data_cols, spoke_labels):
    """Invisible large hit-targets with per-variable values in hover card."""
    traces = []
    for _, row in result.iterrows():
        cntry   = row['cntry']
        name    = COUNTRIES.get(cntry, cntry)
        flag    = COUNTRY_FLAGS.get(cntry, '')
        cluster = int(row['cluster']) + 1

        var_lines = []
        for col, lbl in zip(data_cols, spoke_labels):
            if col in row.index:
                v = row[col]
                if not (isinstance(v, float) and np.isnan(v)):
                    var_lines.append(f'{lbl}: {float(v):.2f}')

        hover = (
            f'<b>{flag} {name}</b><br>'
            f'Cluster {cluster}<br><br>'
            + '<br>'.join(var_lines)
        )
        traces.append(go.Scatter(
            x=[float(row['pc1'])],
            y=[float(row['pc2'])],
            mode='markers',
            marker=dict(size=20, opacity=0, color='rgba(0,0,0,0)'),
            hovertemplate=hover + '<extra></extra>',
            showlegend=False,
        ))
    return traces


def make_value_space_figure(result, explained, pc1_label, pc2_label,
                             round_year, n_clusters,
                             data_cols=None, spoke_labels=None,
                             dim_group_label='Value Orientations'):
    """Build the Value Space figure from pre-computed PCA/cluster data.

    data_cols     : list of column names used as glyph spokes
    spoke_labels  : display names for each spoke (same length as data_cols)
    """
    from data_pipeline import VALUE_KEYS  # local import to avoid circular

    if data_cols is None:
        data_cols = [f'd_{k}' for k in VALUE_KEYS]
    if spoke_labels is None:
        spoke_labels = data_cols

    if result is None or result.empty:
        fig = go.Figure()
        fig.add_annotation(
            text='No data available for this selection.',
            x=0.5, y=0.5, showarrow=False, xref='paper', yref='paper',
            font=dict(size=14, color='#5a6a80'),
        )
        fig.update_layout(paper_bgcolor=BG_COLOR, height=650,
                          margin=dict(t=60, l=80, r=40, b=60))
        return fig

    # Normalise glyph values across the available data columns
    avail = [c for c in data_cols if c in result.columns]
    max_abs = float(result[avail].abs().max().max()) if avail else 1.0
    if max_abs == 0:
        max_abs = 1.0

    x_span = float(result['pc1'].max() - result['pc1'].min())
    y_span = float(result['pc2'].max() - result['pc2'].min())
    glyph_size = 0.12 * max(x_span, y_span, 0.01)

    fig = go.Figure()
    for t in _hull_traces(result):
        fig.add_trace(t)
    for t in _glyph_traces(result, glyph_size, max_abs, avail):
        fig.add_trace(t)
    for t in _label_traces(result):
        fig.add_trace(t)
    for t in _hover_traces(result, avail, spoke_labels[:len(avail)]):
        fig.add_trace(t)

    ess_round = YEAR_TO_ROUND.get(round_year, '?')
    x_title = f'{pc1_label}  (PC1, {explained[0]:.1%} variance)'
    y_title = f'{pc2_label}  (PC2, {explained[1]:.1%} variance)'
    n_ctry  = len(result)

    fig.update_layout(
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        height=650,
        margin=dict(t=60, l=80, r=40, b=60),
        showlegend=False,
        hovermode='closest',
        title=dict(
            text=(f'ESS Round {ess_round} ({round_year})  ·  '
                  f'{dim_group_label}  ·  N={n_ctry}'),
            x=0.5, xanchor='center',
            font=dict(size=14, color='#0d1b2a', family='sans-serif'),
        ),
        xaxis=dict(
            title=x_title,
            showgrid=False, zeroline=False, showticklabels=False,
            title_font=dict(size=11, color='#5a6a80'),
        ),
        yaxis=dict(
            title=y_title,
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor='x', scaleratio=1,
            title_font=dict(size=11, color='#5a6a80'),
        ),
    )
    return fig
