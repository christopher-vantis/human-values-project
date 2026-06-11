"""Central design tokens and the shared Plotly template.

Single source of truth for every colour, font, and spacing decision used by
the dashboard. The CSS custom properties in assets/style.css mirror the
values defined here; change them in both places when rebranding.

Importing this module registers (and activates) the ``values`` Plotly
template so every figure inherits consistent fonts, margins, and colours.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# ── Typography ─────────────────────────────────────────────────────────────────
FONT_FAMILY = (
    "Inter, 'Inter Fallback', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, sans-serif"
)

# ── Core palette (mirrored as CSS variables in assets/style.css) ──────────────
COLORS = {
    'bg':          '#f6f7fb',   # page background
    'surface':     '#ffffff',   # card background
    'surface-alt': '#f1f4fa',   # control panels, info boxes
    'border':      '#e3e8f2',
    'border-dark': '#c9d4e6',
    'ink':         '#0f1c30',   # near-black text
    'text':        '#24304a',
    'muted':       '#64748f',
    'faint':       '#94a3bd',
    'primary':     '#2563eb',   # brand blue
    'primary-dark': '#1d4ed8',
}

BG_COLOR  = COLORS['bg']
SURFACE   = COLORS['surface']
RADAR_BG  = '#eef2f9'
INK       = COLORS['ink']
TEXT      = COLORS['text']
MUTED     = COLORS['muted']
PRIMARY   = COLORS['primary']
GRID      = '#dde4f0'

# ── Schwartz higher-order dimension colours ────────────────────────────────────
DIM_COLORS = {
    'Openness to Change': '#2563eb',
    'Self-Transcendence': '#8b5cf6',
    'Conservation':       '#0d9488',
    'Self-Enhancement':   '#dc2626',
}

CLUSTER_COLORS = ['#2563eb', '#dc2626', '#0d9488', '#d97706', '#8b5cf6', '#db2777']

# Sequential / diverging scale for choropleths (centred at 0)
DIVERGING_SCALE = [
    [0.00, '#1d4ed8'],
    [0.25, '#93b4f5'],
    [0.50, '#f4f6fb'],
    [0.75, '#f0a48c'],
    [1.00, '#c2410c'],
]

HEATMAP_SCALE = [
    [0.00, '#2166ac'],
    [0.25, '#92c5de'],
    [0.50, '#f7f7f7'],
    [0.75, '#f4a582'],
    [1.00, '#d6604d'],
]


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#rrggbb`` to an ``rgba(r,g,b,a)`` string.

    Args:
        hex_color: Colour in 6-digit hex notation (leading ``#`` optional).
        alpha: Opacity in [0, 1].

    Returns:
        CSS rgba() string.
    """
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def _build_template() -> go.layout.Template:
    """Build the shared Plotly template used by all dashboard figures."""
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(family=FONT_FAMILY, size=12.5, color=TEXT),
        title=dict(font=dict(size=15, color=INK), x=0.5, xanchor='center'),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin=dict(t=56, b=56, l=64, r=32),
        hoverlabel=dict(
            bgcolor='white',
            bordercolor=COLORS['border-dark'],
            font=dict(family=FONT_FAMILY, size=12, color=INK),
        ),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID,
                   title=dict(font=dict(size=12, color=MUTED))),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID,
                   title=dict(font=dict(size=12, color=MUTED))),
        colorway=list(DIM_COLORS.values()),
    )
    return template


pio.templates['values'] = _build_template()
pio.templates.default = 'values'
