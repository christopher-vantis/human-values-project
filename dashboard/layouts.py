"""Static layout objects and pure UI helpers for the dashboard.

Nothing in this module accesses the loaded DataFrames (DF, DF_MICRO, …).
It imports only data_pipeline constants (COUNTRIES, ALL_YEARS, …) that are
available at import time without loading raw data.
"""
from dash import dcc, html, Input, Output, State
import data_pipeline as dp

# ── Aliases ────────────────────────────────────────────────────────────────────
_COUNTRIES    = dp.COUNTRIES
_ALL_YEARS    = dp.ALL_YEARS
_DIM_COLORS   = dp.DIM_COLORS
_YEAR_TO_ROUND = dp.YEAR_TO_ROUND

DEFAULT_YEAR    = 2023
DEFAULT_COUNTRY = 'DE'

# ── Inline-style shared constants ─────────────────────────────────────────────
_SLATE  = '#1a2840'
_BLUE   = '#1a5fb4'
_MUTED  = '#7a90b0'
_BODY   = '#3a4a60'
_CTRL   = '#edf0f7'
_PANEL  = '#f7f9fc'
_BORDER = '#c0cce0'

INFO_PANEL_STYLE = {   # used by app.py for the toggle open state
    'display': 'block',
    'margin-top': '10px',
    'padding': '10px 12px',
    'background-color': _PANEL,
    'border-radius': '6px',
    'border-left': f'3px solid {_BORDER}',
    'font-size': '11px',
    'color': _BODY,
    'line-height': '1.55',
}


# ── Pure UI helpers ────────────────────────────────────────────────────────────

def country_opts() -> list:
    return [{'label': _COUNTRIES[c], 'value': c}
            for c in sorted(_COUNTRIES.keys())]


def all_year_marks() -> dict:
    return {y: {'label': str(y), 'style': {'color': _SLATE, 'font-size': '11px'}}
            for y in _ALL_YEARS}


def _dim_chips():
    return [
        html.Div([
            html.Span('■', style={'color': c, 'font-size': '14px',
                                  'margin-right': '6px', 'flex-shrink': '0'}),
            html.Span(d, style={'color': _SLATE, 'font-size': '12px'}),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '5px'})
        for d, c in _DIM_COLORS.items()
    ]


def _dim_legend_chips():
    return [
        html.Div([
            html.Span('■', style={'color': c, 'font-size': '14px',
                                  'margin-right': '6px', 'flex-shrink': '0'}),
            html.Span(d, style={'color': _SLATE, 'font-size': '12px'}),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '5px'})
        for d, c in dp.DIM_COLORS.items()
    ]


def _ctrl_label(text):
    return html.Label(text, className='ctrl-label')


def _subtitle(text):
    return html.P(text, className='tab-subtitle')


def _interaction_box(items):
    return html.Div([
        html.P('Interactions', className='ctrl-label',
               style={'margin-bottom': '5px', 'margin-top': '0'}),
        *[html.Div([
            html.Span('→ ', style={'color': _BLUE, 'font-weight': '700',
                                   'flex-shrink': '0'}),
            html.Span(item, style={'color': _BODY, 'line-height': '1.45'}),
        ], style={'display': 'flex', 'align-items': 'flex-start',
                  'margin-bottom': '4px', 'font-size': '11.5px'})
          for item in items],
    ], style={'margin-top': '14px', 'padding': '8px 10px',
              'background-color': _CTRL, 'border-radius': '6px'})


def _axis_entry(label, body):
    return html.Div([
        html.B(label + ' - '),
        html.Span(body, style={'color': '#2a3a50'}),
    ], style={'margin-bottom': '7px', 'font-size': '12.5px', 'line-height': '1.55'})


def _method_panel(btn_id: str, content_id: str, rows: list):
    """Collapsible Info panel. rows = list of (title, body) tuples."""
    items = []
    for i, (title, body) in enumerate(rows):
        items.append(html.P(title, style={
            'font-weight': '700', 'color': _SLATE,
            'font-size': '11px', 'margin': '0 0 3px',
        }))
        items.append(html.P(body, style={
            'margin': '0 0 9px' if i < len(rows) - 1 else '0',
        }))
    return html.Div([
        html.Button(
            'Info',
            id=btn_id,
            n_clicks=0,
            style={
                'width': '100%',
                'background': 'none',
                'border': f'1px solid {_BORDER}',
                'border-radius': '5px',
                'padding': '6px 10px',
                'font-size': '11.5px',
                'color': '#4a6080',
                'cursor': 'pointer',
                'text-align': 'left',
                'font-family': 'inherit',
                'letter-spacing': '0.2px',
            },
        ),
        html.Div(items, id=content_id, style={'display': 'none'}),
    ], style={'margin-top': '14px'})


def _expandable_graph(graph_id: str,
                      config: dict | None = None,
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
        dcc.Graph(id=graph_id, config=cfg),
        *(extra_children or []),
    ], style={'position': 'relative'})
    overlay = html.Div(
        id=f'{graph_id}-overlay',
        className='scatter-overlay',
        style={'display': 'none'},
        children=[html.Div([
            html.Button('✕', id=f'{graph_id}-close-btn', n_clicks=0,
                        className='scatter-overlay-close'),
            dcc.Graph(id=f'{graph_id}-overlay-graph', config=overlay_cfg),
        ], className='scatter-overlay-inner')],
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
    """Sidebar cluster summary — one block per cluster with countries + dominant dim."""
    from figures.value_space import CLUSTER_COLORS
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
        color = CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]
        dim_scores = {
            dim: grp[[c for c in dcols if c in grp.columns]].mean(axis=1).mean()
            for dim, dcols in _dim_dcols.items()
        }
        dominant = max(dim_scores, key=dim_scores.get)
        items.append(html.Div([
            html.Span('● ', style={'color': color, 'font-size': '13px',
                                   'font-weight': '700'}),
            html.Span(f'Cluster {cid + 1}: ',
                      style={'font-weight': '600', 'color': _SLATE, 'font-size': '12px'}),
            html.Span(', '.join(sorted(grp['country_name'].tolist())),
                      style={'color': _BODY, 'font-size': '11.5px'}),
            html.Br(),
            html.Span(f'  ({dominant})',
                      style={'color': _MUTED, 'font-size': '11px', 'margin-left': '18px'}),
        ], style={'margin-bottom': '10px', 'line-height': '1.5'}))
    return items


# ── Dropdown option lists ──────────────────────────────────────────────────────

SCATTER_X_OPTS = [
    {'label': '─── ESS Social Variables ───',        'value': '_s1', 'disabled': True},
    {'label': 'Social Trust',                         'value': 'trust_mean'},
    {'label': 'Religiosity',                          'value': 'religiosity_mean'},
    {'label': 'Education Years',                      'value': 'eduyrs_mean'},
    {'label': 'Safety After Dark',                    'value': 'safety_mean'},
    {'label': 'Left-Right Scale',                     'value': 'lrscale_mean'},
    {'label': 'Mean Age',                             'value': 'age_mean'},
    {'label': 'Urbanisation (%)',                     'value': 'urban_pct'},
    {'label': 'Migration Background (%)',             'value': 'diversity_pct'},
    {'label': '─── External Macro Indicators ───',   'value': '_s2', 'disabled': True},
    {'label': 'Liberal Democracy',                    'value': 'v2x_libdem'},
    {'label': 'Gini Index',                           'value': 'wb_gini'},
    {'label': 'Unemployment (%)',                     'value': 'wb_unemployment'},
    {'label': 'GDP per Capita (PPP)',                 'value': 'wb_gdp_per_capita_ppp'},
    {'label': '─── Government Expenditure (COFOG) ───', 'value': '_s3', 'disabled': True},
    {'label': 'Gov. Health Exp.',                     'value': 'gov_exp_health'},
    {'label': 'Gov. Education Exp.',                  'value': 'gov_exp_education'},
    {'label': 'Gov. Social Exp.',                     'value': 'gov_exp_social'},
    {'label': 'Gov. Defence Exp.',                    'value': 'gov_exp_defence'},
    {'label': 'Gov. Economic Exp.',                   'value': 'gov_exp_economic'},
    {'label': 'Gov. Public Services Exp.',            'value': 'gov_exp_public_services'},
    {'label': 'Gov. Culture & Recreation Exp.',       'value': 'gov_exp_culture'},
]

SCATTER_Y_OPTS = [
    {'label': 'All 4 Dimensions (2×2)',  'value': 'all'},
    {'label': 'Openness to Change',      'value': 'dim_openness'},
    {'label': 'Self-Transcendence',      'value': 'dim_transcendence'},
    {'label': 'Conservation',            'value': 'dim_conservation'},
    {'label': 'Self-Enhancement',        'value': 'dim_enhancement'},
]

ROUND_OPTS = [{'label': 'All rounds (country means)', 'value': 'all'}] + [
    {'label': f'ESS {_YEAR_TO_ROUND[y]} ({y})', 'value': y}
    for y in _ALL_YEARS
]

DIM_GROUP_OPTS = [
    {'label': grp['label'], 'value': key}
    for key, grp in dp.DIMENSION_GROUPS.items()
]

DIM_OPTS = [{'label': 'All Dimensions', 'value': 'all'}] + [
    {'label': d, 'value': d} for d in dp.DIMS
]


# ── Landing page ──────────────────────────────────────────────────────────────

landing = html.Div([

    html.Div([
        html.H2('Schwartz Theory of Basic Human Values', className='lp-h2'),

        html.P([
            'In 1992, social psychologist Shalom Schwartz proposed that ',
            html.B('10 basic human values'), ' are universal across cultures - ',
            'motivational goals that guide attitudes and behaviour in every society. '
            'He arranged them in a circular structure (the ',
            html.Em('circumplex'), ') where neighbouring values reinforce each other '
            'and opposing values compete.',
        ], className='lp-p'),

        html.Div([
            html.Img(
                src='/assets/schwartz_values.jpg',
                style={'display': 'block', 'max-width': '480px', 'width': '100%',
                       'margin': '0 auto 6px', 'border-radius': '6px',
                       'box-shadow': '0 2px 10px rgba(0,0,0,0.10)'},
            ),
            html.P([
                'Source: Schwartz, S. H. (1992). Universals in the content and structure '
                'of values. ',
                html.Em('Advances in Experimental Social Psychology, 25'), ', 1-65. ',
                html.A('Google Scholar',
                       href='https://scholar.google.com/citations?view_op=view_citation'
                            '&hl=en&user=7gi3pqoAAAAJ&citation_for_view=7gi3pqoAAAAJ:d1gkVwhDpl0C',
                       target='_blank', style={'color': _BLUE}),
            ], style={'text-align': 'center', 'font-size': '10.5px',
                      'color': _MUTED, 'margin': '0'}),
        ], style={'margin': '18px 0 22px'}),

        html.P(['The 10 values cluster into ', html.B('4 higher-order dimensions:')],
               className='lp-p'),

        html.Div([
            html.Div([
                html.Span('■ ', style={'color': _DIM_COLORS['Openness to Change'],
                                       'font-size': '16px'}),
                html.B('Openness to Change '),
                html.Span('- Self-Direction, Stimulation, Hedonism. '
                          'Emphasises autonomy, novelty, and pleasure.',
                          style={'color': _BODY}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': _DIM_COLORS['Self-Transcendence'],
                                       'font-size': '16px'}),
                html.B('Self-Transcendence '),
                html.Span('- Universalism, Benevolence. '
                          'Emphasises welfare of others and of nature.',
                          style={'color': _BODY}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': _DIM_COLORS['Conservation'],
                                       'font-size': '16px'}),
                html.B('Conservation '),
                html.Span('- Security, Conformity, Tradition. '
                          'Emphasises order, self-restriction, and preserving the status quo.',
                          style={'color': _BODY}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': _DIM_COLORS['Self-Enhancement'],
                                       'font-size': '16px'}),
                html.B('Self-Enhancement '),
                html.Span('- Power, Achievement. '
                          'Emphasises personal success and dominance over others.',
                          style={'color': _BODY}),
            ], className='lp-dim-row'),
        ], className='lp-dim-block'),

        html.P(
            'Adjacent dimensions are motivationally compatible; opposing dimensions '
            'are in conflict - for example, openness to change vs. conservation, '
            'or self-transcendence vs. self-enhancement.',
            className='lp-p',
        ),

        html.P([
            'Values are measured in the ESS using the ',
            html.B('Portrait Values Questionnaire (PVQ-21)'), ': '
            '21 short portraits of people, and respondents rate how similar each '
            'person is to them. Scores are ',
            html.Em('ipsatized'), ' - centred at each respondent\'s own mean - '
            'so that only relative priorities matter, not absolute scale usage.',
        ], className='lp-p'),
    ], className='lp-section'),

    html.Hr(className='lp-hr'),

    html.Div([
        html.H2('The Dataset', className='lp-h2'),
        html.P([
            'Data come from the ',
            html.B('European Social Survey (ESS)'), ', Rounds 1-11 (2002-2023), '
            'conducted approximately every two years across Europe. '
            'Individual-level survey responses are aggregated to country × round level. '
            'The dashboard covers all ', html.B('39 countries'), ' that have ever '
            'participated in the ESS, from 1 round (Albania, Kosovo, Romania) '
            'to 11 rounds (Belgium, Finland, France, Ireland, Netherlands, Norway, '
            'Portugal, Slovenia, Switzerland). Countries with fewer rounds appear '
            'only for the years they participated.',
        ], className='lp-p'),

        html.P([html.B('ESS-derived social variables'),
                ' - computed from individual responses, aggregated to country × round means:'],
               className='lp-p', style={'margin-bottom': '4px'}),
        html.Ul([
            html.Li([html.B('Social Trust: '),
                     'ppltrst - "Most people can be trusted or you can\'t be too careful" (0-10).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Religiosity: '),
                     'rlgdgr - self-rated degree of religiosity (0-10).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Safety After Dark: '),
                     'aesfdrk - feeling of safety walking alone locally after dark (1=very safe, 4=very unsafe).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Left-Right Political Placement: '),
                     'lrscale - self-placement on the political spectrum (0=left, 10=right).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Mean Age: '), 'agea - mean respondent age in years.'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Urbanisation: '),
                     'domicil - share of respondents living in a big city or its suburbs (%).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Migration Background: '),
                     'brncntr, facntr, mocntr - share of respondents born abroad or '
                     'with at least one parent born abroad (%).'],
                    className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([html.B('Education Years: '),
                     'eduyrs - mean years of completed full-time education '
                     '(non-responses 77, 88, 99 excluded).'],
                    className='lp-li'),
        ], className='lp-ul'),

        html.P([html.B('External macro indicators'),
                ' - matched to ESS reference years per country:'],
               className='lp-p', style={'margin-bottom': '4px'}),
        html.Ul([
            html.Li([
                html.B('Liberal Democracy Index: '),
                'V-Dem Project, Country-Year dataset v15 (v2x_libdem, 0-1). '
                'Varieties of Democracy Institute, University of Gothenburg. '
                'Full coverage for all 39 ESS countries.',
            ], className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([
                html.B('Gini Index (income inequality, 0-100): '),
                'Primary source: OECD Income Distribution Database '
                '(closest-year matching to ESS rounds). '
                'Supplemented for Ireland (IE) with Eurostat EU-SILC, '
                'and for all remaining 22 countries with ',
                html.B('World Bank Development Indicators (SI.POV.GINI)'), '. '
                'All values are observed survey data - no imputation.',
            ], className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([
                html.B('Unemployment Rate (% of labour force): '),
                'Primary source: OECD harmonized unemployment rates. '
                'For 22 additional countries: ',
                html.B('World Bank / ILO modelled estimates (SL.UEM.TOTL.ZS)'), '.',
            ], className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([
                html.B('GDP per Capita (PPP): '),
                'World Bank World Development Indicators '
                '(NY.GDP.PCAP.PP.KD - constant 2017 international $).',
            ], className='lp-li'),
        ], className='lp-ul'),

        html.P([html.B('Government expenditure (COFOG classification)'),
                ' - all values as % of GDP:'],
               className='lp-p', style={'margin-bottom': '4px'}),
        html.Ul([
            html.Li([
                html.B('EU / EEA countries (30): '),
                'Eurostat Government Finance Statistics (gov_10a_exp, PC_GDP unit, '
                'sector S13 general government). Covers GF01-GF10 all COFOG functions.',
            ], className='lp-li', style={'margin-bottom': '6px'}),
            html.Li([
                html.B('Non-EU countries — Health (GF07): '),
                'World Bank SH.XPD.GHED.GD.ZS. 38/39 countries; Kosovo unavailable.',
            ], className='lp-li', style={'margin-bottom': '6px'}),
            html.Li([
                html.B('Non-EU countries — Education (GF09): '),
                'World Bank SE.XPD.TOTL.GD.ZS. 37/39 countries.',
            ], className='lp-li', style={'margin-bottom': '6px'}),
            html.Li([
                html.B('Non-EU countries — Defence (GF02): '),
                'World Bank MS.MIL.XPND.GD.ZS. Full coverage: 39/39.',
            ], className='lp-li', style={'margin-bottom': '6px'}),
            html.Li([
                html.B('Social Protection, Economic Affairs, Public Services, Culture: '),
                'Eurostat gov_10a_exp only — 29 EU/EEA countries. '
                'Non-EU/EEA countries show partial polygons (health + education + defence).',
            ], className='lp-li'),
        ], className='lp-ul'),
    ], className='lp-section'),

    html.Hr(className='lp-hr'),

    html.Div([
        html.H2('Missing Data in Structural Indicators', className='lp-h2'),
        html.P([
            'The 12 structural indicators in the Country Profile tab are drawn from '
            'multiple sources with different country coverage. Missing values (shown as '
            '"n/a") are never imputed - the reason is always documented. The main gaps are:',
        ], className='lp-p'),
        html.Ul([
            html.Li([html.B('EIGE Gender Equality Index (26/39): '),
                     'Covers EU27 only. Missing: AL, CH, GB, IL, IS, ME, MK, NO, RS, RU, TR, UA, XK.'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('OECD Trade Union Density (28/39): '),
                     'Missing: AL, BG, CY, HR, ME, MK, RO, RS, RU, UA, XK.'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('Eurostat Healthy Life Years (30/39): '),
                     'Covers EU and EEA. Missing: AL, IL, ME, MK, RS, RU, TR, UA, XK.'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('Eurostat Tertiary Attainment (34/39): '),
                     'Missing: AL, IL, RU, UA, XK.'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('Eurostat GDP per Capita PPS (35/39): '),
                     'Missing: IL, RU, UA, XK.'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('Eurostat Gini (36/39): '),
                     'Missing: IL (not in EU-SILC), RU, UA (WB data only through 2020).'],
                    className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([html.B('Kosovo (XK) across multiple indicators: '),
                     'As a non-UN-member territory, XK is excluded from TI CPI, WHR, '
                     'World Bank migrant stock, OECD, EIGE, and several Eurostat datasets.'],
                    className='lp-li'),
        ], className='lp-ul'),
        html.P([
            'ESS-derived indicators (Social Trust %, Religiosity %) and V-Dem Liberal '
            'Democracy Index achieve full 39/39 coverage.',
        ], className='lp-p'),
    ], className='lp-section'),

    html.Hr(className='lp-hr'),

    html.Div([
        html.H2('Limitations', className='lp-h2'),

        html.Div([
            html.B('1. Pan-cultural regularities'),
            html.P([
                'Schwartz and Bardi (2001) showed across 13 samples from 56 countries that value '
                'hierarchies share a remarkably stable cross-cultural structure: Benevolence and '
                'Universalism rank near the top in virtually all societies; Stimulation, Tradition, '
                'and Power near the bottom. If countries consistently show a positive delta for '
                'Benevolence/Universalism and a negative one for Stimulation, that reflects a '
                'universal regularity - not a country-specific finding. ',
                html.B('What is informative are the deviations of individual countries from the '
                       'cross-national average.'),
            ], className='lp-p', style={'margin-top': '4px'}),
        ], className='lp-limitation'),

        html.Div([
            html.B('2. Measurement invariance'),
            html.P([
                'Davidov, Schmidt, and Schwartz (2008) demonstrated that PVQ-21 items in '
                'cross-national comparisons often achieve only configural invariance, rarely '
                'metric, and almost never scalar invariance. Mean-centring (ipsatisation) '
                'mitigates this problem but does not eliminate it. Statements such as '
                '"Universalism ranks higher in France than in Hungary" should therefore be '
                'read as ',
                html.Em('indicators of structural differences'),
                ' - not as precise quantifications.',
            ], className='lp-p', style={'margin-top': '4px'}),
        ], className='lp-limitation'),

        html.Div([
            html.B('3. Within- vs. between-country variance'),
            html.P([
                'Magun, Rudnev, and Schmidt (2016) showed via latent class analysis that '
                'value diversity ',
                html.Em('within'),
                ' European countries is often greater than the diversity ',
                html.Em('between'),
                ' them. A national value profile is an aggregate, not a cultural essence. '
                'Individual-level profiles (Tab 4) complement the country-level view, '
                'but even these are a stratified sample - not a population census.',
            ], className='lp-p', style={'margin-top': '4px'}),
        ], className='lp-limitation'),

    ], className='lp-section'),

], className='landing-page')


# ── Tab 1 - Country Profile ───────────────────────────────────────────────────

tab1 = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Single-country value profile for one ESS round. '
                'Δ-scores show each value\'s deviation from that country\'s '
                'own average - positive means above-average priority.'
            ),
            _ctrl_label('Country'),
            dcc.Dropdown(
                id='t1-country',
                options=country_opts(),
                value=DEFAULT_COUNTRY,
                clearable=False,
                className='ctrl-dropdown',
            ),
            html.Div(style={'height': '14px'}),
            _ctrl_label('ESS Round'),
            dcc.Slider(
                id='t1-year',
                min=min(_ALL_YEARS), max=max(_ALL_YEARS), step=None,
                marks={},           # filled by update_t1_slider callback on load
                value=DEFAULT_YEAR, included=False,
                className='tab1-slider', vertical=True, verticalHeight=320,
            ),
            html.Div(style={'height': '16px'}),
            html.Div([
                html.P('Higher-order dimensions:', className='ctrl-label',
                       style={'margin-bottom': '6px'}),
                *_dim_chips(),
            ], className='dim-legend-sidebar'),
            _interaction_box([
                'Hover spoke points to see value name & Δ-score',
                'Select a country from the dropdown',
                'Drag the slider to change ESS round',
            ]),
            _method_panel('t1-method-btn', 't1-method-content', [
                ('Δ-scores',
                 'Each value is centred at that country\'s mean across all 10 values '
                 'for the selected round. A positive score indicates above-average '
                 'relative priority; negative means below-average. Centring removes '
                 'country-level scale-use biases so that only relative priorities matter.'),
                ('PVQ-21 measurement',
                 'Values are elicited via 21 short portrait descriptions. Respondents '
                 'rate how similar each portrait is to them on a 1-6 scale. Item means '
                 'are aggregated at country × ESS round level after excluding '
                 'out-of-range missing codes.'),
                ('Higher-order dimensions',
                 'The 10 basic values are grouped into 4 dimensions following '
                 'Schwartz\'s theoretical structure. Coloured arcs on the outer ring '
                 'mark these groupings: Openness to Change (Self-Direction, Stimulation, '
                 'Hedonism), Self-Transcendence (Universalism, Benevolence), '
                 'Conservation (Security, Conformity, Tradition), '
                 'Self-Enhancement (Power, Achievement).'),
            ]),
        ], className='sidebar'),

        html.Div([
            _expandable_graph('t1-radar',
                              extra_children=[html.Div(id='t1-country-info')]),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab Corr - Correlations ───────────────────────────────────────────────────

tab_corr = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Pearson correlations between country-level predictors and '
                'Schwartz value dimensions. N varies per round (up to 39 countries). '
                'Regression line with 95 % CI band.'
            ),
            _ctrl_label('ESS Round'),
            dcc.Dropdown(id='tc-round', options=ROUND_OPTS, value=2023,
                         clearable=False, className='ctrl-dropdown'),
            html.Div(style={'height': '14px'}),
            _ctrl_label('X-Axis (Predictor)'),
            dcc.Dropdown(id='tc-x-var', options=SCATTER_X_OPTS, value='trust_mean',
                         clearable=False, className='ctrl-dropdown', optionHeight=32),
            html.Div(style={'height': '14px'}),
            _ctrl_label('Y-Axis (Schwartz Dimension)'),
            dcc.Dropdown(id='tc-y-var', options=SCATTER_Y_OPTS, value='all',
                         clearable=False, className='ctrl-dropdown'),
            html.Div(style={'height': '18px'}),
            html.Div(id='tc-x-desc'),
            html.Div(style={'height': '14px'}),
            html.Div([
                html.P('Significance levels',
                       style={'font-size': '11px', 'font-weight': '700',
                              'color': _SLATE, 'margin': '0 0 6px'}),
                html.Table([
                    html.Tr([html.Td('***', style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': _SLATE}),
                             html.Td('p < .001', style={'font-size': '11px',
                                                        'color': _BODY})]),
                    html.Tr([html.Td('**',  style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': _SLATE}),
                             html.Td('p < .01',  style={'font-size': '11px',
                                                        'color': _BODY})]),
                    html.Tr([html.Td('*',   style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': _SLATE}),
                             html.Td('p < .05',  style={'font-size': '11px',
                                                        'color': _BODY})]),
                ], style={'border-spacing': '0', 'margin': '0'}),
            ], style={'padding': '10px 12px', 'background-color': _CTRL,
                      'border-radius': '6px', 'border-left': f'3px solid {_BLUE}'}),
            _interaction_box([
                'Switch the X-axis to compare different predictors',
                'Choose "All 4 Dimensions" for a 2×2 overview',
                'Hover a country flag for name and exact values',
            ]),
            _method_panel('tc-method-btn', 'tc-method-content', [
                ('Unit of analysis',
                 'Each data point is one country in one ESS round. Selecting '
                 '"All rounds" aggregates to a single point per country - the mean '
                 'of that country\'s values across all rounds it participated in.'),
                ('Predictor variables',
                 'Three categories: ESS-derived social variables (country-round means '
                 'from the survey), external macro indicators (V-Dem, World Bank GDP, '
                 'Gini, unemployment), and Eurostat COFOG government expenditure shares. '
                 'Source details appear below the predictor dropdown.'),
                ('Statistical approach',
                 'Pearson r measures the linear association between predictor and '
                 'Schwartz dimension. The OLS regression line and 95 % parametric '
                 'confidence band are computed from the visible data points. N is '
                 'shown in each panel annotation and varies by round.'),
            ]),
        ], className='sidebar'),

        html.Div([
            html.P(
                'Click any cell to jump to the scatter detail below.',
                style={'font-size': '11px', 'color': _MUTED,
                       'margin': '0 0 4px', 'text-align': 'right'},
            ),
            dcc.Graph(id='tc-heatmap', config={'displayModeBar': False}),
            html.Div(id='tc-scatter-wrap', children=[
                html.Hr(style={'border': 'none', 'border-top': '1px solid #d8e0ea',
                               'margin': '6px 0 2px'}),
                html.Div([
                    html.Button('', id='tc-expand-btn', n_clicks=0,
                                className='chart-expand-btn', title='Fullscreen'),
                    dcc.Graph(id='tc-scatter', config={'displayModeBar': False}),
                ], style={'position': 'relative'}),
            ]),
        ], className='main-content'),

    ], className='tab-with-sidebar'),

    html.Div(
        id='tc-overlay',
        className='scatter-overlay',
        style={'display': 'none'},
        children=[html.Div([
            html.Button('✕', id='tc-overlay-close', n_clicks=0,
                        className='scatter-overlay-close'),
            dcc.Graph(id='tc-scatter-full',
                      config={'displayModeBar': True,
                              'modeBarButtonsToRemove': [
                                  'sendDataToCloud', 'editInChartStudio',
                                  'lasso2d', 'select2d']}),
        ], className='scatter-overlay-inner')],
    ),
], className='tab-content')


# ── Tab 2 - Value Space ───────────────────────────────────────────────────────

tab2 = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Countries placed by similarity in the selected dimension using PCA. '
                'Radar glyphs show each country\'s profile. '
                'Clusters group countries with similar patterns.'
            ),
            _ctrl_label('Dimension'),
            dcc.Dropdown(id='t2vs-dim-group', options=DIM_GROUP_OPTS, value='values',
                         clearable=False, className='ctrl-dropdown'),
            html.Div(id='t2vs-dim-desc', style={
                'font-size': '10.5px', 'color': _MUTED, 'line-height': '1.45',
                'margin': '6px 0 10px', 'font-style': 'italic',
            }),
            _ctrl_label('ESS Round'),
            dcc.Slider(
                id='t2vs-year',
                min=min(_ALL_YEARS), max=max(_ALL_YEARS), step=None,
                marks=all_year_marks(),
                value=DEFAULT_YEAR, included=False,
                className='tab1-slider', vertical=True, verticalHeight=240,
            ),
            html.Div(style={'height': '18px'}),
            _ctrl_label('Number of Clusters'),
            dcc.Slider(id='t2vs-clusters', min=2, max=6, step=1, value=3,
                       marks={i: str(i) for i in range(2, 7)}, included=False),
            html.Div(style={'height': '16px'}),
            html.Div(id='t2vs-cluster-summary'),
            _interaction_box([
                'Switch the Dimension dropdown to compare different profiles',
                'Hover over a country point for variable details',
                'Adjust the cluster slider to change group count',
                'Use the year slider to explore change over time',
            ]),
            _method_panel('t2-method-btn', 't2-method-content', [
                ('PCA similarity space',
                 'Variables in the selected dimension are z-scored and projected onto '
                 '2 principal components. Countries close together have similar profiles; '
                 'countries far apart differ substantially. '
                 'Variance explained by each axis is shown in the label.'),
                ('Glyph shapes',
                 'Each radar glyph shows the original variable values centred at the '
                 'country\'s PCA position. Glyph shape tells you how — position tells '
                 'you who is similar.'),
                ('K-Means clustering',
                 'Clusters are computed in the full multi-dimensional space (before PCA). '
                 'Coloured regions show cluster membership.'),
                ('Coverage note',
                 'Not all countries have data for every dimension. Government Spending '
                 'covers up to 39 countries; Defence = 39/39, Health = 38/39. '
                 'Countries with incomplete data for the chosen group are excluded from '
                 'the PCA.'),
            ]),
        ], className='sidebar'),

        html.Div([
            _expandable_graph('t2vs-graph'),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab 3 - Parallel Coordinates ─────────────────────────────────────────────

tab3 = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Each line is one ESS respondent, pooled across all '
                '11 rounds and 39 countries. Lines are coloured by the '
                'person\'s dominant Schwartz value dimension - the '
                'higher-order dimension with the highest relative priority. '
                'Each group is a stratified sample of 300 respondents.'
            ),
            _ctrl_label('Highlight Dimension'),
            dcc.Dropdown(id='t3-dim', options=DIM_OPTS, value='all',
                         clearable=False, className='ctrl-dropdown'),
            html.Div(style={'height': '16px'}),
            html.Div([
                html.P('Dimension colors:', className='ctrl-label',
                       style={'margin-bottom': '6px'}),
                *_dim_legend_chips(),
            ], className='dim-legend-sidebar'),
            _interaction_box([
                'Select a dimension to fade others and spotlight one group',
                'Drag on any axis to filter respondents to a range',
                'Drag the selection band to move it up / down the axis',
                'Combine filters across axes to narrow to a specific profile',
            ]),
            _method_panel('t3-method-btn', 't3-method-content', [
                ('Data and sampling',
                 'Individual ESS respondents are pooled across all 11 rounds and up to '
                 '39 countries. To keep the visualisation legible, 300 respondents per '
                 'dominant dimension are selected via stratified random sampling '
                 '(1 200 total). The random seed is fixed, so results are reproducible.'),
                ('Dominant dimension',
                 'Each respondent\'s PVQ items are ipsatized - centred at their '
                 'personal mean to remove individual scale-use tendencies. Four '
                 'higher-order dimension scores are then computed, and the dimension '
                 'with the highest relative score is assigned as that respondent\'s '
                 'dominant dimension.'),
                ('Axis filtering',
                 'Drag on any axis to create a range filter. Multiple filters across '
                 'axes combine to isolate respondents that satisfy all conditions '
                 'simultaneously. Drag the filter band along an axis to shift the '
                 'selected range without changing its width.'),
            ]),
        ], className='sidebar'),

        html.Div([
            html.H3(id='t3-title', style={
                'font-size': '13px', 'font-weight': '600',
                'color': '#0d1b2a', 'margin-bottom': '6px',
                'text-align': 'center',
            }),
            _expandable_graph('t3-parallel'),
            html.Div([
                html.P('Axis guide', style={
                    'font-size': '11px', 'font-weight': '700',
                    'text-transform': 'uppercase', 'letter-spacing': '0.6px',
                    'color': _MUTED, 'margin': '0 0 10px',
                }),
                html.Div([
                    _axis_entry('Interpersonal Trust',
                        'ESS variable ppltrst. Scale 0-10: 0 = "you can\'t be too careful", '
                        '10 = "most people can be trusted".'),
                    _axis_entry('Trust in Politicians',
                        'ESS variable trstplt. Scale 0-10: 0 = no trust at all, 10 = complete trust.'),
                    _axis_entry('Trust: Legal System',
                        'ESS variable trstlgl. Scale 0-10: 0 = no trust, 10 = complete trust.'),
                    _axis_entry('Life Satisfaction',
                        'ESS variable stflife. Scale 0-10: 0 = extremely dissatisfied, '
                        '10 = extremely satisfied.'),
                    _axis_entry('Econ. Satisfaction',
                        'ESS variable stfeco. Scale 0-10: satisfaction with the present '
                        'state of the economy in the country.'),
                    _axis_entry('Democracy Satisfaction',
                        'ESS variable stfdem. Scale 0-10: satisfaction with the way '
                        'democracy works in the country.'),
                    _axis_entry('Left-Right Scale',
                        'ESS variable lrscale. Scale 0-10: 0 = far left, 10 = far right.'),
                    _axis_entry('Immigration Attitude',
                        'ESS variable imwbcnt. Scale 0-10: 0 = immigrants make the country '
                        'a worse place to live, 10 = a better place.'),
                    _axis_entry('Redistribution Support',
                        'Derived from ESS variable gincdif (inverted). Higher = stronger '
                        'agreement that government should reduce income differences. Scale 1-5.'),
                    _axis_entry('Religiosity',
                        'ESS variable rlgdgr. Scale 0-10: 0 = not religious at all, '
                        '10 = very religious.'),
                    _axis_entry('Safety After Dark',
                        'Derived from ESS variable aesfdrk (inverted). Higher = feels '
                        'safer walking alone in local area after dark. Scale 1-4.'),
                ]),
            ], style={
                'margin-top': '16px', 'padding': '12px 16px',
                'background-color': _CTRL, 'border-radius': '6px',
                'border-left': f'3px solid {_BLUE}',
            }),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')
