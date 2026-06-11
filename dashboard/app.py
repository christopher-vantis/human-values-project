"""Dash application entry point.

Responsibilities:
  - Load the precomputed DataFrames from the pipeline
  - Create the Dash app (brand, meta tags) and register all callbacks
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
    EXPLORE_NAV, SCORE_COLORS, SCORE_LABELS,
    build_tab_corr, card, flag_img, landing, make_cluster_summary,
    register_expand_callbacks, tab1, tab2, tab_deep,
)

APP_NAME = 'European Values Atlas'
BASE_URL = 'https://little-project-on-human-values.onrender.com'
_DESCRIPTION = ('Schwartz basic human values across 30 European countries - '
                'ESS Round 11 (2023). Country profiles, regional deep dives '
                'for Germany and Switzerland, social gradients, and '
                'macro-level correlates.')

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

# Regional indicators actually available per deep-dive country (>= 3
# reliable regions with indicator data, otherwise the scatter is pointless)
def _available_indicators(cntry: str) -> list[str]:
    """Indicator keys with enough regional coverage for one country."""
    regions = set(DF_REGIONAL[(DF_REGIONAL['cntry'] == cntry)
                              & (~DF_REGIONAL['below_min_n'])]['region'])
    return [key for key in dp.REGIONAL_INDICATOR_META
            if (DF_REG_IND[(DF_REG_IND['indicator'] == key)
                           & (DF_REG_IND['region'].isin(regions))]
                .shape[0] >= 3)]


_IND_BY_COUNTRY = {cntry: _available_indicators(cntry)
                   for cntry in dp.ESS11_COUNTRIES}

# The heatmap is a pure function of precomputed data - build it once
_HEATMAP_FIG = make_corr_heatmap(DF_SCATTER)
tab_corr = build_tab_corr(_HEATMAP_FIG, MLM_RESULTS)

# ── App ────────────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    title=APP_NAME,
    suppress_callback_exceptions=True,
    external_stylesheets=dmc.styles.ALL,
    meta_tags=[
        {'name': 'viewport',
         'content': 'width=device-width, initial-scale=1'},
        {'name': 'description', 'content': _DESCRIPTION},
        {'property': 'og:title', 'content': APP_NAME},
        {'property': 'og:description', 'content': _DESCRIPTION},
        {'property': 'og:type', 'content': 'website'},
        {'property': 'og:url', 'content': BASE_URL},
        {'property': 'og:image', 'content': f'{BASE_URL}/assets/og.png'},
        {'name': 'twitter:card', 'content': 'summary_large_image'},
    ],
)

app.index_string = '''<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

_TABS = [
    ('About',             'tab-0'),
    ('Country Profile',   'tab-1'),
    ('Country Deep Dive', 'tab-deep'),
    ('Correlations',      'tab-corr'),
    ('Value Space',       'tab-2'),
]

header = html.Header([
    html.Img(src='/assets/logo.svg', className='brand-logo',
             alt='European Values Atlas logo'),
    html.Div([
        html.H1(APP_NAME, className='main-title'),
        html.P('Schwartz basic human values across Europe',
               className='main-subtitle'),
    ], className='brand-text'),
    html.Span('ESS Round 11 · 2023', className='header-chip'),
], className='header')

footer = html.Footer([
    html.Div([
        html.Div([
            html.Img(src='/assets/logo.svg', className='footer-logo',
                     alt=''),
            html.Span(APP_NAME, className='footer-brand'),
        ], className='footer-brand-row'),
        html.P('Exploring what people across Europe value - '
               'and why it differs.', className='footer-tagline'),
    ], className='footer-col'),
    html.Div([
        html.P('Data', className='footer-heading'),
        html.P(['European Social Survey, Round 11 (2023) · V-Dem v15 · '
                'World Bank WDI · Eurostat & GISCO. Raw ESS microdata is '
                'not redistributed; all figures show anonymised aggregates.'],
               className='footer-text'),
    ], className='footer-col'),
    html.Div([
        html.P('About', className='footer-heading'),
        html.P([
            'Built by Christopher Vantis · ',
            html.A('Source on GitHub',
                   href='https://github.com/christopher-vantis/'
                        'human-values-project',
                   target='_blank', rel='noopener',
                   className='footer-link'),
            ' · MIT licence',
        ], className='footer-text'),
    ], className='footer-col'),
], className='footer')

app.layout = dmc.MantineProvider(
    theme={'fontFamily': theme.FONT_FAMILY, 'primaryColor': 'blue'},
    children=html.Div([
        header,
        dcc.Tabs(
            id='main-tabs',
            value='tab-0',
            className='main-tabs',
            children=[dcc.Tab(label=label, value=value, className='tab',
                              selected_className='tab--selected')
                      for label, value in _TABS],
        ),
        html.Div(id='tab-content', className='outer-tab-content'),
        footer,
    ], className='app-wrapper'),
)

for _gid in ('t1-radar', 't2vs-graph'):
    register_expand_callbacks(app, _gid)


# ── Tab routing + in-page navigation ───────────────────────────────────────────

@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    """Swap the visible tab content."""
    return {'tab-0': landing, 'tab-1': tab1, 'tab-deep': tab_deep,
            'tab-corr': tab_corr, 'tab-2': tab2}[tab]


_NAV_TARGET = dict(EXPLORE_NAV)


@app.callback(
    Output('main-tabs', 'value'),
    [Input(btn_id, 'n_clicks') for btn_id, _ in EXPLORE_NAV],
    prevent_initial_call=True,
)
def navigate(*clicks):
    """Hero and explore-card buttons jump straight into a tab.

    The zero-click guard is required because the buttons mount dynamically
    with the landing tab, which re-fires this callback with no real click.
    """
    if not any(clicks):
        raise PreventUpdate
    target = _NAV_TARGET.get(ctx.triggered_id)
    if not target:
        raise PreventUpdate
    return target


# ── Tab 1 - Country Profile ────────────────────────────────────────────────────

def _facts_card(country: str) -> html.Div:
    """Country facts strip: flag, name, and key figures."""
    capital, pop_m, area_km2, system, eu = dp.COUNTRY_INFO[country]
    n_resp = int(DF_MAIN.loc[DF_MAIN['cntry'] == country, 'n'].iloc[0]) \
        if (DF_MAIN['cntry'] == country).any() else 0

    def _stat(label, value):
        return html.Div([
            html.Div(label, className='fact-label'),
            html.Div(value, className='fact-value'),
        ], className='fact-item')

    return card(html.Div([
        html.Div([flag_img(country, height=22),
                  html.Span(dp.COUNTRIES[country], className='facts-name')],
                 className='facts-title'),
        _stat('Capital', capital),
        _stat('Population', f'{pop_m:.1f} M'),
        _stat('Density', f'{round(pop_m * 1e6 / area_km2):,} / km²'),
        _stat('System', system),
        _stat('EU status', eu),
        _stat('ESS11 sample', f'{n_resp:,}'),
    ], className='facts-row'))


def _rank_row(label: str, rank: int, total: int, color: str) -> html.Div:
    """One dimension rank row with a position track."""
    pct = 100 * (total - rank) / (total - 1)
    return html.Div([
        html.Div([
            html.Span(className='legend-swatch', style={'background': color}),
            html.Span(label, className='insight-dim'),
            html.Span(f'#{rank} of {total}', className='insight-rank'),
        ], className='insight-head'),
        html.Div(html.Div(className='rank-marker',
                          style={'left': f'{pct:.0f}%',
                                 'background': color}),
                 className='rank-track'),
    ], className='insight-row')


def _insights_card(country: str) -> html.Div:
    """'What stands out': dimension ranks + most distinctive values."""
    row = DF_MAIN[DF_MAIN['cntry'] == country].iloc[0]
    total = len(DF_MAIN)

    rank_rows = []
    for dim_label, col in dp.DIM_COLS.items():
        rank = int((DF_MAIN[col] > row[col]).sum()) + 1
        rank_rows.append(_rank_row(dim_label, rank, total,
                                   theme.DIM_COLORS[dim_label]))

    # Values where the country deviates most from the European average
    # (unweighted mean of the 30 country scores)
    devs = []
    for k in dp.VALUE_KEYS:
        dev = float(row[f'd_{k}'] - DF_MAIN[f'd_{k}'].mean())
        devs.append((abs(dev), dev, k))
    top = sorted(devs, reverse=True)[:3]
    dev_rows = [html.Div([
        html.Span('▲' if dev > 0 else '▼',
                  className='dev-arrow',
                  style={'color': '#16a34a' if dev > 0 else '#dc2626'}),
        html.Span(dp.VALUE_LABELS[k], className='insight-dim'),
        html.Span(f'{abs(dev):.2f} {"above" if dev > 0 else "below"} '
                  'European average', className='dev-text'),
    ], className='dev-row') for _, dev, k in top]

    return card([
        html.P('What stands out', className='card-title'),
        html.P('Rank among the 30 ESS11 countries (right = higher priority).',
               className='side-note'),
        *rank_rows,
        html.Div(className='card-divider'),
        html.P('Most distinctive values', className='card-title'),
        *dev_rows,
    ], className='insights-card')


def _stat_card(col: str, ind_row, sentences: dict) -> html.Div:
    """One structural indicator as a compact stat card with a range bar."""
    meta = dp.INDICATOR_META[col]
    v, yr = (None, None) if ind_row is None else (
        ind_row.get(col), ind_row.get(col + '_year'))
    yr = int(yr) if yr and not pd.isna(yr) else None
    na = v is None or (isinstance(v, float) and math.isnan(v))
    val_str = 'n/a' if na else (
        f'{v:.3f}' if col == 'vdem_ldi' else
        f'{v:.0f}' if col == 'estat_gdp_pps' else f'{v:.1f}')

    series = DF_IND[col].dropna() if col in DF_IND.columns else pd.Series([])
    bar = []
    if not na and len(series) > 2 and series.max() > series.min():
        pct = 100 * (v - series.min()) / (series.max() - series.min())
        bar = [html.Div(html.Div(className='range-marker',
                                 style={'left': f'{pct:.0f}%'}),
                        className='range-track'),
               html.Div([html.Span(f'{series.min():.0f}'),
                         html.Span('all ESS11 countries'),
                         html.Span(f'{series.max():.0f}')],
                        className='range-ends')]

    return html.Div([
        html.Div(meta['label'], className='stat-label'),
        html.Div([
            html.Span(val_str,
                      className='stat-value' + (' stat-value--na' if na else '')),
            html.Span(meta['unit'], className='stat-unit'),
            html.Span(str(yr) if yr and not na else '',
                      className='stat-year'),
        ], className='stat-value-row'),
        *bar,
        html.Div(sentences.get(col, ''), className='stat-sentence'),
        html.Div([
            html.P(meta.get('desc', ''), className='indicator-tooltip-desc'),
            html.P(meta['source'], className='indicator-tooltip-source'),
        ], className='indicator-tooltip'),
    ], className='stat-card indicator-row')


@app.callback(
    Output('t1-radar', 'figure'),
    Output('t1-facts', 'children'),
    Output('t1-insights', 'children'),
    Output('t1-indicators', 'children'),
    Input('t1-country', 'value'),
)
def update_t1(country):
    """Redraw radar, facts, insights, and indicator cards for one country."""
    ind_row = DF_IND.loc[country] if country in DF_IND.index else None
    sents   = INDICATOR_SENTENCES.get(country, {})
    indicators = card([
        html.P('Structural indicators', className='card-title'),
        html.P('Hover a card for the indicator definition and source. The '
               'track shows where the country sits among all ESS11 countries.',
               className='side-note'),
        html.Div([_stat_card(col, ind_row, sents)
                  for col in dp.INDICATOR_META], className='stat-grid'),
    ])
    return (make_radar_single(DF_MAIN, country), _facts_card(country),
            _insights_card(country), indicators)


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
    if sub.empty:
        note = ('No NUTS regional map for this country - the social '
                'gradients below still apply.')
    else:
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
        # Countries without regional data (IL, UA): explicit empty state
        # instead of a stale figure from the previous country
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text='No regional indicators available for this country.',
            x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False,
            font=dict(size=13, color=theme.MUTED))
        fig.update_layout(height=440)
        return fig, ''
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
