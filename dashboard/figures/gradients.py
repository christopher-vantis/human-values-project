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
                       score_label: str, color: str,
                       country_mean: float | None = None) -> go.Figure:
    """Lollipop panel of one Schwartz score across social groups.

    Δ-scores are person-centred, so 0 means "as important as the
    respondent's own average value" - NOT the national average. The
    optional dashed reference line marks the country-level mean so that
    panels where every group is negative (e.g. Power anywhere) read
    correctly as a universal low priority rather than a data error.

    Args:
        df: Gradient aggregates (df_gradients).
        country: ISO-2 ESS country code.
        score_col: Score column (d_* or dim_*).
        score_label: Display name for the score.
        color: Marker colour (the dimension colour).
        country_mean: Country-level weighted mean of the same score.

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

    # Data-driven range that always contains 0 and the country mean -
    # a symmetric range wastes half the panel for values like Power that
    # sit far below zero in every group
    anchors = [float(sub[score_col].min()), float(sub[score_col].max()), 0.0]
    if country_mean is not None:
        anchors.append(country_mean)
    pad  = 0.12 * (max(anchors) - min(anchors)) + 0.02
    x_lo, x_hi = min(anchors) - pad, max(anchors) + pad
    for i, key in enumerate(keys, start=1):
        block = (sub[sub['variable'] == key]
                 .sort_values('group_order', ascending=False))
        # Stems anchor at the country average (fallback 0), so stem length
        # directly shows each group's deviation - the social gradient
        anchor = country_mean if country_mean is not None else 0.0
        stem_x, stem_y = [], []
        for _, row in block.iterrows():
            stem_x += [anchor, row[score_col], None]
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
        fig.update_xaxes(range=[x_lo, x_hi], zeroline=True,
                         zerolinewidth=1.4,
                         zerolinecolor=theme.COLORS['border-dark'],
                         row=i, col=1)

    fig.update_xaxes(title_text=f'{score_label} (Δ-score)',
                     row=len(keys), col=1)
    fig.update_layout(
        height=140 + 30 * sum(groups_per_var),
        margin=dict(t=46, b=52, l=150, r=24),
    )
    fig.update_annotations(font=dict(size=11.5, color=theme.MUTED),
                           xanchor='left', x=0)

    if country_mean is not None:
        fig.add_vline(x=country_mean, line_dash='dot', line_width=1.5,
                      line_color=theme.COLORS['border-dark'], row='all', col=1)
        fig.add_annotation(
            x=country_mean, xref='x', y=1.0, yref='paper', yanchor='bottom',
            text=f'country average ({country_mean:+.2f})',
            showarrow=False, xanchor='center',
            font=dict(size=10, color=theme.COLORS['faint']))
    return fig
