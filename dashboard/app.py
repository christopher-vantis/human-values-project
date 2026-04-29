import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dash import Dash, dcc, html, Input, Output, State, ctx
import pandas as pd

import data_pipeline as dp
from figures.radar       import make_radar_single
from figures.parallel    import make_parallel, make_country_legend, make_parallel_micro
from figures.value_space import make_value_space_figure, CLUSTER_COLORS
from figures.scatter     import make_scatter_single, make_scatter_all

# ── Data ──────────────────────────────────────────────────────────────────────
DF          = dp.load_data()
DF_MICRO    = dp.load_micro_individual(sample_per_dim=300)
DF_SCATTER  = dp.load_scatter_data()
DF_IND, INDICATOR_SENTENCES = dp.load_indicators()
ALL_YEARS      = dp.ALL_YEARS
COUNTRIES      = dp.COUNTRIES
DIM_COLORS     = dp.DIM_COLORS
DIMS           = dp.DIMS
BG_COLOR       = dp.BG_COLOR
COUNTRY_COLORS = dp.COUNTRY_COLORS

DEFAULT_YEAR    = 2023
DEFAULT_COUNTRY = 'DE'
ALL_COUNTRY_CODES = sorted(COUNTRIES.keys())


# ── UI helpers ────────────────────────────────────────────────────────────────

def _country_opts():
    return [{'label': COUNTRIES[c], 'value': c} for c in ALL_COUNTRY_CODES]


def _year_slider_marks(country: str) -> dict:
    avail = set(DF[DF['cntry'] == country]['year'].unique())
    marks = {}
    for y in ALL_YEARS:
        if y in avail:
            marks[y] = {'label': str(y),
                        'style': {'color': '#1a2840', 'font-size': '11px'}}
        else:
            marks[y] = {'label': str(y),
                        'style': {'color': '#bbbbbb', 'font-size': '11px',
                                  'text-decoration': 'line-through'}}
    return marks


def _all_year_marks() -> dict:
    return {y: {'label': str(y), 'style': {'color': '#1a2840', 'font-size': '11px'}}
            for y in ALL_YEARS}


def _nearest_available(country: str, year: int) -> int:
    avail = sorted(DF[DF['cntry'] == country]['year'].unique())
    return min(avail, key=lambda y: abs(y - year))


def _dim_chips():
    return [
        html.Div([
            html.Span('■', style={'color': c, 'font-size': '14px',
                                  'margin-right': '6px', 'flex-shrink': '0'}),
            html.Span(d, style={'color': '#1a2840', 'font-size': '12px'}),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '5px'})
        for d, c in DIM_COLORS.items()
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
            html.Span('→ ', style={'color': '#1a5fb4', 'font-weight': '700',
                                   'flex-shrink': '0'}),
            html.Span(item, style={'color': '#3a4a60', 'line-height': '1.45'}),
        ], style={'display': 'flex', 'align-items': 'flex-start',
                  'margin-bottom': '4px', 'font-size': '11.5px'})
          for item in items],
    ], style={
        'margin-top': '14px',
        'padding': '8px 10px',
        'background-color': '#edf0f7',
        'border-radius': '6px',
    })


_METHOD_OPEN = {
    'display': 'block',
    'margin-top': '10px',
    'padding': '10px 12px',
    'background-color': '#f7f9fc',
    'border-radius': '6px',
    'border-left': '3px solid #c0cce0',
    'font-size': '11px',
    'color': '#3a4a60',
    'line-height': '1.55',
}


def _method_panel(btn_id: str, content_id: str, rows: list):
    """Collapsible methodology panel. rows = list of (title, body) tuples."""
    items = []
    for i, (title, body) in enumerate(rows):
        items.append(html.P(title, style={
            'font-weight': '700', 'color': '#1a2840',
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
                'border': '1px solid #c0cce0',
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


def _make_cluster_summary(result, n_clusters):
    """Sidebar cluster summary: one line per cluster with countries and dominant dim."""
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
        country_names = sorted(grp['country_name'].tolist())
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
                      style={'font-weight': '600', 'color': '#1a2840',
                             'font-size': '12px'}),
            html.Span(', '.join(country_names),
                      style={'color': '#3a4a60', 'font-size': '11.5px'}),
            html.Br(),
            html.Span(f'  ({dominant})',
                      style={'color': '#7a90b0', 'font-size': '11px',
                             'margin-left': '18px'}),
        ], style={'margin-bottom': '10px', 'line-height': '1.5'}))

    return items


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
                style={
                    'display': 'block',
                    'max-width': '480px',
                    'width': '100%',
                    'margin': '0 auto 6px',
                    'border-radius': '6px',
                    'box-shadow': '0 2px 10px rgba(0,0,0,0.10)',
                },
            ),
            html.P([
                'Source: Schwartz, S. H. (1992). Universals in the content and structure '
                'of values. ',
                html.Em('Advances in Experimental Social Psychology, 25'), ', 1-65. ',
                html.A(
                    'Google Scholar',
                    href='https://scholar.google.com/citations?view_op=view_citation'
                         '&hl=en&user=7gi3pqoAAAAJ&citation_for_view=7gi3pqoAAAAJ:d1gkVwhDpl0C',
                    target='_blank',
                    style={'color': '#1a5fb4'},
                ),
            ], style={
                'text-align': 'center',
                'font-size': '10.5px',
                'color': '#7a90b0',
                'margin': '0',
            }),
        ], style={'margin': '18px 0 22px'}),

        html.P([
            'The 10 values cluster into ', html.B('4 higher-order dimensions:'),
        ], className='lp-p'),

        html.Div([
            html.Div([
                html.Span('■ ', style={'color': DIM_COLORS['Openness to Change'],
                                       'font-size': '16px'}),
                html.B('Openness to Change '),
                html.Span('- Self-Direction, Stimulation, Hedonism. '
                          'Emphasises autonomy, novelty, and pleasure.',
                          style={'color': '#3a4a60'}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': DIM_COLORS['Self-Transcendence'],
                                       'font-size': '16px'}),
                html.B('Self-Transcendence '),
                html.Span('- Universalism, Benevolence. '
                          'Emphasises welfare of others and of nature.',
                          style={'color': '#3a4a60'}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': DIM_COLORS['Conservation'],
                                       'font-size': '16px'}),
                html.B('Conservation '),
                html.Span('- Security, Conformity, Tradition. '
                          'Emphasises order, self-restriction, and preserving the status quo.',
                          style={'color': '#3a4a60'}),
            ], className='lp-dim-row'),
            html.Div([
                html.Span('■ ', style={'color': DIM_COLORS['Self-Enhancement'],
                                       'font-size': '16px'}),
                html.B('Self-Enhancement '),
                html.Span('- Power, Achievement. '
                          'Emphasises personal success and dominance over others.',
                          style={'color': '#3a4a60'}),
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
            'Individual-level survey responses are aggregated to country x round level. '
            'The dashboard covers all ', html.B('39 countries'), ' that have ever '
            'participated in the ESS, from 1 round (Albania, Kosovo, Romania) '
            'to 11 rounds (Belgium, Finland, France, Ireland, Netherlands, Norway, '
            'Portugal, Slovenia, Switzerland). Countries with fewer rounds appear '
            'only for the years they participated.',
        ], className='lp-p'),

        # ── ESS social aggregates ──
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
            html.Li([html.B('Mean Age: '),
                     'agea - mean respondent age in years.'],
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

        # ── External macro indicators ──
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
                html.B('World Bank Development Indicators (SI.POV.GINI)'), ', '
                'which uses Eurostat EU-SILC as the underlying source for EU/EEA members '
                'and national household surveys for others. '
                'All values are observed survey data - no imputation. '
                'Kosovo (XK) unemployment is unavailable (no ILO estimate published).',
            ], className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([
                html.B('Unemployment Rate (% of labour force): '),
                'Primary source: OECD harmonized unemployment rates '
                '(supplemented with OECD data for Switzerland). '
                'For the 22 additional countries not covered by the OECD file: ',
                html.B('World Bank / ILO modelled estimates (SL.UEM.TOTL.ZS)'), '. '
                'OECD harmonized and ILO modelled estimates use the same ILO '
                'definition but differ slightly in methodology.',
            ], className='lp-li', style={'margin-bottom': '5px'}),
            html.Li([
                html.B('GDP per Capita (PPP): '),
                'World Bank World Development Indicators '
                '(NY.GDP.PCAP.PP.KD - constant 2017 international $).',
            ], className='lp-li'),
        ], className='lp-ul'),

        # ── Government expenditure ──
        html.P([html.B('Government expenditure (COFOG classification)'),
                ' - Eurostat Government Finance Statistics, total general government expenditure as % of GDP:'],
               className='lp-p', style={'margin-bottom': '4px'}),
        html.Ul([
            html.Li('GF01 General Public Services · GF02 Defence · GF04 Economic Affairs · '
                    'GF07 Health · GF08 Culture & Recreation · GF09 Education · GF10 Social Protection.',
                    className='lp-li'),
        ], className='lp-ul'),
    ], className='lp-section'),

    html.Hr(className='lp-hr'),

    html.Div([
        html.H2('Missing Data in Structural Indicators', className='lp-h2'),

        html.P([
            'The 12 structural indicators shown in the Country Profile tab are drawn '
            'from multiple sources with different country coverage. '
            'Missing values (shown as "n/a") are never imputed - the reason is always '
            'documented. The main gaps are:',
        ], className='lp-p'),

        html.Ul([
            html.Li([
                html.B('EIGE Gender Equality Index (26/39 countries): '),
                'Covers EU27 member states only. Countries outside EIGE scope: '
                'Albania, Switzerland, United Kingdom (Brexit 2020), Israel, Iceland, '
                'Montenegro, North Macedonia, Norway, Serbia, Russia, Turkiye, Ukraine, Kosovo.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('OECD Trade Union Density (28/39 countries): '),
                'Coverage limited to OECD member and partner countries in the TUD dataset. '
                'Missing: Albania, Bulgaria, Cyprus, Croatia, Montenegro, North Macedonia, '
                'Romania, Serbia, Russia, Ukraine, Kosovo.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('Eurostat Healthy Life Years (30/39 countries): '),
                'Eurostat hlth_hlye covers EU and EEA members. '
                'Missing: Albania, Israel, Montenegro, North Macedonia, Serbia, Russia, '
                'Turkiye, Ukraine, Kosovo.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('Eurostat Tertiary Attainment (34/39 countries): '),
                'Missing: Albania, Israel, Russia, Ukraine, Kosovo - not covered by Eurostat edat_lfse_03.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('Eurostat GDP per Capita PPS (35/39 countries): '),
                'Missing: Israel, Russia, Ukraine, Kosovo - not included in the Eurostat PPS reference framework.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('Eurostat Gini (36/39 countries): '),
                'Israel: not covered by Eurostat EU-SILC. '
                'Russia: no Eurostat coverage. '
                'Ukraine: World Bank Gini data available only through 2020; no recent estimate.',
            ], className='lp-li', style={'margin-bottom': '8px'}),
            html.Li([
                html.B('Kosovo (XK) across multiple indicators: '),
                'As a non-UN-member territory, Kosovo is excluded from several '
                'international datasets (TI CPI, World Happiness Report, World Bank '
                'migrant stock, OECD, EIGE, Eurostat for several indicators).',
            ], className='lp-li'),
        ], className='lp-ul'),

        html.P([
            'ESS-derived indicators (Social Trust %, Religiosity %) and V-Dem Liberal '
            'Democracy Index achieve full 39/39 coverage. '
            'For ESS indicators, the most recent ESS round in which the country participated '
            'is used (varying from round 2 in 2004 for Luxembourg to round 11 in 2023 '
            'for most countries).',
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
                options=_country_opts(),
                value=DEFAULT_COUNTRY,
                clearable=False,
                className='ctrl-dropdown',
            ),
            html.Div(style={'height': '14px'}),
            _ctrl_label('ESS Round'),
            dcc.Slider(
                id='t1-year',
                min=min(ALL_YEARS), max=max(ALL_YEARS), step=None,
                marks=_year_slider_marks(DEFAULT_COUNTRY),
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
            dcc.Graph(id='t1-radar', config={'displayModeBar': False}),
            html.Div(id='t1-country-info'),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab Corr - Correlations ───────────────────────────────────────────────────

_SCATTER_X_OPTS = [
    {'label': '─── ESS Social Variables ───', 'value': '_s1', 'disabled': True},
    {'label': 'Social Trust',             'value': 'trust_mean'},
    {'label': 'Religiosity',              'value': 'religiosity_mean'},
    {'label': 'Education Years',          'value': 'eduyrs_mean'},
    {'label': 'Safety After Dark',        'value': 'safety_mean'},
    {'label': 'Left-Right Scale',         'value': 'lrscale_mean'},
    {'label': 'Mean Age',                 'value': 'age_mean'},
    {'label': 'Urbanisation (%)',         'value': 'urban_pct'},
    {'label': 'Migration Background (%)', 'value': 'diversity_pct'},
    {'label': '─── External Macro Indicators ───', 'value': '_s2', 'disabled': True},
    {'label': 'Liberal Democracy',        'value': 'v2x_libdem'},
    {'label': 'Gini Index',               'value': 'wb_gini'},
    {'label': 'Unemployment (%)',         'value': 'wb_unemployment'},
    {'label': 'GDP per Capita (PPP)',      'value': 'wb_gdp_per_capita_ppp'},
    {'label': '─── Government Expenditure (COFOG) ───', 'value': '_s3', 'disabled': True},
    {'label': 'Gov. Health Exp.',         'value': 'gov_exp_health'},
    {'label': 'Gov. Education Exp.',      'value': 'gov_exp_education'},
    {'label': 'Gov. Social Exp.',         'value': 'gov_exp_social'},
    {'label': 'Gov. Defence Exp.',            'value': 'gov_exp_defence'},
    {'label': 'Gov. Economic Exp.',           'value': 'gov_exp_economic'},
    {'label': 'Gov. Public Services Exp.',    'value': 'gov_exp_public_services'},
    {'label': 'Gov. Culture & Recreation Exp.', 'value': 'gov_exp_culture'},
]

_SCATTER_Y_OPTS = [
    {'label': 'All 4 Dimensions (2×2)',  'value': 'all'},
    {'label': 'Openness to Change',      'value': 'dim_openness'},
    {'label': 'Self-Transcendence',      'value': 'dim_transcendence'},
    {'label': 'Conservation',            'value': 'dim_conservation'},
    {'label': 'Self-Enhancement',        'value': 'dim_enhancement'},
]

_ROUND_OPTS = [{'label': 'All rounds (country means)', 'value': 'all'}] + [
    {'label': f'ESS {dp.YEAR_TO_ROUND[y]} ({y})', 'value': y}
    for y in dp.ALL_YEARS
]

tab_corr = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Pearson correlations between country-level predictors and '
                'Schwartz value dimensions. N varies per round (up to 39 countries). '
                'Regression line with 95 % CI band.'
            ),
            _ctrl_label('ESS Round'),
            dcc.Dropdown(
                id='tc-round',
                options=_ROUND_OPTS,
                value=2023,
                clearable=False,
                className='ctrl-dropdown',
            ),
            html.Div(style={'height': '14px'}),
            _ctrl_label('X-Axis (Predictor)'),
            dcc.Dropdown(
                id='tc-x-var',
                options=_SCATTER_X_OPTS,
                value='trust_mean',
                clearable=False,
                className='ctrl-dropdown',
                optionHeight=32,
            ),
            html.Div(style={'height': '14px'}),
            _ctrl_label('Y-Axis (Schwartz Dimension)'),
            dcc.Dropdown(
                id='tc-y-var',
                options=_SCATTER_Y_OPTS,
                value='all',
                clearable=False,
                className='ctrl-dropdown',
            ),
            html.Div(style={'height': '18px'}),
            # Variable description - filled dynamically by callback
            html.Div(id='tc-x-desc'),
            html.Div(style={'height': '14px'}),
            # Significance legend - social-science standard (stars only)
            html.Div([
                html.P('Significance levels',
                       style={'font-size': '11px', 'font-weight': '700',
                              'color': '#1a2840', 'margin': '0 0 6px'}),
                html.Table([
                    html.Tr([html.Td('***', style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': '#1a2840'}),
                             html.Td('p < .001', style={'font-size': '11px',
                                                        'color': '#3a4a60'})]),
                    html.Tr([html.Td('**',  style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': '#1a2840'}),
                             html.Td('p < .01',  style={'font-size': '11px',
                                                        'color': '#3a4a60'})]),
                    html.Tr([html.Td('*',   style={'font-family': 'monospace',
                                                   'font-weight': '700',
                                                   'padding-right': '8px',
                                                   'color': '#1a2840'}),
                             html.Td('p < .05',  style={'font-size': '11px',
                                                        'color': '#3a4a60'})]),
                ], style={'border-spacing': '0', 'margin': '0'}),
            ], style={
                'padding': '10px 12px',
                'background-color': '#edf0f7',
                'border-radius': '6px',
                'border-left': '3px solid #1a5fb4',
            }),
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
                 'from the survey), external macro indicators (V-Dem Liberal Democracy '
                 'Index, World Bank GDP, Gini, unemployment), and Eurostat COFOG '
                 'government expenditure shares. Source details appear below the '
                 'predictor dropdown.'),
                ('Statistical approach',
                 'Pearson r measures the linear association between predictor and '
                 'Schwartz dimension. The OLS regression line and 95 % parametric '
                 'confidence band are computed from the visible data points. N is '
                 'shown in each panel annotation and varies by round, since not all '
                 '39 countries participated in every ESS round.'),
            ]),
        ], className='sidebar'),

        html.Div([
            dcc.Graph(id='tc-scatter', config={'displayModeBar': False}),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab 2 - Value Space ───────────────────────────────────────────────────────

tab2 = html.Div([
    html.Div([

        html.Div([
            _subtitle(
                'Countries placed by value profile similarity using PCA. '
                'Radar glyphs show each country\'s value priorities. '
                'Clusters group countries with similar profiles.'
            ),
            _ctrl_label('ESS Round'),
            dcc.Slider(
                id='t2vs-year',
                min=min(ALL_YEARS), max=max(ALL_YEARS), step=None,
                marks=_all_year_marks(),
                value=DEFAULT_YEAR, included=False,
                className='tab1-slider', vertical=True, verticalHeight=260,
            ),
            html.Div(style={'height': '18px'}),
            _ctrl_label('Number of Clusters'),
            dcc.Slider(
                id='t2vs-clusters',
                min=2, max=6, step=1, value=3,
                marks={i: str(i) for i in range(2, 7)},
                included=False,
            ),
            html.Div(style={'height': '16px'}),
            html.Div(id='t2vs-cluster-summary'),
            _interaction_box([
                'Hover over a country point for its profile details',
                'Adjust the cluster slider to change group count',
                'Drag the year slider to explore change over time',
            ]),
            _method_panel('t2-method-btn', 't2-method-content', [
                ('Principal Component Analysis',
                 'Each country\'s 10 Schwartz Δ-scores are projected onto 2 principal '
                 'components that capture the most variance in value profiles. Countries '
                 'close together in the space have similar overall profiles; countries '
                 'far apart differ substantially. Variance explained by each axis is '
                 'shown in the axis label.'),
                ('Axis orientation',
                 'Axes are labeled by the Schwartz dimension contrast that loads most '
                 'strongly on each component - typically Conservation vs. Openness to '
                 'Change (PC1) and Self-Enhancement vs. Self-Transcendence (PC2), '
                 'reflecting the two main axes of the theoretical value circumplex.'),
                ('K-Means clustering',
                 'Clusters are computed in the original 10-dimensional value space, not '
                 'in the PCA projection. Coloured regions show cluster membership. '
                 'Radar glyphs placed at each country\'s PCA coordinates show its actual '
                 'value profile, so both position and glyph shape carry information.'),
            ]),
        ], className='sidebar'),

        html.Div([
            dcc.Graph(id='t2vs-graph', config={'displayModeBar': False}),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── Tab 3 - Parallel Coordinates (individual-level IQR bands) ────────────────

def _dim_legend_chips():
    return [
        html.Div([
            html.Span('■', style={'color': c, 'font-size': '14px',
                                  'margin-right': '6px', 'flex-shrink': '0'}),
            html.Span(d, style={'color': '#1a2840', 'font-size': '12px'}),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '5px'})
        for d, c in dp.DIM_COLORS.items()
    ]


def _axis_entry(label, body):
    return html.Div([
        html.B(label + ' - '),
        html.Span(body, style={'color': '#2a3a50'}),
    ], style={'margin-bottom': '7px', 'font-size': '12.5px', 'line-height': '1.55'})


_DIM_OPTS = [{'label': 'All Dimensions', 'value': 'all'}] + [
    {'label': d, 'value': d} for d in dp.DIMS
]

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
            dcc.Dropdown(
                id='t3-dim',
                options=_DIM_OPTS,
                value='all',
                clearable=False,
                className='ctrl-dropdown',
            ),
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
            dcc.Graph(id='t3-parallel', config={'displayModeBar': False}),
            html.Div([
                html.P('Axis guide', style={
                    'font-size': '11px', 'font-weight': '700',
                    'text-transform': 'uppercase', 'letter-spacing': '0.6px',
                    'color': '#7a90b0', 'margin': '0 0 10px',
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
                        'ESS variable lrscale. Scale 0-10: 0 = far left, 10 = far right. '
                        'Self-placement on the political spectrum.'),
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
                'margin-top': '16px',
                'padding': '12px 16px',
                'background-color': '#edf0f7',
                'border-radius': '6px',
                'border-left': '3px solid #1a5fb4',
            }),
        ], className='main-content'),

    ], className='tab-with-sidebar'),
], className='tab-content')


# ── App shell ─────────────────────────────────────────────────────────────────

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
        html.P(
            'by Christopher Vantis',
            style={
                'font-style': 'italic',
                'font-size': '12px',
                'color': '#7a90b0',
                'margin': '4px 0 0',
            },
        ),
    ], className='header'),

    dcc.Tabs(
        id='main-tabs',
        value='tab-0',
        className='main-tabs',
        children=[
            dcc.Tab(label='About',               value='tab-0',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Country Profile',     value='tab-1',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Correlations',        value='tab-corr',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Value Space',         value='tab-2',
                    className='tab', selected_className='tab--selected'),
            dcc.Tab(label='Parallel Coordinates', value='tab-3',
                    className='tab', selected_className='tab--selected'),
        ],
    ),

    html.Div(id='tab-content', className='outer-tab-content'),
], className='app-wrapper')


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    return {
        'tab-0': landing, 'tab-1': tab1, 'tab-corr': tab_corr,
        'tab-2': tab2,    'tab-3': tab3,
    }[tab]


# Tab 1 - Country Profile
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
    density = round(pop_m * 1_000_000 / area_km2)
    rounds_avail = sorted(DF[DF['cntry'] == country]['year'].unique())
    rounds_str   = f'{dp.YEAR_TO_ROUND[rounds_avail[0]]}-{dp.YEAR_TO_ROUND[rounds_avail[-1]]}' \
                   if len(rounds_avail) > 1 else str(dp.YEAR_TO_ROUND[rounds_avail[0]])

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
        ], style={
            'flex': '1',
            'min-width': '80px',
            'padding': '0 16px 0 0',
        })

    # ── basic facts card ──────────────────────────────────────────────────────
    facts_card = html.Div([
        html.Div([
            _stat('Capital',     capital),
            _stat('Population',  f'{pop_m:.1f} M'),
            _stat('Density',     f'{density:,} / km²'),
            _stat('System',      system),
            _stat('EU status',   eu),
            _stat('ESS rounds',  f'R{rounds_str}  ({len(rounds_avail)} of 11)'),
        ], style={'display': 'flex', 'flex-wrap': 'wrap', 'gap': '12px 0'}),
    ], style={
        'margin-top': '14px',
        'padding': '14px 18px',
        'background-color': '#f7f9fc',
        'border-radius': '8px',
        'border-top': '3px solid #c0cce0',
    })

    # ── structural indicator block ────────────────────────────────────────────
    ind_row = DF_IND.loc[country] if country in DF_IND.index else None
    sents   = INDICATOR_SENTENCES.get(country, {})

    def _ind_item(col: str) -> html.Div:
        meta  = dp.INDICATOR_META[col]
        label = meta['label']
        unit  = meta['unit']
        src   = meta['source']
        sentence = sents.get(col, '')

        if ind_row is not None:
            import pandas as _pd
            v    = ind_row.get(col)
            yr_v = ind_row.get(col + '_year')
            yr   = int(yr_v) if yr_v and not _pd.isna(yr_v) else None
        else:
            v, yr = None, None

        na = v is None or (hasattr(v, '__float__') and __import__('math').isnan(float(v)))

        val_str = 'n/a' if na else (
            f'{v:.3f}' if col == 'vdem_ldi' else
            f'{v:.0f}' if col == 'estat_gdp_pps' else
            f'{v:.1f}'
        )
        yr_str  = f' ({yr})' if yr and not na else ''

        return html.Div([
            # Label + value row
            html.Div([
                html.Span(label, style={
                    'font-size': '11px', 'font-weight': '600',
                    'color': '#3a4a60', 'flex': '1',
                }),
                html.Span(
                    f'{val_str} {unit}{yr_str}',
                    title=src,
                    style={
                        'font-size': '11px', 'font-weight': '700',
                        'color': '#0d1b2a' if not na else '#9aa8b8',
                        'text-align': 'right', 'white-space': 'nowrap',
                        'cursor': 'help',
                    },
                ),
            ], style={'display': 'flex', 'align-items': 'baseline',
                      'gap': '8px', 'margin-bottom': '2px'}),
            # Contextual sentence
            html.Div(sentence, style={
                'font-size': '10.5px', 'color': '#7a90b0',
                'line-height': '1.4', 'font-style': 'italic',
                'margin-bottom': '8px',
            }),
        ])

    ind_items = [_ind_item(col) for col in dp.INDICATOR_META]
    ind_block = html.Div([
        html.P('Structural Indicators', style={
            'font-size': '10px', 'font-weight': '700', 'color': '#1a2840',
            'text-transform': 'uppercase', 'letter-spacing': '0.5px',
            'margin': '0 0 10px',
        }),
        *ind_items,
        html.P('Hover over a value for data source. See About for coverage notes.',
               style={'font-size': '9.5px', 'color': '#b0bcc8',
                      'margin': '4px 0 0', 'font-style': 'italic'}),
    ], style={
        'margin-top': '14px',
        'padding': '14px 18px',
        'background-color': '#f7f9fc',
        'border-radius': '8px',
        'border-top': '3px solid #c0cce0',
    })

    return html.Div([facts_card, ind_block])


# Tab Corr - Correlations
@app.callback(
    Output('tc-scatter', 'figure'),
    Output('tc-x-desc',  'children'),
    Input('tc-round', 'value'),
    Input('tc-x-var',   'value'),
    Input('tc-y-var',   'value'),
)
def update_corr(year, x_col, y_col):
    detail = dp.SCATTER_X_DETAIL.get(x_col, {})
    desc_html = html.Div([
        html.Div(detail.get('source', ''), style={
            'font-size': '10.5px', 'font-weight': '700',
            'color': '#1a5fb4', 'margin-bottom': '5px',
        }),
        *([html.Div([
            html.Span('Variable: ', style={'font-weight': '600',
                                           'color': '#1a2840', 'font-size': '10.5px'}),
            html.Span(detail['variable'], style={'color': '#3a4a60', 'font-size': '10.5px'}),
        ], style={'margin-bottom': '3px', 'line-height': '1.45'})] if 'variable' in detail else []),
        *([html.Div([
            html.Span('Scale: ', style={'font-weight': '600',
                                        'color': '#1a2840', 'font-size': '10.5px'}),
            html.Span(detail['scale'], style={'color': '#3a4a60', 'font-size': '10.5px'}),
        ], style={'margin-bottom': '3px', 'line-height': '1.45'})] if 'scale' in detail else []),
        *([html.Div([
            html.Span('Aggregation: ', style={'font-weight': '600',
                                               'color': '#1a2840', 'font-size': '10.5px'}),
            html.Span(detail['aggregation'], style={'color': '#3a4a60', 'font-size': '10.5px'}),
        ], style={'line-height': '1.45'})] if 'aggregation' in detail else []),
    ], style={
        'padding': '8px 10px',
        'background-color': '#f7f9fc',
        'border-radius': '6px',
        'border-left': '3px solid #c0cce0',
    })

    if y_col == 'all':
        fig = make_scatter_all(DF_SCATTER, x_col, year=year)
    else:
        fig = make_scatter_single(DF_SCATTER, x_col, y_col, year=year)
    return fig, desc_html


# Tab 2 - Value Space
@app.callback(
    Output('t2vs-graph', 'figure'),
    Output('t2vs-cluster-summary', 'children'),
    Input('t2vs-year', 'value'),
    Input('t2vs-clusters', 'value'),
)
def update_value_space(year, n_clusters):
    result, explained, pc1_label, pc2_label = dp.compute_pca_clustering(
        DF, year, n_clusters
    )
    fig     = make_value_space_figure(result, explained, pc1_label, pc2_label,
                                      year, n_clusters)
    summary = _make_cluster_summary(result, n_clusters)
    return fig, summary


# Tab 3 - Parallel Coordinates (IQR band profile)
@app.callback(
    Output('t3-parallel', 'figure'),
    Output('t3-title', 'children'),
    Input('t3-dim', 'value'),
)
def update_t3(highlight_dim):
    label = highlight_dim if highlight_dim != 'all' else 'All Dimensions'
    title = f'Parallel Coordinates  ·  Highlight: {label}  ·  All ESS Rounds'
    return make_parallel_micro(DF_MICRO, highlight_dim), title


# ── Methodology panel toggles ─────────────────────────────────────────────────

def _toggle(n):
    open_ = bool(n and n % 2 == 1)
    return _METHOD_OPEN if open_ else {'display': 'none'}, \
           '▲ Info' if open_ else 'Info'


@app.callback(
    Output('t1-method-content', 'style'),
    Output('t1-method-btn', 'children'),
    Input('t1-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t1_method(n):
    return _toggle(n)


@app.callback(
    Output('tc-method-content', 'style'),
    Output('tc-method-btn', 'children'),
    Input('tc-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_tc_method(n):
    return _toggle(n)


@app.callback(
    Output('t2-method-content', 'style'),
    Output('t2-method-btn', 'children'),
    Input('t2-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t2_method(n):
    return _toggle(n)


@app.callback(
    Output('t3-method-content', 'style'),
    Output('t3-method-btn', 'children'),
    Input('t3-method-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_t3_method(n):
    return _toggle(n)


server = app.server  # expose Flask server for gunicorn

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('RENDER') is None  # debug off on Render
    app.run(host='0.0.0.0', port=port, debug=debug)
