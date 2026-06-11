"""Regional choropleth + regional indicator scatter (Country Deep Dive tab).

Maps NUTS-level weighted Schwartz scores onto GISCO boundaries for every
ESS11 country with NUTS region codes. Countries report different NUTS
levels (NUTS-1 to NUTS-3; NUTS-3 is rolled up to NUTS-2 upstream). Regions
with fewer than MIN_REGION_N respondents - or without any respondents -
are drawn in grey instead of pretending the estimate is reliable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import theme
from data_pipeline import COUNTRIES, MIN_REGION_N

# ESS country codes whose NUTS ids use a different prefix
_NUTS_PREFIX = {'GB': 'UK', 'GR': 'EL'}

# Regions with data but no map geometry (overseas, excluded for readability)
_NAME_FALLBACK = {'ES70': 'Canarias'}


def region_names(geojson: dict) -> dict[str, str]:
    """Map NUTS_ID -> NUTS_NAME from the trimmed GeoJSON."""
    names = {f['properties']['NUTS_ID']: f['properties']['NUTS_NAME']
             for f in geojson.get('features', [])}
    return {**_NAME_FALLBACK, **names}


def _country_features(geojson: dict, country: str, level: int) -> dict:
    """FeatureCollection trimmed to one country at one NUTS level."""
    prefix = _NUTS_PREFIX.get(country, country)
    feats = [f for f in geojson.get('features', [])
             if (f['properties']['NUTS_ID'].startswith(prefix)
                 and len(f['properties']['NUTS_ID']) == level + 2)]
    return {'type': 'FeatureCollection', 'features': feats}


def _no_map_figure(country: str) -> go.Figure:
    """Empty state for countries without NUTS geometry (IL, UA)."""
    fig = go.Figure()
    fig.add_annotation(
        text=(f'No regional map available for {COUNTRIES.get(country, country)}'
              '<br>(ESS region codes lie outside the NUTS system).<br>'
              'Social gradients below still apply.'),
        x=0.5, y=0.5, showarrow=False, xref='paper', yref='paper',
        font=dict(size=13, color=theme.MUTED))
    fig.update_layout(height=520, margin=dict(t=48, b=8, l=8, r=8))
    return fig


def _grey_trace(gj: dict, regions: list[str], names: dict[str, str],
                reason: dict[str, str]) -> go.Choropleth:
    """Grey overlay for regions without a reliable estimate."""
    return go.Choropleth(
        geojson=gj,
        locations=regions,
        z=[0] * len(regions),
        featureidkey='properties.NUTS_ID',
        colorscale=[[0, '#d4dae6'], [1, '#d4dae6']],
        showscale=False,
        marker=dict(line=dict(color='white', width=1)),
        customdata=[[names.get(r, r), reason[r]] for r in regions],
        hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}'
                      '<extra></extra>',
    )


def make_choropleth(df_regional: pd.DataFrame, geojson: dict, country: str,
                    score_col: str, score_label: str) -> go.Figure:
    """Choropleth of one Schwartz score across a country's NUTS regions.

    Args:
        df_regional: Regional aggregates (df_regional).
        geojson: Trimmed GISCO FeatureCollection (load_geojson()).
        country: ISO-2 ESS country code.
        score_col: Score column (d_* or dim_*).
        score_label: Display name for the score.

    Returns:
        Plotly choropleth figure with a diverging scale centred at 0, or
        an explanatory empty state if the country has no NUTS regions.
    """
    sub = df_regional[df_regional['cntry'] == country].copy()
    if sub.empty:
        return _no_map_figure(country)

    level = int(sub['region'].str.len().mode()[0]) - 2
    gj    = _country_features(geojson, country, level)
    names = region_names(geojson)

    reliable = sub[~sub['below_min_n']]
    small    = sub[sub['below_min_n']]
    missing  = [f['properties']['NUTS_ID'] for f in gj['features']
                if f['properties']['NUTS_ID'] not in set(sub['region'])]

    z_max = max(float(reliable[score_col].abs().max())
                if not reliable.empty else 0.0, 0.05)
    fig = go.Figure()
    if not reliable.empty:
        fig.add_trace(go.Choropleth(
            geojson=gj,
            locations=reliable['region'],
            z=reliable[score_col],
            featureidkey='properties.NUTS_ID',
            colorscale=theme.DIVERGING_SCALE,
            zmid=0, zmin=-z_max, zmax=z_max,
            marker=dict(line=dict(color='white', width=1)),
            colorbar=dict(title=dict(text='Δ-score', side='right'),
                          thickness=12, len=0.62, tickfont=dict(size=10)),
            customdata=np.stack(
                [reliable['region'].map(names).fillna(reliable['region']),
                 reliable[score_col].round(3),
                 reliable['n']], axis=1),
            hovertemplate=(f'<b>%{{customdata[0]}}</b><br>{score_label}: '
                           'Δ = %{customdata[1]}<br>n = %{customdata[2]} '
                           'respondents<extra></extra>'),
        ))

    grey_reason = {r: f'n < {MIN_REGION_N} respondents - estimate suppressed'
                   for r in small['region']}
    grey_reason.update({r: 'No ESS11 respondents sampled' for r in missing})
    grey_regions = list(small['region']) + missing
    if grey_regions:
        fig.add_trace(_grey_trace(gj, grey_regions, names, grey_reason))

    fig.update_geos(
        fitbounds='locations',
        visible=False,
        projection_type='mercator',
        bgcolor='rgba(0,0,0,0)',
    )
    fig.update_layout(
        height=520,
        margin=dict(t=48, b=8, l=8, r=8),
        title=dict(
            text=(f'<b>{score_label}</b> across '
                  f'{COUNTRIES.get(country, country)} (NUTS-{level})'),
            font=dict(size=14, color=theme.INK),
        ),
        dragmode=False,
    )
    return fig


def make_regional_scatter(df_regional: pd.DataFrame, df_indicators: pd.DataFrame,
                          geojson: dict, country: str, score_col: str,
                          score_label: str, indicator_key: str,
                          indicator_label: str) -> go.Figure:
    """Scatter: regional Schwartz score vs. a Eurostat regional indicator.

    Holding national institutions constant, this asks whether value
    priorities track regional social structure within one country.

    Args:
        df_regional: Regional aggregates.
        df_indicators: Long Eurostat indicator table (region, indicator,
            value, year).
        geojson: Trimmed GISCO FeatureCollection (for region names).
        country: ISO-2 ESS country code.
        score_col: Score column (d_* or dim_*).
        score_label: Display name for the score.
        indicator_key: Key in the indicator table.
        indicator_label: Display name for the indicator.

    Returns:
        Plotly scatter figure with OLS fit and an honest small-N note.
    """
    from figures.scatter import _regress_ci

    names = region_names(geojson)
    sub = df_regional[(df_regional['cntry'] == country)
                      & (~df_regional['below_min_n'])].copy()
    ind = df_indicators[df_indicators['indicator'] == indicator_key]
    sub = sub.merge(ind[['region', 'value', 'year']], on='region', how='inner')

    fig = go.Figure()
    if len(sub) < 3:
        fig.add_annotation(
            text='Not enough regions with reliable estimates and indicator '
                 'data for this combination.',
            x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False,
            font=dict(size=13, color=theme.MUTED))
        fig.update_layout(height=440)
        return fig

    x = sub['value'].values.astype(float)
    y = sub[score_col].values.astype(float)
    reg = _regress_ci(x, y)
    if reg:
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_hi']), mode='lines',
            line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['ci_lo']), mode='lines',
            line=dict(width=0), fill='tonexty',
            fillcolor=theme.hex_to_rgba(theme.PRIMARY, 0.08),
            showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(
            x=list(reg['x_fit']), y=list(reg['y_fit']), mode='lines',
            line=dict(color=theme.hex_to_rgba(theme.PRIMARY, 0.8), width=2),
            showlegend=False, hoverinfo='skip'))

    labels = sub['region'].map(names).fillna(sub['region'])
    # Region-name labels clutter quickly; show them only on sparse maps
    mode = 'markers+text' if len(sub) <= 14 else 'markers'
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode=mode,
        text=labels,
        textposition='top center',
        textfont=dict(size=9.5, color=theme.MUTED),
        marker=dict(size=9, color=theme.PRIMARY,
                    line=dict(color='white', width=1.5)),
        customdata=np.stack([labels, sub['n'], sub['year']], axis=1),
        hovertemplate=(f'<b>%{{customdata[0]}}</b><br>'
                       f'{indicator_label}: %{{x:.1f}} (%{{customdata[2]}})<br>'
                       f'{score_label}: Δ = %{{y:.3f}}<br>'
                       'n = %{customdata[1]} respondents<extra></extra>'),
        showlegend=False,
    ))

    if reg:
        fig.add_annotation(
            text=(f"r = {reg['r']:+.2f}   p = {reg['p']:.3f}   "
                  f"N = {reg['n']} regions (exploratory)"),
            xref='paper', yref='paper', x=0.98, y=0.02,
            xanchor='right', yanchor='bottom', showarrow=False,
            font=dict(size=10, color=theme.MUTED),
            bgcolor='rgba(241,244,250,0.9)', borderpad=4)

    fig.update_xaxes(title_text=indicator_label)
    fig.update_yaxes(title_text=f'{score_label} (Δ-score)',
                     zeroline=True, zerolinewidth=1.5)
    fig.update_layout(height=440, margin=dict(t=24, b=56, l=70, r=24))
    return fig
