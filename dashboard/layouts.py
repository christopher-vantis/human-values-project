"""Static layout objects and pure UI helpers for the dashboard.

Nothing in this module accesses loaded DataFrames. It uses only constants
from data_pipeline / theme that are available at import time. Layout pieces
that depend on precomputed results (correlation heatmap, multilevel-model
table) are built by factory functions called from app.py at startup.
"""
from __future__ import annotations

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html

import data_pipeline as dp
import theme

DEFAULT_COUNTRY      = 'DE'
DEFAULT_DEEP_COUNTRY = 'DE'
DEFAULT_SCORE        = 'dim_openness'

# ── Score (dimension / value) metadata shared by several tabs ──────────────────
SCORE_LABELS = {col: lbl for col, lbl in dp.SCATTER_Y_META}
SCORE_LABELS.update({f'd_{k}': dp.VALUE_LABELS[k] for k in dp.VALUE_KEYS})

SCORE_COLORS = {col: theme.DIM_COLORS[lbl] for col, lbl in dp.SCATTER_Y_META}
SCORE_COLORS.update({f'd_{k}': theme.DIM_COLORS[dp.VALUE_TO_DIM[k]]
                     for k in dp.VALUE_KEYS})

SCORE_OPTS = [
    {'group': 'Higher-order dimensions',
     'items': [{'value': col, 'label': lbl} for col, lbl in dp.SCATTER_Y_META]},
    {'group': 'Basic values',
     'items': [{'value': f'd_{k}', 'label': dp.VALUE_LABELS[k]}
               for k in dp.VALUE_KEYS]},
]

# ── Dropdown option lists ──────────────────────────────────────────────────────

COUNTRY_OPTS = [{'value': c, 'label': f'{dp.COUNTRY_FLAGS[c]} {dp.COUNTRIES[c]}'}
                for c in sorted(dp.ESS11_COUNTRIES,
                                key=lambda c: dp.COUNTRIES[c])]

_X_GROUPS = [
    ('ESS social variables (Round 11, weighted)', 8),
    ('External macro indicators (2023)', 4),
    ('Government expenditure (COFOG, latest)', 7),
]
SCATTER_X_OPTS = []
_i = 0
for _label, _count in _X_GROUPS:
    SCATTER_X_OPTS.append({
        'group': _label,
        'items': [{'value': col, 'label': lbl}
                  for col, lbl, _ in dp.SCATTER_X_META[_i:_i + _count]],
    })
    _i += _count

SCATTER_Y_OPTS = ([{'value': 'all', 'label': 'All 4 dimensions (2×2)'}]
                  + [{'value': col, 'label': lbl}
                     for col, lbl in dp.SCATTER_Y_META])

DIM_GROUP_OPTS = [{'value': key, 'label': grp['label']}
                  for key, grp in dp.DIMENSION_GROUPS.items()]

DEEP_COUNTRY_OPTS = [
    {'value': c, 'label': f'{dp.COUNTRY_FLAGS[c]} {meta["label"]}'}
    for c, meta in dp.DEEP_DIVE_COUNTRIES.items()
]


# ── Small pure helpers ─────────────────────────────────────────────────────────

def card(children, **kwargs) -> html.Div:
    """White content card with border + soft shadow."""
    cls = 'card ' + kwargs.pop('className', '')
    return html.Div(children, className=cls.strip(), **kwargs)


def ctrl_group(label: str, *children) -> html.Div:
    """Sidebar control group: small caps label above the control(s)."""
    return html.Div([html.Label(label, className='ctrl-label'), *children],
                    className='ctrl-group')


def select(id_: str, data, value, **kwargs) -> dmc.Select:
    """Project-styled dmc.Select with sensible defaults."""
    return dmc.Select(id=id_, data=data, value=value, clearable=False,
                      searchable=kwargs.pop('searchable', False),
                      allowDeselect=False, size='sm', radius='md', **kwargs)


def _subtitle(text: str) -> html.P:
    return html.P(text, className='tab-subtitle')


def info_accordion(title: str, rows: list[tuple[str, str]]) -> dmc.Accordion:
    """Collapsible methods/info panel (no callback needed)."""
    body = []
    for heading, text in rows:
        body.append(html.P(heading, className='info-heading'))
        body.append(html.P(text, className='info-body'))
    return dmc.Accordion(
        chevronPosition='right',
        variant='contained',
        radius='md',
        className='info-accordion',
        children=[dmc.AccordionItem([
            dmc.AccordionControl(title,
                                 style={'fontSize': '12.5px',
                                        'fontWeight': 600}),
            dmc.AccordionPanel(body),
        ], value='info')],
    )


def _dim_legend() -> html.Div:
    """Colour legend for the four higher-order dimensions."""
    rows = [html.Div([
        html.Span(className='legend-swatch',
                  style={'background': color}),
        html.Span(dim, className='legend-text'),
    ], className='legend-row') for dim, color in theme.DIM_COLORS.items()]
    return html.Div(rows, className='legend-box')


def _expandable_graph(graph_id: str, config: dict | None = None,
                      extra_children: list | None = None) -> html.Div:
    """Wrap a dcc.Graph with a fullscreen button and overlay."""
    cfg = {**(config or {}), 'displayModeBar': False}
    overlay_cfg = {
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['sendDataToCloud', 'editInChartStudio',
                                   'lasso2d', 'select2d'],
    }
    main_block = html.Div([
        html.Button('', id=f'{graph_id}-expand-btn', n_clicks=0,
                    className='chart-expand-btn', title='Fullscreen'),
        dcc.Loading(dcc.Graph(id=graph_id, config=cfg),
                    type='circle', color=theme.PRIMARY, delay_show=350),
        *(extra_children or []),
    ], style={'position': 'relative'})
    overlay = html.Div(
        id=f'{graph_id}-overlay',
        className='chart-overlay',
        style={'display': 'none'},
        children=[html.Div([
            html.Button('✕', id=f'{graph_id}-close-btn', n_clicks=0,
                        className='chart-overlay-close'),
            dcc.Graph(id=f'{graph_id}-overlay-graph', config=overlay_cfg),
        ], className='chart-overlay-inner')],
    )
    return html.Div([main_block, overlay])


def register_expand_callbacks(app_ref, graph_id: str) -> None:
    """Register clientside fullscreen show/hide + figure-copy callbacks."""
    app_ref.clientside_callback(
        """
        function(_a, _b) {
            const ctx = window.dash_clientside.callback_context;
            if (!ctx || !ctx.triggered || !ctx.triggered.length)
                return window.dash_clientside.no_update;
            return ctx.triggered[0].prop_id.split('.')[0].endsWith('-expand-btn')
                ? {display: 'flex'}
                : {display: 'none'};
        }
        """,
        Output(f'{graph_id}-overlay', 'style'),
        Input(f'{graph_id}-expand-btn', 'n_clicks'),
        Input(f'{graph_id}-close-btn',  'n_clicks'),
        prevent_initial_call=True,
    )
    app_ref.clientside_callback(
        """
        function(n, fig) {
            if (!fig || !n) return window.dash_clientside.no_update;
            var f = JSON.parse(JSON.stringify(fig));
            f.layout = f.layout || {};
            f.layout.height = Math.max(500, Math.floor(window.innerHeight * 0.78));
            f.layout.autosize = true;
            return f;
        }
        """,
        Output(f'{graph_id}-overlay-graph', 'figure'),
        Input(f'{graph_id}-expand-btn', 'n_clicks'),
        State(graph_id, 'figure'),
        prevent_initial_call=True,
    )


def make_cluster_summary(result, n_clusters: int) -> list:
    """Sidebar cluster summary: countries + dominant dimension per cluster."""
    if result is None or result.empty:
        return []
    _dim_dcols = {
        'Openness to Change': ['d_SD', 'd_HE', 'd_ST'],
        'Self-Transcendence': ['d_UN', 'd_BE'],
        'Conservation':       ['d_TR', 'd_CO', 'd_SE'],
        'Self-Enhancement':   ['d_PO', 'd_AC'],
    }
    items = []
    for cid in range(n_clusters):
        grp = result[result['cluster'] == cid]
        if grp.empty:
            continue
        color = theme.CLUSTER_COLORS[cid % len(theme.CLUSTER_COLORS)]
        dim_scores = {
            dim: grp[[c for c in dcols if c in grp.columns]].mean(axis=1).mean()
            for dim, dcols in _dim_dcols.items()
        }
        dominant = max(dim_scores, key=dim_scores.get)
        items.append(html.Div([
            html.Span('● ', style={'color': color, 'fontWeight': 700}),
            html.Span(f'Cluster {cid + 1}: ', className='cluster-title'),
            html.Span(', '.join(sorted(grp['country_name'].tolist())),
                      className='cluster-countries'),
            html.Br(),
            html.Span(f'({dominant})', className='cluster-dominant'),
        ], className='cluster-item'))
    return items


# ── Hero + landing page ────────────────────────────────────────────────────────

def _hero_stat(value: str, label: str) -> html.Div:
    return html.Div([
        html.Div(value, className='hero-stat-value'),
        html.Div(label, className='hero-stat-label'),
    ], className='hero-stat')


hero = html.Div([
    html.Div([
        html.H2('What do Europeans value - and why does it differ?',
                className='hero-title'),
        html.P(
            'Schwartz basic human values across 30 European countries, '
            'measured in the European Social Survey Round 11 (2023), mapped '
            'from the national level down to regions and social groups, and '
            'linked to macro-level indicators.',
            className='hero-subtitle'),
        html.Div([
            dmc.Button('Explore country profiles', id='hero-btn-profile',
                       n_clicks=0, size='sm', radius='md'),
            dmc.Button('Regional deep dive', id='hero-btn-deep',
                       n_clicks=0, size='sm', radius='md', variant='outline'),
        ], className='hero-buttons'),
    ], className='hero-text'),
    html.Div([
        _hero_stat('30',     'countries'),
        _hero_stat('49,259', 'respondents'),
        _hero_stat('21',     'PVQ portrait items'),
        _hero_stat('10',     'basic values'),
    ], className='hero-stats'),
], className='hero')


landing = html.Div([
    hero,

    html.Div([
        html.H2('Schwartz Theory of Basic Human Values', className='lp-h2'),
        html.P([
            'In 1992, social psychologist Shalom Schwartz proposed that ',
            html.B('10 basic human values'), ' are universal across cultures - '
            'motivational goals that guide attitudes and behaviour in every '
            'society. He arranged them in a circular structure (the ',
            html.Em('circumplex'), ') where neighbouring values reinforce each '
            'other and opposing values compete.',
        ], className='lp-p'),

        html.Div([
            html.Img(src='/assets/schwartz_values.jpg',
                     className='lp-schwartz-img'),
            html.P([
                'Source: Schwartz, S. H. (1992). Universals in the content and '
                'structure of values. ',
                html.Em('Advances in Experimental Social Psychology, 25'),
                ', 1-65.',
            ], className='lp-img-caption'),
        ], className='lp-img-block'),

        html.P(['The 10 values cluster into ',
                html.B('4 higher-order dimensions:')], className='lp-p'),
        html.Div([
            html.Div([
                html.Span('■ ', style={'color': theme.DIM_COLORS[d]}),
                html.B(f'{d} '),
                html.Span(desc, className='lp-dim-desc'),
            ], className='lp-dim-row')
            for d, desc in [
                ('Openness to Change',
                 '- Self-Direction, Stimulation, Hedonism. Autonomy, novelty, pleasure.'),
                ('Self-Transcendence',
                 '- Universalism, Benevolence. Welfare of others and of nature.'),
                ('Conservation',
                 '- Security, Conformity, Tradition. Order, self-restriction, stability.'),
                ('Self-Enhancement',
                 '- Power, Achievement. Personal success and social dominance.'),
            ]
        ], className='lp-dim-block'),
    ], className='lp-section'),

    html.Div([
        html.H2('Data & Methods', className='lp-h2'),
        html.P([
            'All value scores come from the ', html.B('European Social Survey, '
            'Round 11 (2023)'), ' - the newest available round, covering 30 '
            'countries and 50,116 respondents. Values are measured with the ',
            html.B('Portrait Values Questionnaire (PVQ-21)'), ': 21 short '
            'portraits rated on how similar each described person is to the '
            'respondent.',
        ], className='lp-p'),
        html.Ul([
            html.Li([html.B('Reverse-coding: '),
                     'the raw 1-6 scale runs from "very much like me" to '
                     '"not like me at all"; items are recoded (7 - x) so that '
                     'higher always means stronger endorsement.'],
                    className='lp-li'),
            html.Li([html.B('Person-centring (ipsatisation): '),
                     'each respondent\'s value scores are centred at their own '
                     'mean across all valid items, following Schwartz\'s '
                     'recommended procedure. Only relative priorities matter, '
                     'not absolute scale use. Respondents with fewer than 16 '
                     'valid items are excluded (49,259 retained).'],
                    className='lp-li'),
            html.Li([html.B('Survey weights: '),
                     'all country, regional, and group aggregates use the ESS '
                     'analysis weight (anweight), which corrects for sampling '
                     'design and post-stratifies to population margins.'],
                    className='lp-li'),
            html.Li([html.B('Multiple-comparison control: '),
                     'the correlation matrix tests 76 predictor x dimension '
                     'pairs simultaneously; significance stars are based on '
                     'Benjamini-Hochberg FDR-adjusted q-values, not raw '
                     'p-values.'],
                    className='lp-li'),
            html.Li([html.B('Regional estimates: '),
                     'Germany at NUTS-1 (Bundesländer) and Switzerland at '
                     'NUTS-2 (Grossregionen) level; regions with fewer than '
                     '50 respondents are greyed out rather than displayed as '
                     'reliable estimates.'],
                    className='lp-li'),
        ], className='lp-ul'),
        html.P([html.B('External sources: '),
                'V-Dem v15 (Liberal Democracy Index), World Bank WDI (GDP, '
                'Gini, unemployment), Eurostat (COFOG government expenditure, '
                'regional statistics, GISCO NUTS boundaries), plus the 12 '
                'structural indicators documented in the Country Profile tab.'],
               className='lp-p'),
    ], className='lp-section'),

    html.Div([
        html.H2('Limitations', className='lp-h2'),
        html.Div([
            html.B('1. Pan-cultural regularities'),
            html.P([
                'Schwartz and Bardi (2001) showed that value hierarchies share '
                'a remarkably stable cross-cultural structure: Benevolence and '
                'Universalism rank near the top in virtually all societies; '
                'Power near the bottom. The dashboard\'s Δ-scores reproduce '
                'this pattern - what is informative are the ',
                html.B('deviations of individual countries, regions, and '
                       'groups from that universal baseline.'),
            ], className='lp-p'),
        ], className='lp-limitation'),
        html.Div([
            html.B('2. Measurement invariance'),
            html.P([
                'Davidov, Schmidt, and Schwartz (2008) demonstrated that '
                'PVQ-21 items in cross-national comparison often achieve only '
                'configural invariance, rarely metric, and almost never scalar '
                'invariance. Person-centring mitigates but does not eliminate '
                'this. Cross-country statements should be read as ',
                html.Em('indicators of structural differences'),
                ', not precise quantifications.',
            ], className='lp-p'),
        ], className='lp-limitation'),
        html.Div([
            html.B('3. Aggregates are not essences'),
            html.P([
                'Magun, Rudnev, and Schmidt (2016) showed that value diversity ',
                html.Em('within'), ' European countries is often greater than '
                'the diversity ', html.Em('between'), ' them. The multilevel '
                'models in the Correlations tab quantify this directly: only '
                '7-18 % of individual variance sits between countries. A '
                'national or regional value profile is an average, not a '
                'cultural essence.',
            ], className='lp-p'),
        ], className='lp-limitation'),
        html.Div([
            html.B('4. Cross-sectional snapshot'),
            html.P([
                'Everything shown refers to the 2023 cross-section. '
                'Correlations are descriptive associations between countries '
                '(or regions) - they are not causal estimates and say nothing '
                'about change over time.',
            ], className='lp-p'),
        ], className='lp-limitation'),
    ], className='lp-section'),
], className='landing-page')


# ── Tab 1 - Country Profile ────────────────────────────────────────────────────

tab1 = html.Div([
    html.Div([
        html.Div([
            _subtitle(
                'Single-country value profile, ESS Round 11 (2023). Δ-scores '
                'show each value\'s deviation from the respondent\'s own '
                'average - positive means above-average priority.'),
            ctrl_group('Country',
                       select('t1-country', COUNTRY_OPTS, DEFAULT_COUNTRY,
                              searchable=True)),
            ctrl_group('Higher-order dimensions', _dim_legend()),
            info_accordion('Methods', [
                ('Δ-scores',
                 'PVQ items are reverse-coded (7 - x) and centred at each '
                 'respondent\'s personal mean across all 21 items, then '
                 'aggregated to weighted country means (ESS anweight). '
                 'Positive = above-average relative priority.'),
                ('PVQ-21 measurement',
                 'Values are elicited via 21 short portrait descriptions '
                 'rated on a 1-6 similarity scale. Respondents with fewer '
                 'than 16 valid items are excluded.'),
                ('Higher-order dimensions',
                 'Coloured arcs on the outer ring mark the four groupings: '
                 'Openness to Change (Self-Direction, Stimulation, Hedonism), '
                 'Self-Transcendence (Universalism, Benevolence), Conservation '
                 '(Security, Conformity, Tradition), Self-Enhancement '
                 '(Power, Achievement).'),
            ]),
        ], className='sidebar'),
        html.Div([
            card(_expandable_graph('t1-radar')),
            html.Div(id='t1-country-info'),
        ], className='main-content'),
    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab Deep Dive - regional analysis for DE / CH ──────────────────────────────

tab_deep = html.Div([
    html.Div([
        html.Div([
            _subtitle(
                'How are value priorities distributed within a country? '
                'Regional estimates (weighted), regional structure '
                'correlates, and social gradients - ESS Round 11 (2023).'),
            ctrl_group('Country',
                       dmc.SegmentedControl(
                           id='td-country', data=DEEP_COUNTRY_OPTS,
                           value=DEFAULT_DEEP_COUNTRY, fullWidth=True,
                           size='sm', radius='md')),
            ctrl_group('Value score',
                       select('td-score', SCORE_OPTS, DEFAULT_SCORE)),
            html.Div(id='td-region-note', className='side-note'),
            info_accordion('Methods', [
                ('Regional estimates',
                 'Weighted means of person-centred scores per NUTS region '
                 '(Germany: NUTS-1 Bundesländer; Switzerland: NUTS-2 '
                 'Grossregionen). Regions with n < 50 respondents are greyed '
                 'out; Bremen has no ESS11 respondents at all.'),
                ('Regional correlates',
                 'Eurostat regional indicators (latest available year) '
                 'against regional value scores. Because national '
                 'institutions and culture are held constant, these '
                 'within-country associations are often more informative than '
                 'cross-country correlations - but with 7-15 regions they '
                 'remain exploratory.'),
                ('Social gradients',
                 'Weighted group means of the same person-centred scores. '
                 'Groups with fewer than 30 respondents are dropped. '
                 'Education = years of full-time education; urbanisation from '
                 'the ESS domicil item.'),
            ]),
        ], className='sidebar'),
        html.Div([
            html.Div([
                card([
                    dcc.Loading(dcc.Graph(id='td-choropleth',
                                          config={'displayModeBar': False}),
                                type='circle', color=theme.PRIMARY,
                                delay_show=350),
                ]),
                card([
                    html.Div([
                        html.P('Regional structure correlate',
                               className='card-title'),
                        select('td-indicator', [], None,
                               style={'maxWidth': '260px'}),
                    ], className='card-header-row'),
                    html.P(id='td-indicator-desc', className='side-note'),
                    dcc.Loading(dcc.Graph(id='td-reg-scatter',
                                          config={'displayModeBar': False}),
                                type='circle', color=theme.PRIMARY,
                                delay_show=350),
                ]),
            ], className='grid-2'),
            card([
                html.P('Social gradients', className='card-title'),
                html.P('How the selected score differs across social groups '
                       'within the country. Dots are weighted group means; '
                       'hover for group sizes.', className='side-note'),
                dcc.Loading(dcc.Graph(id='td-gradients',
                                      config={'displayModeBar': False}),
                            type='circle', color=theme.PRIMARY,
                            delay_show=350),
            ]),
        ], className='main-content'),
    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab Corr - Correlations (factory: needs precomputed heatmap + MLM) ─────────

def _mlm_table(model: dict) -> dmc.Table:
    """Coefficient table for one multilevel model."""
    head = dmc.TableThead(dmc.TableTr([
        dmc.TableTh('Predictor'), dmc.TableTh('β'),
        dmc.TableTh('SE'), dmc.TableTh('p'),
    ]))
    rows = []
    for c in model['coefficients']:
        stars = ('***' if c['p'] < 0.001 else '**' if c['p'] < 0.01
                 else '*' if c['p'] < 0.05 else '')
        rows.append(dmc.TableTr([
            dmc.TableTd(c['label']),
            dmc.TableTd(f"{c['coef']:+.3f}{stars}"),
            dmc.TableTd(f"{c['se']:.3f}"),
            dmc.TableTd(f"{c['p']:.3f}" if c['p'] >= 0.001 else '<0.001'),
        ]))
    return dmc.Table([head, dmc.TableTbody(rows)],
                     striped=True, highlightOnHover=True,
                     className='mlm-table')


def make_mlm_section(results: dict) -> html.Div:
    """Multilevel-model card content built from precomputed results."""
    if not results or 'models' not in results:
        return html.Div()
    panels = []
    for col, model in results['models'].items():
        panels.append(dmc.AccordionItem([
            dmc.AccordionControl([
                html.Span(model['label'], style={'fontWeight': 600}),
                html.Span(f"  ·  ICC = {model['icc']:.1%}  ·  "
                          f"n = {model['n_obs']:,}",
                          className='mlm-meta'),
            ]),
            dmc.AccordionPanel(_mlm_table(model)),
        ], value=col))
    return card([
        html.P('Beyond bivariate: multilevel models', className='card-title'),
        html.P(
            'Country-level correlations cannot separate composition (who '
            'lives there) from context (what the country is like). These '
            'linear mixed-effects models predict each person\'s dimension '
            'score from individual characteristics and country-level macro '
            'predictors simultaneously, with random country intercepts. The '
            'ICC shows how much variance actually sits between countries. '
            f'{results.get("method", "")}',
            className='side-note'),
        dmc.Accordion(chevronPosition='right', variant='contained',
                      radius='md', children=panels),
    ])


def build_tab_corr(heatmap_fig, mlm_results: dict) -> html.Div:
    """Assemble the Correlations tab (heatmap is precomputed at startup)."""
    return html.Div([
        html.Div([
            html.Div([
                _subtitle(
                    'Pearson correlations between country-level predictors '
                    'and Schwartz dimensions across the 30 ESS11 countries. '
                    'Click any heatmap cell to open the scatter below.'),
                ctrl_group('X-axis (predictor)',
                           select('tc-x-var', SCATTER_X_OPTS, 'trust_mean',
                                  searchable=True)),
                ctrl_group('Y-axis (Schwartz dimension)',
                           select('tc-y-var', SCATTER_Y_OPTS, 'all')),
                html.Div(id='tc-x-desc'),
                html.Div([
                    html.P('Significance (FDR-adjusted)',
                           className='ctrl-label'),
                    html.Table([
                        html.Tr([html.Td('***'), html.Td('q < .001')]),
                        html.Tr([html.Td('**'),  html.Td('q < .01')]),
                        html.Tr([html.Td('*'),   html.Td('q < .05')]),
                    ], className='sig-table'),
                    html.P('q-values control the false-discovery rate across '
                           'all 76 tests (Benjamini-Hochberg).',
                           className='side-note'),
                ], className='sig-box'),
                info_accordion('Methods', [
                    ('Unit of analysis',
                     'Each point is one country in ESS Round 11 (2023). '
                     'ESS-derived predictors are weighted country means; '
                     'external indicators use the newest available year.'),
                    ('Statistical approach',
                     'Pearson r with an OLS fit and 95 % parametric CI band. '
                     'Because 76 correlations are tested at once, stars '
                     'reflect Benjamini-Hochberg adjusted q-values; raw '
                     'p-values are still shown for transparency.'),
                    ('Caveats',
                     'N = 30 countries is small; single influential countries '
                     'can move r substantially. Associations are descriptive, '
                     'not causal - see the multilevel models below for a '
                     'composition-vs-context decomposition.'),
                ]),
            ], className='sidebar'),
            html.Div([
                card([
                    html.P('Click any cell to open the scatter detail below.',
                           className='hint-right'),
                    dcc.Graph(id='tc-heatmap', figure=heatmap_fig,
                              config={'displayModeBar': False}),
                ]),
                card([
                    html.Div([
                        html.Button('', id='tc-expand-btn', n_clicks=0,
                                    className='chart-expand-btn',
                                    title='Fullscreen'),
                        dcc.Loading(dcc.Graph(id='tc-scatter',
                                              config={'displayModeBar': False}),
                                    type='circle', color=theme.PRIMARY,
                                    delay_show=350),
                    ], style={'position': 'relative'}),
                ]),
                make_mlm_section(mlm_results),
            ], className='main-content'),
        ], className='tab-with-sidebar'),

        html.Div(
            id='tc-overlay',
            className='chart-overlay',
            style={'display': 'none'},
            children=[html.Div([
                html.Button('✕', id='tc-overlay-close', n_clicks=0,
                            className='chart-overlay-close'),
                dcc.Graph(id='tc-scatter-full',
                          config={'displayModeBar': True,
                                  'modeBarButtonsToRemove': [
                                      'sendDataToCloud', 'editInChartStudio',
                                      'lasso2d', 'select2d']}),
            ], className='chart-overlay-inner')],
        ),
    ], className='tab-content')


# ── Tab 2 - Value Space ────────────────────────────────────────────────────────

tab2 = html.Div([
    html.Div([
        html.Div([
            _subtitle(
                'Countries placed by profile similarity using PCA (ESS Round '
                '11, 2023). Radar glyphs show each country\'s profile; '
                'colours are K-Means clusters.'),
            ctrl_group('Dimension group',
                       select('t2vs-dim-group', DIM_GROUP_OPTS, 'values')),
            html.Div(id='t2vs-dim-desc', className='side-note'),
            ctrl_group('Number of clusters',
                       dmc.Slider(id='t2vs-clusters', min=2, max=6, step=1,
                                  value=3, size='sm', radius='md',
                                  marks=[{'value': i, 'label': str(i)}
                                         for i in range(2, 7)],
                                  styles={'markLabel':
                                          {'fontSize': '10px'}})),
            html.Div(id='t2vs-validation', className='validation-box'),
            html.Div(id='t2vs-cluster-summary'),
            info_accordion('Methods', [
                ('PCA similarity space',
                 'Variables in the selected group are projected onto two '
                 'principal components (macro groups are z-scored first). '
                 'Countries close together have similar profiles. Variance '
                 'explained is shown on each axis.'),
                ('K-Means + silhouette',
                 'Clusters are computed in the full variable space (before '
                 'PCA). The silhouette score (-1 to +1) measures how well '
                 'separated the chosen clustering is; the suggested k '
                 'maximises it. With only ~30 countries and up to 10 '
                 'variables, clusters are descriptive groupings - not '
                 'statistically validated types.'),
                ('Glyph shapes',
                 'Each radar glyph shows the country\'s raw variable profile '
                 'centred at its PCA position. Shape tells you how, position '
                 'tells you who is similar.'),
            ]),
        ], className='sidebar'),
        html.Div([
            card(_expandable_graph('t2vs-graph')),
        ], className='main-content'),
    ], className='tab-with-sidebar'),
], className='tab-content')
