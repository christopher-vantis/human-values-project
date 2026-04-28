import plotly.graph_objects as go
import pandas as pd
import numpy as np

from data_pipeline import (
    COUNTRIES, DIMS, DIM_COLORS, DIM_COLS, MACRO_COLS,
    MICRO_ATTR_META,
    COUNTRY_COLORS, BG_COLOR, YEAR_TO_ROUND, hex_to_rgba,
)


def _build_colorscale(countries_sorted: list) -> list:
    """Discrete step colorscale: integer country index → country color."""
    n = len(countries_sorted)
    scale = []
    for i, c in enumerate(countries_sorted):
        color = COUNTRY_COLORS[c]
        scale.append([i / n, color])
        scale.append([(i + 1) / n, color])
    scale[-1][0] = 1.0
    return scale


# Columns that are non-negative: clamp range minimum to 0 so that NaN values
# rendered as 0 by Plotly.js appear at the axis bottom rather than below it.
_NON_NEG_COLS = {
    'ldi', 'gini', 'unemployment_rate', 'migration_share', 'mean_eduyrs',
}


def _axis_range(df: pd.DataFrame, col: str, pad_frac: float = 0.12) -> list:
    """Data-driven axis range with padding; returns [lo, hi] or None if all NaN."""
    vals = df[col].dropna()
    if vals.empty:
        return None
    lo, hi = vals.min(), vals.max()
    span = hi - lo
    pad = max(span * pad_frac, 0.5) if span > 0 else 0.5
    lo_padded = lo - pad
    if col in _NON_NEG_COLS:
        lo_padded = min(lo_padded, 0)   # ensures 0 is within range
    return [lo_padded, hi + pad]


# Schwartz higher-order dimension columns - kept on a global range for cross-year
# comparability. Macro columns are scaled per-year so data always fills the axis.
_DIM_COLS = {'dim_openness', 'dim_transcendence', 'dim_conservation', 'dim_enhancement'}


def make_parallel(df: pd.DataFrame, year: int, countries: list) -> go.Figure:
    def _empty(msg=''):
        fig = go.Figure()
        if msg:
            fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False,
                               font=dict(size=13, color='#5a6a80'),
                               xref='paper', yref='paper')
        fig.update_layout(paper_bgcolor=BG_COLOR, height=820,
                          margin=dict(t=140, b=60, l=110, r=110))
        return fig

    if not countries:
        return _empty()

    data = df[(df['year'] == year) & (df['cntry'].isin(countries))].copy()
    if data.empty:
        return _empty('No data for this round / country selection.')

    countries_sorted = sorted(data['cntry'].unique())
    idx_map   = {c: i for i, c in enumerate(countries_sorted)}
    data['_cidx'] = data['cntry'].map(idx_map).astype(float)
    n = len(countries_sorted)

    colorscale = _build_colorscale(countries_sorted)

    dimensions = []
    for col, label in MACRO_COLS:
        if col not in data.columns:
            continue
        # Schwartz dims: global range keeps them comparable across years.
        # Macro cols: per-year range so data fills the axis (avoids compression
        # from e.g. 2010-crisis unemployment dragging the 2020/2023 axis down).
        source = df if col in _DIM_COLS else data
        rng = _axis_range(source, col)
        # Use None (not float nan) so Plotly.js treats missing values as
        # "no data" (broken line) rather than mapping them to 0.
        vals = [None if pd.isna(v) else v for v in data[col]]
        dim = dict(label=label, values=vals)
        if rng is not None:
            dim['range'] = rng
        dimensions.append(dim)

    fig = go.Figure(go.Parcoords(
        line=dict(
            color=data['_cidx'].tolist(),
            colorscale=colorscale,
            cmin=0,
            cmax=n,
            showscale=False,
        ),
        dimensions=dimensions,
        labelside='top',
        labelangle=-30,
        labelfont=dict(size=10.5, color='#1a2840', family='sans-serif'),
        tickfont=dict(size=9, color='#5a6a80'),
        rangefont=dict(size=8.5, color='#5a6a80'),
    ))

    # Title is rendered as a Dash html.Div above the graph.
    fig.update_layout(
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        height=820,
        margin=dict(t=140, b=60, l=110, r=110),
    )
    return fig


def make_parallel_micro(df: pd.DataFrame, highlight_dim: str) -> go.Figure:
    """IQR-band profile plot: median ± IQR per Schwartz dimension across attitude axes.

    highlight_dim: 'all'  → show all 4 dimensions equally
                   <name> → highlight one, fade the others
    """
    def _empty(msg=''):
        fig = go.Figure()
        if msg:
            fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False,
                               font=dict(size=13, color='#5a6a80'),
                               xref='paper', yref='paper')
        fig.update_layout(paper_bgcolor=BG_COLOR, height=520,
                          margin=dict(t=90, b=70, l=60, r=40))
        return fig

    if df is None or df.empty:
        return _empty('No data available.')

    highlight = None if highlight_dim == 'all' else highlight_dim
    n_axes = len(MICRO_ATTR_META)
    xs = list(range(n_axes))

    def _norm(val, lo, hi):
        return (val - lo) / (hi - lo) if hi > lo else 0.5

    fig = go.Figure()

    for dim in DIMS:
        grp = df[df['dominant_dim'] == dim]
        if grp.empty:
            continue

        color    = DIM_COLORS[dim]
        is_hl    = highlight is None or highlight == dim
        a_band   = 0.28 if is_hl else 0.04
        a_line   = 1.00 if is_hl else 0.15
        lw       = 2.5  if is_hl else 1.0
        mk_size  = 7    if is_hl else 3

        medians, q1s, q3s = [], [], []
        med_raw, q1_raw, q3_raw = [], [], []
        ax_labels = []

        for col, label, (rng_lo, rng_hi) in MICRO_ATTR_META:
            vals = grp[col].dropna()
            ax_labels.append(label.replace('\n', ' '))
            if vals.empty:
                mr, q1r, q3r = (rng_lo + rng_hi) / 2, rng_lo, rng_hi
            else:
                mr  = float(vals.median())
                q1r = float(vals.quantile(0.25))
                q3r = float(vals.quantile(0.75))
            medians.append(_norm(mr,  rng_lo, rng_hi))
            q1s.append(    _norm(q1r, rng_lo, rng_hi))
            q3s.append(    _norm(q3r, rng_lo, rng_hi))
            med_raw.append(mr)
            q1_raw.append(q1r)
            q3_raw.append(q3r)

        # IQR filled polygon: Q3 left→right, Q1 right→left (closed)
        band_x = xs + xs[::-1] + [xs[0]]
        band_y = q3s + q1s[::-1] + [q3s[0]]
        fig.add_trace(go.Scatter(
            x=band_x, y=band_y,
            mode='lines',
            fill='toself',
            fillcolor=hex_to_rgba(color, a_band),
            line=dict(width=0, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip',
        ))

        # Median line (smooth spline)
        customdata = [
            [q1_raw[i], med_raw[i], q3_raw[i], ax_labels[i]]
            for i in range(n_axes)
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=medians,
            mode='lines+markers',
            line=dict(color=hex_to_rgba(color, a_line), width=lw,
                      shape='spline', smoothing=0.7),
            marker=dict(color=color, size=mk_size, opacity=a_line,
                        line=dict(color='white', width=1) if is_hl else dict(width=0)),
            name=dim,
            customdata=customdata,
            hovertemplate=(
                '<b>%{customdata[3]}</b><br>'
                'Median: %{customdata[1]:.2f}<br>'
                'IQR: %{customdata[0]:.2f} - %{customdata[2]:.2f}'
                '<extra>' + dim + '</extra>'
            ),
        ))

    # Axis vertical lines and labels
    for i, (col, label, (rng_lo, rng_hi)) in enumerate(MICRO_ATTR_META):
        fig.add_shape(
            type='line', x0=i, x1=i, y0=0, y1=1,
            xref='x', yref='y',
            line=dict(color='#c8d4e0', width=1),
            layer='below',
        )
        fig.add_annotation(
            x=i, xref='x', y=1.25, yref='y',
            text=label.replace('\n', '<br>'),
            showarrow=False, align='center',
            font=dict(size=9.5, color='#1a2840', family='sans-serif'),
            xanchor='center', yanchor='bottom',
        )
        fig.add_annotation(
            x=i, xref='x', y=1.03, yref='y',
            text=str(rng_hi),
            showarrow=False,
            font=dict(size=8, color='#9aa8b8'),
            xanchor='center', yanchor='bottom',
        )
        fig.add_annotation(
            x=i, xref='x', y=-0.04, yref='y',
            text=str(rng_lo),
            showarrow=False,
            font=dict(size=8, color='#9aa8b8'),
            xanchor='center', yanchor='top',
        )

    fig.update_layout(
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        height=560,
        margin=dict(t=60, b=80, l=50, r=30),
        xaxis=dict(
            range=[-0.5, n_axes - 0.5],
            showgrid=False, showticklabels=False, zeroline=False,
        ),
        yaxis=dict(
            range=[-0.10, 1.55],
            showgrid=False, showticklabels=False, zeroline=False,
        ),
        showlegend=True,
        legend=dict(
            orientation='h', x=0.5, xanchor='center', y=-0.12,
            font=dict(size=11, color='#1a2840'), bgcolor='rgba(0,0,0,0)',
            itemsizing='constant',
        ),
        hovermode='x unified',
    )
    return fig


def make_country_legend(countries_sorted: list) -> list:
    """Dash html elements: colored chip + country name."""
    from dash import html
    items = []
    for c in countries_sorted:
        color = COUNTRY_COLORS[c]
        items.append(
            html.Div([
                html.Span(style={
                    'display': 'inline-block',
                    'width': '14px', 'height': '14px',
                    'background-color': color,
                    'border-radius': '3px',
                    'margin-right': '6px',
                    'vertical-align': 'middle',
                }),
                html.Span(COUNTRIES[c], style={
                    'font-size': '12px',
                    'color': '#1a2840',
                    'vertical-align': 'middle',
                }),
            ], style={'margin': '3px 10px', 'display': 'inline-block'})
        )
    return items
