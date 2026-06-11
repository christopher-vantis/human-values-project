"""Social-gradient lollipop chart (Country Deep Dive tab).

Shows how one Schwartz score varies across social groups within one
country: age bands, education, urbanisation, gender, religiosity, and the
country-specific splits (East/West Germany, Swiss language regions).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import theme
from data_pipeline import GRADIENT_VARS


def _country_variables(df: pd.DataFrame, country: str) -> list[str]:
    """Gradient variable keys available for one country, in display order."""
    present = set(df[df['cntry'] == country]['variable'])
    return [v for v in GRADIENT_VARS if v in present]


def make_gradient_dots(df: pd.DataFrame, country: str, score_col: str,
                       score_label: str, color: str) -> go.Figure:
    """Lollipop panel of one Schwartz score across social groups.

    Args:
        df: Gradient aggregates (df_gradients).
        country: 'DE' or 'CH'.
        score_col: Score column (d_* or dim_*).
        score_label: Display name for the score.
        color: Marker colour (the dimension colour).

    Returns:
        Plotly figure with one subplot row per gradient variable.
    """
    sub  = df[df['cntry'] == country]
    keys = _country_variables(df, country)
    if not keys:
        fig = go.Figure()
        fig.add_annotation(text='No gradient data available.',
                           x=0.5, y=0.5, xref='paper', yref='paper',
                           showarrow=False,
                           font=dict(size=13, color=theme.MUTED))
        return fig

    groups_per_var = [len(sub[sub['variable'] == k]) for k in keys]
    fig = make_subplots(
        rows=len(keys), cols=1,
        shared_xaxes=True,
        row_heights=[max(g, 2) for g in groups_per_var],
        vertical_spacing=0.22 / len(keys),
        subplot_titles=[GRADIENT_VARS[k]['label'] for k in keys],
    )

    x_abs = float(sub[score_col].abs().max()) * 1.25 + 0.02
    for i, key in enumerate(keys, start=1):
        block = (sub[sub['variable'] == key]
                 .sort_values('group_order', ascending=False))
        # Stems from 0 to the value (None separates segments)
        stem_x, stem_y = [], []
        for _, row in block.iterrows():
            stem_x += [0, row[score_col], None]
            stem_y += [row['group'], row['group'], None]
        fig.add_trace(go.Scatter(
            x=stem_x, y=stem_y, mode='lines',
            line=dict(color=theme.hex_to_rgba(color, 0.35), width=2),
            hoverinfo='skip', showlegend=False), row=i, col=1)
        fig.add_trace(go.Scatter(
            x=block[score_col], y=block['group'],
            mode='markers',
            marker=dict(size=10, color=color,
                        line=dict(color='white', width=1.5)),
            customdata=block[['n']],
            hovertemplate=(f'<b>%{{y}}</b><br>{score_label}: '
                           'Δ = %{x:.3f}<br>n = %{customdata[0]} respondents'
                           '<extra></extra>'),
            showlegend=False), row=i, col=1)
        fig.update_yaxes(tickfont=dict(size=10.5, color=theme.TEXT),
                         showgrid=False, row=i, col=1)
        fig.update_xaxes(range=[-x_abs, x_abs], zeroline=True,
                         zerolinewidth=1.4,
                         zerolinecolor=theme.COLORS['border-dark'],
                         row=i, col=1)

    fig.update_xaxes(title_text=f'{score_label} (Δ-score)',
                     row=len(keys), col=1)
    fig.update_layout(
        height=140 + 30 * sum(groups_per_var),
        margin=dict(t=36, b=52, l=150, r=24),
    )
    fig.update_annotations(font=dict(size=11.5, color=theme.MUTED),
                           xanchor='left', x=0)
    return fig
