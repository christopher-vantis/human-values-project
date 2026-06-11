"""Dash application entry point.

Responsibilities:
  - Load the precomputed DataFrames from the pipeline
  - Create the Dash app and register all callbacks
  - Expose the WSGI server for Gunicorn

Layout objects live in layouts.py, data access in data_pipeline.py, and
design tokens / the Plotly template in theme.py. Everything shown refers
to ESS Round 11 (2023) - the newest available data.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import dash_mantine_components as dmc
import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

import data_pipeline as dp
import theme
from figures.choropleth import make_choropleth, make_regional_scatter
from figures.gradients import make_gradient_dots
from figures.radar import make_radar_single
from figures.scatter import make_corr_heatmap, make_scatter_all, make_scatter_single
from figures.value_space import make_value_space_figure
from layouts import (
    DEFAULT_COUNTRY, SCORE_COLORS, SCORE_LABELS,
    build_tab_corr, card, landing, make_cluster_summary,
    register_expand_callbacks, tab1, tab2, tab_deep,
)

# ── Data (precomputed; no raw microdata needed on the server) ──────────────────
DF_MAIN     = dp.load_data()
DF_SCATTER  = dp.load_scatter_data()
DF_REGIONAL = dp.load_regional()
DF_GRAD     = dp.load_gradients()
DF_REG_IND  = dp.load_regional_indicators()
DF_GOV_EXP  = dp.load_gov_exp()
GEOJSON     = dp.load_geojson()
MLM_RESULTS = dp.load_mlm_results()
DF_IND, INDICATOR_SENTENCES = dp.load_indicators()

# Regional indicators actually available per deep-dive country
_IND_BY_COUNTRY = {
    cntry: [key for key in dp.REGIONAL_INDICATOR_META
            if (DF_REG_IND[(DF_REG_IND['indicator'] == key)
                           & (DF_REG_IND['region'].str.startswith(cntry))]
                .shape[0] >= 3)]
    for cntry in dp.DEEP_DIVE_COUNTRIES
}

# The heatmap is a pure function of precomputed data - build it once
_HEATMAP_FIG = make_corr_heatmap(DF_SCATTER)
tab_corr = build_tab_corr(_HEATMAP_FIG, MLM_RESULTS)

# ── App ────────────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    title='Little Project on Human Values',
    suppress_callback_exceptions=True,
    external_stylesheets=dmc.styles.ALL,
)

_TABS = [
    ('About',             'tab-0'),
    ('Country Profile',   'tab-1'),
    ('Country Deep Dive', 'tab-deep'),
    ('Correlations',      'tab-corr'),
    ('Value Space',       'tab-2'),
]

app.layout = dmc.MantineProvider(
    theme={'fontFamily': theme.FONT_FAMILY, 'primaryColor': 'blue'},
    children=html.Div([
        html.Div([
            html.H1('Little Project on Human Values', className='main-title'),
            html.P('Schwartz basic human values across Europe · ESS Round 11 '
                   '(2023) · regions, social groups, and macro context.',
                   className='main-subtitle'),
            html.P('by Christopher Vantis', className='main-byline'),
        ], className='header'),

        dcc.Tabs(
            id='main-tabs',
            value='tab-0',
            className='main-tabs',
            children=[dcc.Tab(label=label, value=value, className='tab',
                              selected_className='tab--selected')
                      for label, value in _TABS],
        ),
        html.Div(id='tab-content', className='outer-tab-content'),
    ], className='app-wrapper'),
)

for _gid in ('t1-radar', 't2vs-graph'):
    register_expand_callbacks(app, _gid)


# ── Tab routing + hero navigation ──────────────────────────────────────────────

@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    """Swap the visible tab content."""
    return {'tab-0': landing, 'tab-1': tab1, 'tab-deep': tab_deep,
            'tab-corr': tab_corr, 'tab-2': tab2}[tab]


@app.callback(
    Output('main-tabs', 'value'),
    Input('hero-btn-profile', 'n_clicks'),
    Input('hero-btn-deep', 'n_clicks'),
    prevent_initial_call=True,
)
def hero_navigate(profile_clicks, deep_clicks):
    """Hero call-to-action buttons jump straight into the analysis tabs.

    The guard is required because the buttons mount dynamically with the
    landing tab, which re-fires this callback with zero clicks.
    """
    if not profile_clicks and not deep_clicks:
        raise PreventUpdate
    return 'tab-1' if ctx.triggered_id == 'hero-btn-profile' else 'tab-deep'


# ── Tab 1 - Country Profile ────────────────────────────────────────────────────

@app.callback(Output('t1-radar', 'figure'), Input('t1-country', 'value'))
def update_t1(country):
    """Redraw the radar for the selected country."""
    return make_radar_single(DF_MAIN, country)


def _stat(label: str, value: str) -> html.Div:
    """One fact item in the country facts card."""
    return html.Div([
        html.Div(label, className='fact-label'),
        html.Div(value, className='fact-value'),
    ], className='fact-item')


def _indicator_item(col: str, ind_row, sentences: dict) -> html.Div:
    """One structural-indicator row with hover tooltip."""
    meta     = dp.INDICATOR_META[col]
    sentence = sentences.get(col, '')
    v, yr = (None, None) if ind_row is None else (
        ind_row.get(col), ind_row.get(col + '_year'))
    yr = int(yr) if yr and not pd.isna(yr) else None
    na = v is None or (isinstance(v, float) and math.isnan(v))
    val_str = 'n/a' if na else (
        f'{v:.3f}' if col == 'vdem_ldi' else
        f'{v:.0f}' if col == 'estat_gdp_pps' else f'{v:.1f}')
    yr_str = f' ({yr})' if yr and not na else ''
    return html.Div([
        html.Div([
            html.Span(meta['label'], className='indicator-name'),
            html.Span(f'{val_str} {meta["unit"]}{yr_str}',
                      className='indicator-value'
                                + (' indicator-value--na' if na else '')),
        ], className='indicator-line'),
        html.Div(sentence, className='indicator-sentence'),
        html.Div([
            html.P(meta.get('desc', ''), className='indicator-tooltip-desc'),
            html.P(meta['source'], className='indicator-tooltip-source'),
        ], className='indicator-tooltip'),
    ], className='indicator-row')


@app.callback(Output('t1-country-info', 'children'),
              Input('t1-country', 'value'))
def update_t1_info(country):
    """Country facts card + 12 structural indicators."""
    info = dp.COUNTRY_INFO.get(country)
    if not info:
        return []
    capital, pop_m, area_km2, system, eu = info
    n_resp = int(DF_MAIN.loc[DF_MAIN['cntry'] == country, 'n'].iloc[0]) \
        if (DF_MAIN['cntry'] == country).any() else 0

    facts = card(html.Div([
        _stat('Capital', capital),
        _stat('Population', f'{pop_m:.1f} M'),
        _stat('Density', f'{round(pop_m * 1e6 / area_km2):,} / km²'),
        _stat('System', system),
        _stat('EU status', eu),
        _stat('ESS11 sample', f'{n_resp:,} respondents'),
    ], className='facts-row'))

    ind_row = DF_IND.loc[country] if country in DF_IND.index else None
    sents   = INDICATOR_SENTENCES.get(country, {})
    indicators = card([
        html.P('Structural Indicators', className='card-title'),
        *[_indicator_item(col, ind_row, sents) for col in dp.INDICATOR_META],
        html.P('Hover over a row for the indicator description and source.',
               className='side-note'),
    ])
    return html.Div([facts, indicators])


# ── Tab Deep Dive ──────────────────────────────────────────────────────────────

@app.callback(
    Output('td-indicator', 'data'),
    Output('td-indicator', 'value'),
    Output('td-region-note', 'children'),
    Input('td-country', 'value'),
    State('td-indicator', 'value'),
)
def update_td_country(country, current_indicator):
    """Refresh the indicator list + sample note when the country changes."""
    keys = _IND_BY_COUNTRY.get(country, [])
    data = [{'value': k, 'label': dp.REGIONAL_INDICATOR_META[k]['label']}
            for k in keys]
    value = current_indicator if current_indicator in keys else (
        keys[0] if keys else None)

    sub = DF_REGIONAL[DF_REGIONAL['cntry'] == country]
    n_ok = int((~sub['below_min_n']).sum())
    note = (f'{n_ok} regions with reliable estimates '
            f'(n ≥ {dp.MIN_REGION_N}); {len(sub) - n_ok} suppressed.')
    if country == 'DE':
        note += ' Bremen has no ESS11 respondents.'
    return data, value, note


@app.callback(
    Output('td-choropleth', 'figure'),
    Input('td-country', 'value'),
    Input('td-score', 'value'),
)
def update_td_choropleth(country, score):
    """Regional choropleth of the selected score."""
    return make_choropleth(DF_REGIONAL, GEOJSON, country,
                           score, SCORE_LABELS[score])


@app.callback(
    Output('td-reg-scatter', 'figure'),
    Output('td-indicator-desc', 'children'),
    Input('td-country', 'value'),
    Input('td-score', 'value'),
    Input('td-indicator', 'value'),
)
def update_td_scatter(country, score, indicator):
    """Regional value score vs. the chosen Eurostat indicator."""
    if not indicator:
        raise PreventUpdate
    meta = dp.REGIONAL_INDICATOR_META[indicator]
    fig = make_regional_scatter(DF_REGIONAL, DF_REG_IND, GEOJSON, country,
                                score, SCORE_LABELS[score],
                                indicator, meta['label'])
    return fig, f"{meta['desc']} Source: {meta['source']}."


@app.callback(
    Output('td-gradients', 'figure'),
    Input('td-country', 'value'),
    Input('td-score', 'value'),
)
def update_td_gradients(country, score):
    """Social-gradient lollipops for the selected score."""
    return make_gradient_dots(DF_GRAD, country, score,
                              SCORE_LABELS[score], SCORE_COLORS[score])


# ── Tab Corr - Correlations ────────────────────────────────────────────────────

@app.callback(
    Output('tc-x-var', 'value'),
    Output('tc-y-var', 'value'),
    Input('tc-heatmap', 'clickData'),
    prevent_initial_call=True,
)
def heatmap_click(click_data):
    """Clicking a heatmap cell selects that predictor x dimension pair."""
    if not click_data:
        raise PreventUpdate
    pt    = click_data['points'][0]
    lbl2x = {lbl: col for col, lbl, _ in dp.SCATTER_X_META}
    lbl2y = {lbl: col for col, lbl in dp.SCATTER_Y_META}
    x_col = lbl2x.get(pt.get('y', ''))
    y_col = lbl2y.get(pt.get('x', ''))
    if not x_col or not y_col:
        raise PreventUpdate
    return x_col, y_col


def _x_detail_panel(x_col: str) -> html.Div:
    """Source / scale / aggregation details for the chosen predictor."""
    detail = dp.SCATTER_X_DETAIL.get(x_col, {})

    def _row(key, label):
        if key not in detail:
            return []
        return [html.Div([
            html.Span(f'{label}: ', className='detail-key'),
            html.Span(detail[key], className='detail-val'),
        ], className='detail-row')]

    return html.Div([
        html.Div(detail.get('source', ''), className='detail-source'),
        *_row('variable', 'Variable'),
        *_row('scale', 'Scale'),
        *_row('aggregation', 'Aggregation'),
    ], className='detail-box')


@app.callback(
    Output('tc-scatter', 'figure'),
    Output('tc-x-desc', 'children'),
    Input('tc-x-var', 'value'),
    Input('tc-y-var', 'value'),
)
def update_corr(x_col, y_col):
    """Redraw the scatter (single or 2x2) for the chosen pair."""
    fig = (make_scatter_all(DF_SCATTER, x_col) if y_col == 'all'
           else make_scatter_single(DF_SCATTER, x_col, y_col))
    return fig, _x_detail_panel(x_col)


@app.callback(
    Output('tc-overlay', 'style'),
    Input('tc-expand-btn', 'n_clicks'),
    Input('tc-overlay-close', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_scatter_overlay(_open, _close):
    """Show / hide the fullscreen scatter overlay."""
    return ({'display': 'flex'} if ctx.triggered_id == 'tc-expand-btn'
            else {'display': 'none'})


@app.callback(
    Output('tc-scatter-full', 'figure'),
    Input('tc-expand-btn', 'n_clicks'),
    State('tc-x-var', 'value'),
    State('tc-y-var', 'value'),
    prevent_initial_call=True,
)
def update_scatter_full(_, x_col, y_col):
    """Large version of the current scatter for the overlay."""
    fig = (make_scatter_all(DF_SCATTER, x_col) if y_col == 'all'
           else make_scatter_single(DF_SCATTER, x_col, y_col))
    fig.update_layout(height=820)
    return fig


# ── Tab 2 - Value Space ────────────────────────────────────────────────────────

@app.callback(Output('t2vs-dim-desc', 'children'),
              Input('t2vs-dim-group', 'value'))
def update_dim_desc(dim_group):
    """Short description of the selected dimension group."""
    return dp.DIMENSION_GROUPS.get(dim_group, {}).get('desc', '')


def _validation_summary(validation: dict, n_clusters: int) -> html.Div:
    """Silhouette validation summary for the sidebar."""
    if not validation or not validation.get('scores'):
        return html.Div()
    scores = validation['scores']
    best_k = validation['best_k']
    chosen = validation.get('chosen_score')
    rows = [html.Div([
        html.Span(f'k = {k}', className='val-k'),
        html.Div(className='val-bar',
                 style={'width': f'{max(score, 0) * 100:.0f}%'}),
        html.Span(f'{score:.2f}', className='val-score'),
    ], className='val-row') for k, score in sorted(scores.items())]
    return html.Div([
        html.P('Cluster validation (silhouette)', className='ctrl-label'),
        *rows,
        html.P(f'Chosen k = {n_clusters}: {chosen:.2f} · suggested '
               f'k = {best_k} (highest silhouette).',
               className='side-note'),
    ])


@app.callback(
    Output('t2vs-graph', 'figure'),
    Output('t2vs-cluster-summary', 'children'),
    Output('t2vs-validation', 'children'),
    Input('t2vs-clusters', 'value'),
    Input('t2vs-dim-group', 'value'),
)
def update_value_space(n_clusters, dim_group):
    """Recompute PCA + clustering for the chosen group and k."""
    group  = dp.DIMENSION_GROUPS.get(dim_group, dp.DIMENSION_GROUPS['values'])
    src_df = {'df_main': DF_MAIN, 'df_scatter': DF_SCATTER,
              'df_gov_exp': DF_GOV_EXP}.get(group['source'], DF_MAIN)
    result, explained, pc1_label, pc2_label, validation = \
        dp.compute_pca_clustering(src_df, n_clusters, dim_group=dim_group)
    fig = make_value_space_figure(
        result, explained, pc1_label, pc2_label, n_clusters,
        data_cols=group['cols'],
        spoke_labels=group['spoke_labels'],
        dim_group_label=group['label'],
    )
    return (fig, make_cluster_summary(result, n_clusters),
            _validation_summary(validation, n_clusters))


# ── WSGI server ────────────────────────────────────────────────────────────────
server = app.server

if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('RENDER') is None
    app.run(host='0.0.0.0', port=port, debug=debug)
