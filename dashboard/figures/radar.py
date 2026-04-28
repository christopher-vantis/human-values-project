import numpy as np
import plotly.graph_objects as go
import pandas as pd

from data_pipeline import (
    COUNTRIES, COUNTRY_FLAGS, VALUE_KEYS, VALUE_LABELS,
    DIM_COLORS, VALUE_TO_DIM, COUNTRY_COLORS,
    BG_COLOR, RADAR_BG, YEAR_TO_ROUND, DELTA_RANGE,
    hex_to_rgba,
)

# ── Angular positions ─────────────────────────────────────────────────────────
# 10 values at 36° each, clockwise from top (0° = 12 o'clock)
N_VALUES  = 10
_DEG_STEP = 360 / N_VALUES
ANGLES_DEG = [i * _DEG_STEP for i in range(N_VALUES)]   # [0, 36, 72, ..., 324]

# Angular axis tick labels at spoke positions
_TICK_VALS_DEG = ANGLES_DEG
_TICK_TEXT_DEG = [VALUE_LABELS[k] for k in VALUE_KEYS]

# Radial ticks shown inside the chart
_RTICK_VALS = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
_RTICK_TEXT = ['-1.0', '-0.5', '0', '+0.5', '+1.0', '+1.5']

# Arcs drawn just outside the data range
_ARC_R      = DELTA_RANGE[1] + 0.22    # radius of the arc line
_LABEL_R    = DELTA_RANGE[1] + 0.55    # radius of the arc label
_RANGE_EXT  = DELTA_RANGE[1] + 0.80    # full radial axis range (includes labels)

# Higher-order arc definitions: (label, start_deg, end_deg, color)
# Clockwise from top. Openness spans HE(288°)→ST(324°)→SD(0°); SE ends at 270°.
_ARCS = [
    ('Openness to Change',  270,  18, DIM_COLORS['Openness to Change']),
    ('Self-Transcendence',   18,  90, DIM_COLORS['Self-Transcendence']),
    ('Conservation',         90, 198, DIM_COLORS['Conservation']),
    ('Self-Enhancement',    198, 270, DIM_COLORS['Self-Enhancement']),
]


def _arc_theta(start: float, end: float, n: int = 60) -> np.ndarray:
    """Angular positions (degrees) for an arc, handling wrap-around."""
    if end <= start:
        end += 360
    return np.linspace(start, end, n)


def _polar_base_layout(show_legend: bool = False) -> dict:
    return dict(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[DELTA_RANGE[0], _RANGE_EXT],
                tickvals=_RTICK_VALS,
                ticktext=_RTICK_TEXT,
                gridcolor='#c0ccd8',
                linecolor='#7a90b0',
                tickfont=dict(size=8.5, color='#5a6a80'),
                angle=90,
                # Hide the axis line beyond tickvals to keep it clean
                showline=False,
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=_TICK_VALS_DEG,
                ticktext=_TICK_TEXT_DEG,
                tickfont=dict(size=10.5, color='#1a2840'),
                direction='clockwise',
                rotation=90,
                gridcolor='#c8d4e0',
                linecolor='#c0ccd8',
            ),
            bgcolor=RADAR_BG,
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        showlegend=show_legend,
        legend=dict(
            orientation='h', x=0.5, xanchor='center', y=-0.07,
            font=dict(size=11), bgcolor='rgba(0,0,0,0)',
            itemsizing='constant',
        ),
        margin=dict(t=100, b=20, l=20, r=20),
        height=540,
    )


def _add_arcs(fig: go.Figure) -> None:
    """Add higher-order dimension arc lines to the figure (no text labels)."""
    for label, start_deg, end_deg, color in _ARCS:
        theta = _arc_theta(start_deg, end_deg)
        r_arr = [_ARC_R] * len(theta)
        fig.add_trace(go.Scatterpolar(
            r=r_arr,
            theta=theta,
            thetaunit='degrees',
            mode='lines',
            line=dict(color=color, width=10),
            showlegend=False,
            hoverinfo='skip',
        ))


def _no_data_figure() -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text='No data available for this selection.',
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color='#5a6a80'),
        xref='paper', yref='paper',
    )
    fig.update_layout(paper_bgcolor=BG_COLOR, height=540,
                      margin=dict(t=80, b=20, l=20, r=20))
    return fig


def make_radar_single(df: pd.DataFrame, country: str, year: int) -> go.Figure:
    row = df[(df['cntry'] == country) & (df['year'] == year)]
    if row.empty:
        return _no_data_figure()

    deltas   = [float(row[f'd_{k}'].values[0]) for k in VALUE_KEYS]
    r_vals   = deltas + [deltas[0]]
    th_vals  = ANGLES_DEG + [ANGLES_DEG[0]]   # close the polygon

    fig = go.Figure()
    _add_arcs(fig)   # arcs first (behind the polygon)

    fig.add_trace(go.Scatterpolar(
        r=r_vals,
        theta=th_vals,
        thetaunit='degrees',
        fill='toself',
        fillcolor=hex_to_rgba('#3a7ad4', 0.17),
        line=dict(color='#1a5fb4', width=2.2),
        marker=dict(color='#1a5fb4', size=7,
                    line=dict(color='white', width=1.5)),
        mode='lines+markers',
        name=COUNTRIES[country],
        hovertemplate=(
            '<b>%{customdata}</b><br>Δ = %{r:.3f}<extra></extra>'
        ),
        customdata=[VALUE_LABELS[k] for k in VALUE_KEYS] + [VALUE_LABELS[VALUE_KEYS[0]]],
    ))

    ess_round = YEAR_TO_ROUND[year]
    flag = COUNTRY_FLAGS.get(country, '')
    title_text = (
        f'{flag}  <b>{COUNTRIES[country]}</b>'
        f'   ·   ESS Round {ess_round} ({year})'
    )
    layout = _polar_base_layout(show_legend=False)
    layout['title'] = dict(
        text=title_text, x=0.5, xanchor='center',
        font=dict(size=15, color='#0d1b2a', family='sans-serif'),
    )
    fig.update_layout(**layout)
    return fig


def make_radar_comparison(df: pd.DataFrame, countries: list, year: int) -> go.Figure:
    fig = go.Figure()
    _add_arcs(fig)   # arcs first so country polygons render on top
    found_any = False

    for country in countries:
        row = df[(df['cntry'] == country) & (df['year'] == year)]
        if row.empty:
            continue
        found_any = True
        deltas  = [float(row[f'd_{k}'].values[0]) for k in VALUE_KEYS]
        r_vals  = deltas + [deltas[0]]
        th_vals = ANGLES_DEG + [ANGLES_DEG[0]]
        color   = COUNTRY_COLORS[country]

        fig.add_trace(go.Scatterpolar(
            r=r_vals,
            theta=th_vals,
            thetaunit='degrees',
            fill='toself',
            fillcolor=hex_to_rgba(color, 0.08),
            line=dict(color=color, width=2),
            marker=dict(color=color, size=5,
                        line=dict(color='white', width=1)),
            mode='lines+markers',
            name=COUNTRIES[country],
            hovertemplate=(
                f'<b>{COUNTRIES[country]}</b>'
                '<br>%{customdata}: Δ = %{r:.3f}<extra></extra>'
            ),
            customdata=[VALUE_LABELS[k] for k in VALUE_KEYS] + [VALUE_LABELS[VALUE_KEYS[0]]],
        ))

    if not found_any:
        return _no_data_figure()

    ess_round = YEAR_TO_ROUND[year]
    layout = _polar_base_layout(show_legend=True)
    layout['title'] = dict(
        text=f'ESS Round {ess_round} ({year})   ·   Country Comparison',
        x=0.5, xanchor='center',
        font=dict(size=15, color='#0d1b2a', family='sans-serif'),
    )
    fig.update_layout(**layout)
    return fig
