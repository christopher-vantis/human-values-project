"""Native Schwartz circumplex wheel for the About page.

Replaces the scanned textbook JPEG with a crisp, interactive Plotly wheel:
ten value sectors coloured by their higher-order dimension, hover cards
with each value's motivational goal, and dimension labels around the ring.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

import theme
from data_pipeline import VALUE_KEYS, VALUE_LABELS, VALUE_TO_DIM

# Motivational goal one-liners (Schwartz, 2012)
VALUE_GOALS = {
    'SD': 'Independent thought and action - choosing, creating, exploring.',
    'UN': 'Understanding, tolerance, and protection of all people and nature.',
    'BE': 'Preserving and enhancing the welfare of close others.',
    'TR': 'Respect for and commitment to cultural or religious customs.',
    'CO': 'Restraint of actions likely to upset others or violate norms.',
    'SE': 'Safety, harmony, and stability of society and self.',
    'PO': 'Social status and prestige, control over people and resources.',
    'AC': 'Personal success through demonstrating competence.',
    'HE': 'Pleasure and sensuous gratification for oneself.',
    'ST': 'Excitement, novelty, and challenge in life.',
}

_N = len(VALUE_KEYS)
_STEP = 360 / _N
_CENTERS = [i * _STEP for i in range(_N)]

# Dimension label positions: midpoints of the four arcs (degrees, clockwise
# from top), matching the radar's arc layout
_DIM_LABELS = [
    ('Openness<br>to Change',  324),
    ('Self-<br>Transcendence',  54),
    ('Conservation',           144),
    ('Self-<br>Enhancement',   234),
]


def make_circumplex() -> go.Figure:
    """Build the interactive circumplex wheel.

    Returns:
        Plotly figure: 10 Barpolar sectors + dimension ring labels,
        configured as a static-layout, hover-only graphic.
    """
    colors = [theme.DIM_COLORS[VALUE_TO_DIM[k]] for k in VALUE_KEYS]
    fig = go.Figure()
    fig.add_trace(go.Barpolar(
        theta=_CENTERS,
        width=[_STEP - 1.2] * _N,
        r=[0.55] * _N,
        base=[0.55] * _N,
        marker=dict(color=[theme.hex_to_rgba(c, 0.88) for c in colors],
                    line=dict(color='white', width=2)),
        customdata=np.stack(
            [[VALUE_LABELS[k] for k in VALUE_KEYS],
             [VALUE_GOALS[k] for k in VALUE_KEYS],
             [VALUE_TO_DIM[k] for k in VALUE_KEYS]], axis=1),
        hovertemplate=('<b>%{customdata[0]}</b><br>'
                       '%{customdata[1]}<br>'
                       '<i>%{customdata[2]}</i><extra></extra>'),
        showlegend=False,
    ))
    # Dimension labels just outside the ring
    fig.add_trace(go.Scatterpolar(
        r=[1.38] * len(_DIM_LABELS),
        theta=[deg for _, deg in _DIM_LABELS],
        mode='text',
        text=[lbl for lbl, _ in _DIM_LABELS],
        textfont=dict(size=12.5, color=theme.INK, weight=700),
        hoverinfo='skip',
        showlegend=False,
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1.62]),
            angularaxis=dict(
                tickmode='array',
                tickvals=_CENTERS,
                ticktext=[VALUE_LABELS[k] for k in VALUE_KEYS],
                tickfont=dict(size=11, color=theme.TEXT),
                direction='clockwise',
                rotation=90,
                showgrid=False,
                showline=False,
            ),
            bgcolor='rgba(0,0,0,0)',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        height=460,
        margin=dict(t=30, b=30, l=60, r=60),
        annotations=[dict(
            text='10 values<br>4 dimensions',
            x=0.5, y=0.5, xref='paper', yref='paper',
            showarrow=False,
            font=dict(size=11.5, color=theme.MUTED),
        )],
    )
    return fig
