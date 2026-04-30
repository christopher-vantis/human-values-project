"""Dash application entry point.

Responsibilities:
  - Load DataFrames from the pipeline
  - Create the Dash app and register all callbacks
  - Expose the WSGI server for Gunicorn

Layout objects and pure UI helpers live in layouts.py.
Data loading and pipeline constants live in data_pipeline.py.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dash import Dash, dcc, html, Input, Output, State, ctx
from dash.exceptions import PreventUpdate
import pandas as pd

import data_pipeline as dp
from figures.radar       import make_radar_single
from figures.parallel    import make_parallel_micro
from figures.value_space import make_value_space_figure
from figures.scatter     import make_scatter_single, make_scatter_all, make_corr_heatmap

from layouts import (
    landing, tab1, tab_corr, tab2, tab3,
    make_cluster_summary, register_expand_callbacks,
    INFO_PANEL_STYLE, DEFAULT_YEAR, DEFAULT_COUNTRY,
)

# ── Data ──────────────────────────────────────────────────────────────────────
DF          = dp.load_data()
DF_MICRO    = dp.load_micro_individual(sample_per_dim=300)
DF_SCATTER  = dp.load_scatter_data()
DF_GOV_EXP  = dp.load_gov_exp()
DF_IND, INDICATOR_SENTENCES = dp.load_indicators()


# ── Data-dependent helpers ────────────────────────────────────────────────────

def _year_slider_marks(country: str) -> dict:
    avail = set(DF[DF['cntry'] == country]['year'].unique())
    marks = {}
    for y in dp.ALL_YEARS:
        if y in avail:
            marks[y] = {'label': str(y),
                        'style': {'color': '#1a2840', 'font-size': '11px'}}
        else:
            marks[y] = {'label': str(y),
                        'style': {'color': '#bbbbbb', 'font-size': '11px',
                                  'text-decoration': 'line-through'}}
    return marks


def _nearest_available(country: str, year: int) -> int:
    avail = sorted(DF[DF['cntry'] == country]['year'].unique())
    return min(avail, key=lambda y: abs(y - year))


# ── App ────────────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    title='Little Project on Human Values',
    suppress_callback_exceptions=True,
)

app.layout = html.Div([
    html.Div([
        html.H1('Little Project on Human Values', className='main-title'),
        html.P(
            'Exploring what people across Europe value - and why it differs. '
            'Schwartz basic human values measured across 39 European countries, '
            'ESS Rounds 1-11 (2002-2023), linked to macro indicators and social attitudes.',
            className='main-subtitle',
        ),
        html.P('by Christopher Vantis',
               style={'font-style': 'italic', 'font-size': '12px',
                      'color': '#7a90b0', 'margin': '4px 0 0'}),
    ], className='header'),

    dcc.Tabs(
        id='main-tabs',
        value='tab-0',
        className='main-tabs',
        children=[
            dcc.Tab(label='About',                value='tab-0',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Country Profile',      value='tab-1',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Correlations',         value='tab-corr',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Value Space',          value='tab-2',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Parallel Coordinates', value='tab-3',
                    className='tab', selected_className='tab--selected'),
        ],
    ),
    html.Div(id='tab-content', className='outer-tab-content'),
], className='app-wrapper')

# Register clientside fullscreen callbacks for expandable graphs
for _gid in ('t1-radar', 't2vs-graph', 't3-parallel'):
    register_expand_callbacks(app, _gid)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    return {'tab-0': landing, 'tab-1': tab1, 'tab-corr': tab_corr,
            'tab-2': tab2,    'tab-3': tab3}[tab]


# Tab 1 — Country Profile

@app.callback(
    Output('t1-year', 'marks'),
    Output('t1-year', 'value'),
    Input('t1-country', 'value'),
    State('t1-year', 'value'),
)
def update_t1_slider(country, current_year):
    return _year_slider_marks(country), _nearest_available(country, current_year)


@app.callback(
    Output('t1-radar', 'figure'),
    Input('t1-country', 'value'),
    Input('t1-year', 'value'),
)
def update_t1(country, year):
    return make_radar_single(DF, country, year)


@app.callback(
    Output('t1-country-info', 'children'),
    Input('t1-country', 'value'),
)
def update_t1_info(country):
    info = dp.COUNTRY_INFO.get(country)
    if not info:
        return []
    capital, pop_m, area_km2, system, eu = info
    density      = round(pop_m * 1_000_000 / area_km2)
    rounds_avail = sorted(DF[DF['cntry'] == country]['year'].unique())
    rounds_str   = (f'{dp.YEAR_TO_ROUND[rounds_avail[0]]}-{dp.YEAR_TO_ROUND[rounds_avail[-1]]}'
                    if len(rounds_avail) > 1
                    else str(dp.YEAR_TO_ROUND[rounds_avail[0]]))

    def _stat(label, value):
        return html.Div([
            html.Div(label, style={
                'font-size': '10px', 'font-weight': '600', 'color': '#7a90b0',
                'text-transform': 'uppercase', 'letter-spacing': '0.5px',
                'margin-bottom': '4px',
            }),
            html.Div(value, style={
                'font-size': '13px', 'font-weight': '600', 'color': '#1a2840',
                'line-height': '1.3',
            }),
        ], style={'flex': '1', 'min-width': '80px', 'padding': '0 16px 0 0'})

    _card_style = {
        'margin-top': '14px', 'padding': '14px 18px',
        'background-color': '#f7f9fc', 'border-radius': '8px',
        'border-top': '3px solid #c0cce0',
    }

    facts_card = html.Div([
        html.Div([
            _stat('Capital',     capital),
            _stat('Population',  f'{pop_m:.1f} M'),
            _stat('Density',     f'{density:,} / km²'),
            _stat('System',      system),
            _stat('EU status',   eu),
            _stat('ESS rounds',  f'R{rounds_str}  ({len(rounds_avail)} of 11)'),
        ], style={'display': 'flex', 'flex-wrap': 'wrap', 'gap': '12px 0'}),
    ], style=_card_style)

    ind_row = DF_IND.loc[country] if country in DF_IND.index else None
    sents   = INDICATOR_SENTENCES.get(country, {})

    def _ind_item(col: str) -> html.Div:
        meta     = dp.INDICATOR_META[col]
        sentence = sents.get(col, '')
        v, yr    = (None, None) if ind_row is None else (
            ind_row.get(col), ind_row.get(col + '_year'))
        yr = int(yr) if yr and not pd.isna(yr) else None
        import math
        na = v is None or (isinstance(v, float) and math.isnan(v))
        val_str = 'n/a' if na else (
            f'{v:.3f}' if col == 'vdem_ldi' else
            f'{v:.0f}' if col == 'estat_gdp_pps' else
            f'{v:.1f}')
        yr_str = f' ({yr})' if yr and not na else ''
        return html.Div([
            html.Div([
                html.Span(meta['label'], style={
                    'font-size': '11px', 'font-weight': '600',
                    'color': '#3a4a60', 'flex': '1'}),
                html.Span(
                    f'{val_str} {meta["unit"]}{yr_str}',
                    style={'font-size': '11px', 'font-weight': '700',
                           'color': '#0d1b2a' if not na else '#9aa8b8',
                           'text-align': 'right', 'white-space': 'nowrap',
                           'cursor': 'default'}),
            ], style={'display': 'flex', 'align-items': 'baseline',
                      'gap': '8px', 'margin-bottom': '2px'}),
            html.Div(sentence, style={
                'font-size': '10.5px', 'color': '#7a90b0',
                'line-height': '1.4', 'font-style': 'italic',
                'margin-bottom': '8px'}),
            html.Div([
                html.P(meta.get('desc', ''), className='indicator-tooltip-desc'),
                html.P(meta['source'],        className='indicator-tooltip-source'),
            ], className='indicator-tooltip'),
        ], className='indicator-row')

    ind_block = html.Div([
        html.P('Structural Indicators', style={
            'font-size': '10px', 'font-weight': '700', 'color': '#1a2840',
            'text-transform': 'uppercase', 'letter-spacing': '0.5px',
            'margin': '0 0 10px'}),
        *[_ind_item(col) for col in dp.INDICATOR_META],
        html.P('Hover over a row to see indicator description and source.',
               style={'font-size': '9.5px', 'color': '#b0bcc8',
                      'margin': '4px 0 0', 'font-style': 'italic'}),
    ], style=_card_style)

    return html.Div([facts_card, ind_block])


# Tab Corr — fullscreen overlay toggle (hand-written; tc-scatter has no _expandable_graph wrapper)

@app.callback(
    Output('tc-overlay', 'style'),
    Input('tc-expand-btn',    'n_clicks'),
    Input('tc-overlay-close', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_scatter_overlay(_open, _close):
    return {'display': 'flex'} if ctx.triggered_id == 'tc-expand-btn' else {'display': 'none'}


@app.callback(
    Output('tc-scatter-full', 'figure'),
    Input('tc-expand-btn', 'n_clicks'),
    State('tc-round', 'value'),
    State('tc-x-var',  'value'),
    State('tc-y-var',  'value'),
    prevent_initial_call=True,
)
def update_scatter_full(_, year, x_col, y_col):
    fig = (make_scatter_all(DF_SCATTER, x_col, year=year) if y_col == 'all'
           else make_scatter_single(DF_SCATTER, x_col, y_col, year=year))
    fig.update_layout(height=820)
    return fig


@app.callback(Output('tc-heatmap', 'figure'), Input('tc-round', 'value'))
def update_heatmap(year):
    return make_corr_heatmap(DF_SCATTER, year)


@app.callback(
    Output('tc-x-var', 'value'),
    Output('tc-y-var', 'value'),
    Input('tc-heatmap', 'clickData'),
    prevent_initial_call=True,
)
def heatmap_click(click_data):
    if not click_data:
        raise PreventUpdate
    pt      = click_data['points'][0]
    lbl2x   = {lbl: col for col, lbl, _ in dp.SCATTER_X_META}
    lbl2y   = {lbl: col for col, lbl, _ in dp.SCATTER_Y_META}
    x_col   = lbl2x.get(pt.get('y', ''))
    y_col   = lbl2y.get(pt.get('x', ''))
    if not x_col or not y_col:
        raise PreventUpdate
    return x_col, y_col


@app.callback(
    Output('tc-scatter', 'figure'),
    Output('tc-x-desc',  'children'),
    Input('tc-round', 'value'),
    Input('tc-x-var',   'value'),
    Input('tc-y-var',   'value'),
)
def update_corr(year, x_col, y_col):
    detail = dp.SCATTER_X_DETAIL.get(x_col, {})

    def _detail_row(key, label):
        if key not in detail:
            return []
        return [html.Div([
            html.Span(f'{label}: ', style={'font-weight': '600',
                                           'color': '#1a2840', 'font-size': '10.5px'}),
            html.Span(detail[key], style={'color': '#3a4a60', 'font-size': '10.5px'}),
        ], style={'margin-bottom': '3px', 'line-height': '1.45'})]

    desc_html = html.Div([
        html.Div(detail.get('source', ''), style={
            'font-size': '10.5px', 'font-weight': '700',
            'color': '#1a5fb4', 'margin-bottom': '5px'}),
        *_detail_row('variable',    'Variable'),
        *_detail_row('scale',       'Scale'),
        *_detail_row('aggregation', 'Aggregation'),
    ], style={'padding': '8px 10px', 'background-color': '#f7f9fc',
              'border-radius': '6px', 'border-left': '3px solid #c0cce0'})

    fig = (make_scatter_all(DF_SCATTER, x_col, year=year) if y_col == 'all'
           else make_scatter_single(DF_SCATTER, x_col, y_col, year=year))
    return fig, desc_html


# Tab 2 — Value Space

@app.callback(
    Output('t2vs-dim-desc', 'children'),
    Input('t2vs-dim-group', 'value'),
)
def update_dim_desc(dim_group):
    return dp.DIMENSION_GROUPS.get(dim_group, {}).get('desc', '')


@app.callback(
    Output('t2vs-graph', 'figure'),
    Output('t2vs-cluster-summary', 'children'),
    Input('t2vs-year', 'value'),
    Input('t2vs-clusters', 'value'),
    Input('t2vs-dim-group', 'value'),
)
def update_value_space(year, n_clusters, dim_group):
    group  = dp.DIMENSION_GROUPS.get(dim_group, dp.DIMENSION_GROUPS['values'])
    src_df = {'df_main': DF, 'df_scatter': DF_SCATTER,
              'df_gov_exp': DF_GOV_EXP}.get(group['source'], DF)
    result, explained, pc1_label, pc2_label = dp.compute_pca_clustering(
        src_df, year, n_clusters, dim_group=dim_group)
    fig = make_value_space_figure(
        result, explained, pc1_label, pc2_label,
        year, n_clusters,
        data_cols=group['cols'],
        spoke_labels=group['spoke_labels'],
        dim_group_label=group['label'],
    )
    return fig, make_cluster_summary(result, n_clusters)


# Tab 3 — Parallel Coordinates

@app.callback(
    Output('t3-parallel', 'figure'),
    Output('t3-title', 'children'),
    Input('t3-dim', 'value'),
)
def update_t3(highlight_dim):
    label = highlight_dim if highlight_dim != 'all' else 'All Dimensions'
    return (make_parallel_micro(DF_MICRO, highlight_dim),
            f'Parallel Coordinates  ·  Highlight: {label}  ·  All ESS Rounds')


# Info panel toggles

def _toggle(n):
    open_ = bool(n and n % 2 == 1)
    return (INFO_PANEL_STYLE if open_ else {'display': 'none'},
            '▲ Info' if open_ else 'Info')


@app.callback(
    Output('t1-method-content', 'style'),
    Output('t1-method-btn', 'children'),
    Input('t1-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t1_method(n): return _toggle(n)


@app.callback(
    Output('tc-method-content', 'style'),
    Output('tc-method-btn', 'children'),
    Input('tc-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_tc_method(n): return _toggle(n)


@app.callback(
    Output('t2-method-content', 'style'),
    Output('t2-method-btn', 'children'),
    Input('t2-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t2_method(n): return _toggle(n)


@app.callback(
    Output('t3-method-content', 'style'),
    Output('t3-method-btn', 'children'),
    Input('t3-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t3_method(n): return _toggle(n)


# ── WSGI server ────────────────────────────────────────────────────────────────
server = app.server

if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('RENDER') is None
    app.run(host='0.0.0.0', port=port, debug=debug)
