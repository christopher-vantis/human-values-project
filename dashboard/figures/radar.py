"""Schwartz value radar chart (Country Profile tab, ESS Round 11).

Δ-scores are person-centred and reverse-coded upstream, so positive spokes
genuinely mean above-average relative priority.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import theme
from data_pipeline import (
    COUNTRIES, COUNTRY_FLAGS, DELTA_RANGE, ESS_ROUND, ESS_YEAR,
    VALUE_KEYS, VALUE_LABELS,
)

# ── Angular positions: 10 values at 36° each, clockwise from top ───────────────
N_VALUES   = 10
_DEG_STEP  = 360 / N_VALUES
ANGLES_DEG = [i * _DEG_STEP for i in range(N_VALUES)]

_TICK_TEXT = [VALUE_LABELS[k] for k in VALUE_KEYS]

_RTICK_VALS = [-1.0, -0.5, 0.0, 0.5, 1.0]
_RTICK_TEXT = ['-1.0', '-0.5', '0', '+0.5', '+1.0']

# Higher-order arcs just outside the data range
_ARC_R     = DELTA_RANGE[1] + 0.22
_RANGE_EXT = DELTA_RANGE[1] + 0.55

# (label, start_deg, end_deg) - clockwise from top; colours from the theme
_ARCS = [
    ('Openness to Change',  270,  18),
    ('Self-Transcendence',   18,  90),
    ('Conservation',         90, 198),
    ('Self-Enhancement',    198, 270),
]


def _arc_theta(start: float, end: float, n: int = 60) -> np.ndarray:
    """Angular positions (degrees) for an arc, handling wrap-around."""
    if end <= start:
        end += 360
    return np.linspace(start, end, n)


def _polar_base_layout() -> dict:
    """Shared polar layout for the radar figure."""
    return dict(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[DELTA_RANGE[0], _RANGE_EXT],
                tickvals=_RTICK_VALS,
                ticktext=_RTICK_TEXT,
                gridcolor=theme.GRID,
                linecolor=theme.COLORS['border-dark'],
                tickfont=dict(size=9, color=theme.MUTED),
                angle=90,
                showline=False,
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=ANGLES_DEG,
                ticktext=_TICK_TEXT,
                tickfont=dict(size=11, color=theme.INK),
                direction='clockwise',
                rotation=90,
                gridcolor=theme.GRID,
                linecolor=theme.COLORS['border-dark'],
            ),
            bgcolor=theme.RADAR_BG,
        ),
        showlegend=False,
        margin=dict(t=80, b=24, l=40, r=40),
        height=540,
    )


def _add_arcs(fig: go.Figure) -> None:
    """Draw the four higher-order dimension arcs outside the data range."""
    for label, start_deg, end_deg in _ARCS:
        thetas = _arc_theta(start_deg, end_deg)
        fig.add_trace(go.Scatterpolar(
            r=[_ARC_R] * len(thetas),
            theta=thetas,
            thetaunit='degrees',
            mode='lines',
            line=dict(color=theme.DIM_COLORS[label], width=10),
            showlegend=False,
            hoverinfo='skip',
        ))


def no_data_figure(height: int = 540) -> go.Figure:
    """Empty-state figure shown when a selection has no data."""
    fig = go.Figure()
    fig.add_annotation(
        text='No data available for this selection.',
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=theme.MUTED),
        xref='paper', yref='paper',
    )
    fig.update_layout(height=height, margin=dict(t=60, b=20, l=20, r=20))
    return fig


def make_radar_single(df: pd.DataFrame, country: str) -> go.Figure:
    """Radar chart of one country's ESS11 Schwartz value profile.

    Args:
        df: Country-level aggregates (df_main).
        country: ISO-2 country code.

    Returns:
        Plotly figure (empty-state figure if the country is missing).
    """
    row = df[df['cntry'] == country]
    if row.empty:
        return no_data_figure()

    deltas  = [float(row[f'd_{k}'].values[0]) for k in VALUE_KEYS]
    r_vals  = deltas + [deltas[0]]
    th_vals = ANGLES_DEG + [ANGLES_DEG[0]]

    fig = go.Figure()
    _add_arcs(fig)
    fig.add_trace(go.Scatterpolar(
        r=r_vals,
        theta=th_vals,
        thetaunit='degrees',
        fill='toself',
        fillcolor=theme.hex_to_rgba(theme.PRIMARY, 0.16),
        line=dict(color=theme.PRIMARY, width=2.2),
        marker=dict(color=theme.PRIMARY, size=7,
                    line=dict(color='white', width=1.5)),
        mode='lines+markers',
        name=COUNTRIES[country],
        hovertemplate='<b>%{customdata}</b><br>Δ = %{r:.3f}<extra></extra>',
        customdata=[VALUE_LABELS[k] for k in VALUE_KEYS]
                   + [VALUE_LABELS[VALUE_KEYS[0]]],
    ))

    flag = COUNTRY_FLAGS.get(country, '')
    layout = _polar_base_layout()
    layout['title'] = dict(
        text=(f'{flag}  <b>{COUNTRIES[country]}</b>'
              f'   ·   ESS Round {ESS_ROUND} ({ESS_YEAR})'),
        x=0.5, xanchor='center',
        font=dict(size=15, color=theme.INK),
    )
    fig.update_layout(**layout)
    return fig
