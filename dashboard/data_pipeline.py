from pathlib import Path
import glob
import re
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import numpy as np

_THIS_DIR = Path(__file__).parent
_DATA_DIR  = _THIS_DIR.parent / "data"
ESS_DIR    = _DATA_DIR / "raw" / "ess"
MAKRO_DIR  = _DATA_DIR / "raw" / "makro"

DATA_PATH   = ESS_DIR / "ess_schwartz_aggregated.csv"
VDEM_PATH   = MAKRO_DIR / "V-Dem-CY-FullOthers-v15_csv" / "V-Dem-CY-Full+Others-v15.csv"
GINI_PATH   = MAKRO_DIR / "gini_index_unvollständig.xlsx"
UNEMP_PATH  = MAKRO_DIR / "unemployment.xlsx"

COUNTRIES = {
    'AL': 'Albania',        'AT': 'Austria',        'BE': 'Belgium',
    'BG': 'Bulgaria',       'CH': 'Switzerland',    'CY': 'Cyprus',
    'CZ': 'Czechia',        'DE': 'Germany',        'DK': 'Denmark',
    'EE': 'Estonia',        'ES': 'Spain',          'FI': 'Finland',
    'FR': 'France',         'GB': 'United Kingdom', 'GR': 'Greece',
    'HR': 'Croatia',        'HU': 'Hungary',        'IE': 'Ireland',
    'IL': 'Israel',         'IS': 'Iceland',        'IT': 'Italy',
    'LT': 'Lithuania',      'LU': 'Luxembourg',     'LV': 'Latvia',
    'ME': 'Montenegro',     'MK': 'North Macedonia','NL': 'Netherlands',
    'NO': 'Norway',         'PL': 'Poland',         'PT': 'Portugal',
    'RO': 'Romania',        'RS': 'Serbia',         'RU': 'Russia',
    'SE': 'Sweden',         'SI': 'Slovenia',       'SK': 'Slovakia',
    'TR': 'Türkiye',        'UA': 'Ukraine',        'XK': 'Kosovo',
}

COUNTRY_FLAGS = {
    'AL': '🇦🇱', 'AT': '🇦🇹', 'BE': '🇧🇪', 'BG': '🇧🇬',
    'CH': '🇨🇭', 'CY': '🇨🇾', 'CZ': '🇨🇿', 'DE': '🇩🇪',
    'DK': '🇩🇰', 'EE': '🇪🇪', 'ES': '🇪🇸', 'FI': '🇫🇮',
    'FR': '🇫🇷', 'GB': '🇬🇧', 'GR': '🇬🇷', 'HR': '🇭🇷',
    'HU': '🇭🇺', 'IE': '🇮🇪', 'IL': '🇮🇱', 'IS': '🇮🇸',
    'IT': '🇮🇹', 'LT': '🇱🇹', 'LU': '🇱🇺', 'LV': '🇱🇻',
    'ME': '🇲🇪', 'MK': '🇲🇰', 'NL': '🇳🇱', 'NO': '🇳🇴',
    'PL': '🇵🇱', 'PT': '🇵🇹', 'RO': '🇷🇴', 'RS': '🇷🇸',
    'RU': '🇷🇺', 'SE': '🇸🇪', 'SI': '🇸🇮', 'SK': '🇸🇰',
    'TR': '🇹🇷', 'UA': '🇺🇦', 'XK': '🇽🇰',
}

# V-Dem country names → ISO-2
_VDEM_NAME_TO_ISO2 = {v: k for k, v in COUNTRIES.items()}

# Unemployment xlsx ISO-3 → ISO-2
_UNEMP_ISO3_TO_ISO2 = {
    'ALB': 'AL', 'AUT': 'AT', 'BEL': 'BE', 'BGR': 'BG',
    'CHE': 'CH', 'CYP': 'CY', 'CZE': 'CZ', 'DEU': 'DE',
    'DNK': 'DK', 'EST': 'EE', 'ESP': 'ES', 'FIN': 'FI',
    'FRA': 'FR', 'GBR': 'GB', 'GRC': 'GR', 'HRV': 'HR',
    'HUN': 'HU', 'IRL': 'IE', 'ISR': 'IL', 'ISL': 'IS',
    'ITA': 'IT', 'LTU': 'LT', 'LUX': 'LU', 'LVA': 'LV',
    'MNE': 'ME', 'MKD': 'MK', 'NLD': 'NL', 'NOR': 'NO',
    'POL': 'PL', 'PRT': 'PT', 'ROU': 'RO', 'SRB': 'RS',
    'RUS': 'RU', 'SWE': 'SE', 'SVN': 'SI', 'SVK': 'SK',
    'TUR': 'TR', 'UKR': 'UA', 'XKX': 'XK',
}

# Gini xlsx country names → ISO-2
_GINI_NAME_TO_ISO2 = {
    'Albania': 'AL',        'Austria': 'AT',         'Belgium': 'BE',
    'Bulgaria': 'BG',       'Switzerland': 'CH',     'Cyprus': 'CY',
    'Czech Republic': 'CZ', 'Czechia': 'CZ',         'Germany': 'DE',
    'Denmark': 'DK',        'Estonia': 'EE',         'Spain': 'ES',
    'Finland': 'FI',        'France': 'FR',          'United Kingdom': 'GB',
    'Greece': 'GR',         'Croatia': 'HR',         'Hungary': 'HU',
    'Ireland': 'IE',        'Israel': 'IL',          'Iceland': 'IS',
    'Italy': 'IT',          'Lithuania': 'LT',       'Luxembourg': 'LU',
    'Latvia': 'LV',         'Montenegro': 'ME',      'North Macedonia': 'MK',
    'Netherlands': 'NL',    'Norway': 'NO',          'Poland': 'PL',
    'Portugal': 'PT',       'Romania': 'RO',         'Serbia': 'RS',
    'Russia': 'RU',         'Sweden': 'SE',          'Slovenia': 'SI',
    'Slovak Republic': 'SK','Slovakia': 'SK',         'Turkey': 'TR',         'Türkiye': 'TR',
    'Ukraine': 'UA',        'Kosovo': 'XK',
}

YEAR_TO_ROUND = {
    2002: 1, 2004: 2, 2006: 3, 2008: 4, 2010: 5,
    2012: 6, 2014: 7, 2016: 8, 2018: 9, 2020: 10, 2023: 11,
}
ROUND_TO_YEAR = {v: k for k, v in YEAR_TO_ROUND.items()}
ALL_YEARS  = sorted(YEAR_TO_ROUND.keys())
ALL_ROUNDS = sorted(ROUND_TO_YEAR.keys())

VALUE_KEYS = ['SD', 'UN', 'BE', 'TR', 'CO', 'SE', 'PO', 'AC', 'HE', 'ST']
VALUE_LABELS = {
    'SD': 'Self-Direction', 'UN': 'Universalism', 'BE': 'Benevolence',
    'TR': 'Tradition',      'CO': 'Conformity',   'SE': 'Security',
    'PO': 'Power',          'AC': 'Achievement',  'HE': 'Hedonism',
    'ST': 'Stimulation',
}

# Updated GNOME-palette colors (brighter, per task specification)
DIM_COLORS = {
    'Openness to Change': '#3584e4',
    'Self-Transcendence': '#9141ac',
    'Conservation':       '#2ec27e',
    'Self-Enhancement':   '#e01b24',
}
DIMS = list(DIM_COLORS.keys())

DIM_COLS = {
    'Openness to Change': 'dim_openness',
    'Self-Transcendence': 'dim_transcendence',
    'Conservation':       'dim_conservation',
    'Self-Enhancement':   'dim_enhancement',
}

VALUE_TO_DIM = {
    'SD': 'Openness to Change', 'HE': 'Openness to Change', 'ST': 'Openness to Change',
    'UN': 'Self-Transcendence', 'BE': 'Self-Transcendence',
    'TR': 'Conservation',       'CO': 'Conservation',       'SE': 'Conservation',
    'PO': 'Self-Enhancement',   'AC': 'Self-Enhancement',
}

# Macro columns for parallel coordinates (in order)
MACRO_COLS = [
    ('dim_openness',      'Openness\nto Change'),
    ('dim_transcendence', 'Self-\nTranscendence'),
    ('dim_conservation',  'Conservation'),
    ('dim_enhancement',   'Self-\nEnhancement'),
    ('ldi',               'Liberal\nDemocracy'),
    ('gini',              'Gini Index\n(×100)'),
    ('unemployment_rate', 'Unemployment\n(%)'),
    ('migration_share',   'Migration\nBackground (%)'),
    ('mean_eduyrs',       'Years\nof Education'),
]

_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
    '#bd9e39', '#d6616b', '#ce6dbd', '#6b6ecf', '#b5cf6b',
    '#e6550d', '#31a354', '#756bb1', '#636363', '#969696',
    '#6baed6', '#74c476', '#fd8d3c', '#9ecae1', '#a1d99b',
]
COUNTRY_COLORS = {c: _PALETTE[i] for i, c in enumerate(sorted(COUNTRIES.keys()))}

BG_COLOR    = '#f4f6fb'
RADAR_BG    = '#e8edf5'
DELTA_RANGE = [-1.4, 1.75]

# ── Country profile info ───────────────────────────────────────────────────────
# (capital, population_millions, area_km2, political_system, eu_status)
# Population and area: approximate 2023 figures.
# EU status: year of accession, 'EEA', or 'No'.
COUNTRY_INFO = {
    'AL': ('Tirana',        2.8,    28748,   'Parliamentary Republic',              'Candidate'),
    'AT': ('Vienna',        9.1,    83871,   'Federal Parliamentary Republic',       'EU 1995'),
    'BE': ('Brussels',     11.6,    30528,   'Federal Constitutional Monarchy',      'EU 1952'),
    'BG': ('Sofia',         6.5,   110879,   'Parliamentary Republic',              'EU 2007'),
    'CH': ('Bern',          8.7,    41285,   'Federal Council / Direct Democracy',  'EEA'),
    'CY': ('Nicosia',       1.2,     9251,   'Presidential Republic',               'EU 2004'),
    'CZ': ('Prague',       10.9,    78866,   'Parliamentary Republic',              'EU 2004'),
    'DE': ('Berlin',       84.4,   357114,   'Federal Parliamentary Republic',       'EU 1952'),
    'DK': ('Copenhagen',    5.9,    42924,   'Constitutional Monarchy',             'EU 1973'),
    'EE': ('Tallinn',       1.4,    45228,   'Parliamentary Republic',              'EU 2004'),
    'ES': ('Madrid',       47.4,   505990,   'Constitutional Monarchy',             'EU 1986'),
    'FI': ('Helsinki',      5.5,   338145,   'Parliamentary Republic',              'EU 1995'),
    'FR': ('Paris',        68.0,   551695,   'Semi-Presidential Republic',          'EU 1952'),
    'GB': ('London',       67.6,   243610,   'Constitutional Monarchy',             'Left EU 2020'),
    'GR': ('Athens',       10.7,   131957,   'Parliamentary Republic',              'EU 1981'),
    'HR': ('Zagreb',        3.9,    56594,   'Parliamentary Republic',              'EU 2013'),
    'HU': ('Budapest',      9.7,    93028,   'Parliamentary Republic',              'EU 2004'),
    'IE': ('Dublin',        5.1,    70273,   'Parliamentary Republic',              'EU 1973'),
    'IL': ('Jerusalem',     9.5,    20770,   'Parliamentary Republic',              'No'),
    'IS': ('Reykjavik',     0.4,   103000,   'Parliamentary Republic',              'EEA'),
    'IT': ('Rome',         59.1,   301340,   'Parliamentary Republic',              'EU 1952'),
    'LT': ('Vilnius',       2.8,    65300,   'Parliamentary Republic',              'EU 2004'),
    'LU': ('Luxembourg',    0.7,     2586,   'Constitutional Monarchy (Grand Duchy)', 'EU 1952'),
    'LV': ('Riga',          1.8,    64589,   'Parliamentary Republic',              'EU 2004'),
    'ME': ('Podgorica',     0.6,    13812,   'Parliamentary Republic',              'Candidate'),
    'MK': ('Skopje',        2.1,    25713,   'Parliamentary Republic',              'Candidate'),
    'NL': ('Amsterdam',    17.8,    41543,   'Constitutional Monarchy',             'EU 1952'),
    'NO': ('Oslo',          5.5,   385207,   'Constitutional Monarchy',             'EEA'),
    'PL': ('Warsaw',       38.0,   312696,   'Parliamentary Republic',              'EU 2004'),
    'PT': ('Lisbon',       10.3,    92212,   'Semi-Presidential Republic',          'EU 1986'),
    'RO': ('Bucharest',    19.0,   238397,   'Semi-Presidential Republic',          'EU 2007'),
    'RS': ('Belgrade',      6.8,    77474,   'Parliamentary Republic',              'Candidate'),
    'RU': ('Moscow',      146.0, 17098242,   'Federal Semi-Presidential Republic',  'No'),
    'SE': ('Stockholm',    10.5,   450295,   'Constitutional Monarchy',             'EU 1995'),
    'SI': ('Ljubljana',     2.1,    20273,   'Parliamentary Republic',              'EU 2004'),
    'SK': ('Bratislava',    5.5,    49035,   'Parliamentary Republic',              'EU 2004'),
    'TR': ('Ankara',       85.3,   783356,   'Presidential Republic',               'Candidate (frozen)'),
    'UA': ('Kyiv',         43.5,   603550,   'Semi-Presidential Republic',          'Candidate'),
    'XK': ('Pristina',      1.8,    10887,   'Parliamentary Republic',              'No'),
}

# ── Scatter / Correlation analysis ────────────────────────────────────────────

SCATTER_PATH = (
    _DATA_DIR / 'merged_datasets' / 'macro_schwartz_analysis_data.csv'
)

# Real data patches for wb_gini - fetched 2026-04-28 from World Bank API and
# Eurostat EU-SILC to fill gaps in the base CSV.
# (cntry, ess_year): gini_value, source_note
_GINI_PATCHES = {
    # ESS 2002: WB has no 2002 survey for these countries - use nearest year
    ('BE', 2002): (28.1, 'World Bank 2003'),
    ('ES', 2002): (31.8, 'World Bank 2003'),
    ('FI', 2002): (27.7, 'World Bank 2003'),
    ('NL', 2002): (29.8, 'World Bank 2004'),   # no 2002/2003 available
    ('NO', 2002): (27.6, 'World Bank 2003'),
    ('PT', 2002): (38.8, 'World Bank 2003'),
    # HU 2018-2023: WB discontinued after 2017 → Eurostat EU-SILC
    ('HU', 2018): (28.7, 'Eurostat EU-SILC 2018'),
    ('HU', 2020): (28.2, 'Eurostat EU-SILC 2020'),
    ('HU', 2023): (28.6, 'Eurostat EU-SILC 2023 (series break)'),
    # End-of-series: forward-carry last available WB value
    ('CH', 2023): (33.8, 'World Bank 2022'),
    ('DE', 2023): (33.7, 'World Bank 2022'),
    ('NL', 2023): (25.7, 'World Bank 2021'),
}

# (column, short label, hover description)
SCATTER_X_META = [
    ('trust_mean',            'Social Trust',            'ESS ppltrst - interpersonal trust (0-10)'),
    ('religiosity_mean',      'Religiosity',             'ESS rlgdgr - self-rated religiosity (0-10)'),
    ('eduyrs_mean',           'Education Years',         'ESS eduyrs - mean full-time education years'),
    ('safety_mean',           'Safety After Dark',       'ESS aesfdrk - 1=very safe, 4=very unsafe'),
    ('lrscale_mean',          'Left-Right Scale',        'ESS lrscale - 0=far left, 10=far right'),
    ('age_mean',              'Mean Age',                'ESS agea - mean respondent age (years)'),
    ('urban_pct',             'Urbanisation (%)',        'ESS domicil - share urban / suburban respondents'),
    ('diversity_pct',         'Migration Background (%)', 'ESS brncntr/facntr/mocntr - share born abroad or parent born abroad'),
    ('v2x_libdem',            'Liberal Democracy',       'V-Dem v15 v2x_libdem (0-1)'),
    ('wb_gini',               'Gini Index',              'World Bank GINI index (0-100)'),
    ('wb_unemployment',       'Unemployment (%)',        'World Bank unemployment rate (% of labour force)'),
    ('wb_gdp_per_capita_ppp', 'GDP per Capita (PPP)',    'World Bank GDP/cap, PPP, constant 2017 int\'l $'),
    ('gov_exp_health',           'Gov. Health Exp.',            'COFOG: health (% of total gov. spending)'),
    ('gov_exp_education',        'Gov. Education Exp.',         'COFOG: education (% of total gov. spending)'),
    ('gov_exp_social',           'Gov. Social Exp.',            'COFOG: social protection (% of total gov. spending)'),
    ('gov_exp_defence',          'Gov. Defence Exp.',           'COFOG: defence (% of total gov. spending)'),
    ('gov_exp_economic',         'Gov. Economic Exp.',          'COFOG: economic affairs (% of total gov. spending)'),
    ('gov_exp_public_services',  'Gov. Public Services Exp.',   'COFOG: general public services (% of total gov. spending)'),
    ('gov_exp_culture',          'Gov. Culture & Recreation Exp.', 'COFOG: recreation, culture and religion (% of total gov. spending)'),
]

# Rich display metadata for the sidebar (source, question wording, scale, aggregation)
SCATTER_X_DETAIL = {
    'trust_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'ppltrst - "Most people can be trusted, or you can\'t be too careful"',
        'scale':       '0 = can\'t be too careful · 10 = most people can be trusted',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'religiosity_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'rlgdgr - "Regardless of whether you belong to a particular religion, how religious are you?"',
        'scale':       '0 = not religious at all · 10 = very religious',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'eduyrs_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'eduyrs - Years of full-time education completed',
        'scale':       'Years (continuous); non-responses (77, 88, 99) excluded',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'safety_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'aesfdrk - "How safe do you feel walking alone in your local area after dark?"',
        'scale':       '1 = very safe · 4 = very unsafe (lower = safer)',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'lrscale_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'lrscale - "In politics people sometimes talk of \'left\' and \'right\'. Where would you place yourself?"',
        'scale':       '0 = left · 10 = right',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'age_mean': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'agea - Age of respondent (calculated)',
        'scale':       'Years (continuous)',
        'aggregation': 'Country mean, averaged across all available ESS rounds',
    },
    'urban_pct': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'domicil - "Which phrase on this card best describes the area where you live?"',
        'scale':       '% of respondents in "a big city" or "suburbs / outskirts of big city"',
        'aggregation': 'Country share, averaged across all available ESS rounds',
    },
    'diversity_pct': {
        'source':      'European Social Survey (ESS), Rounds 1-11 (2002-2023)',
        'variable':    'brncntr, facntr, mocntr - born abroad or at least one parent born abroad',
        'scale':       '% of respondents with migration background',
        'aggregation': 'Country share, averaged across all available ESS rounds',
    },
    'v2x_libdem': {
        'source':      'V-Dem Project, Country-Year Dataset v15 (Coppedge et al., 2024)',
        'variable':    'v2x_libdem - Liberal Democracy Index',
        'scale':       '0-1 (higher = more liberal-democratic); composite of electoral, liberal, and participatory components',
        'aggregation': 'Country mean over ESS reference years (2002-2023)',
    },
    'wb_gini': {
        'source':      'World Bank WDI (SI.POV.GINI) · Eurostat EU-SILC for HU 2018-2023',
        'variable':    'SI.POV.GINI - Gini index of equivalised disposable income',
        'scale':       '0-100 (higher = more unequal). 12 gaps filled with real data: '
                       'WB nearest survey year (2002 gaps) or Eurostat EU-SILC / WB forward-carry (HU, CH, DE, NL 2023).',
        'aggregation': 'Matched to ESS reference year; no imputation - all values from primary sources',
    },
    'wb_unemployment': {
        'source':      'World Bank World Development Indicators (WDI)',
        'variable':    'SL.UEM.TOTL.ZS - Unemployment, total (% of total labour force)',
        'scale':       '% of labour force (ILO modelled estimates)',
        'aggregation': 'Country mean over ESS reference years',
    },
    'wb_gdp_per_capita_ppp': {
        'source':      'World Bank World Development Indicators (WDI)',
        'variable':    'NY.GDP.PCAP.PP.KD - GDP per capita, PPP (constant 2017 international $)',
        'scale':       'Purchasing-power-parity adjusted, in thousands of 2017 USD',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_health': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF07 - Health (function 07 of total government expenditure)',
        'scale':       '% of total government expenditure',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_education': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF09 - Education (function 09 of total government expenditure)',
        'scale':       '% of total government expenditure',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_social': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF10 - Social protection (function 10 of total government expenditure)',
        'scale':       '% of total government expenditure',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_defence': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF02 - Defence (function 02 of total government expenditure)',
        'scale':       '% of total government expenditure',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_economic': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF04 - Economic affairs (function 04 of total government expenditure)',
        'scale':       '% of GDP (Eurostat COFOG, total general government expenditure)',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_public_services': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF01 - General public services (function 01 of total government expenditure)',
        'scale':       '% of GDP (Eurostat COFOG, total general government expenditure)',
        'aggregation': 'Country mean over ESS reference years',
    },
    'gov_exp_culture': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF08 - Recreation, culture and religion (function 08 of total government expenditure)',
        'scale':       '% of GDP (Eurostat COFOG, total general government expenditure)',
        'aggregation': 'Country mean over ESS reference years',
    },
}

# (column, display label, color)
SCATTER_Y_META = [
    ('dim_openness',      'Openness to Change',  DIM_COLORS['Openness to Change']),
    ('dim_transcendence', 'Self-Transcendence',  DIM_COLORS['Self-Transcendence']),
    ('dim_conservation',  'Conservation',         DIM_COLORS['Conservation']),
    ('dim_enhancement',   'Self-Enhancement',     DIM_COLORS['Self-Enhancement']),
]

# ── Individual-level parallel coordinates ──────────────────────────────────────

# Attitude variables for the individual-level parallel coordinates.
# All present in 11/11 ESS rounds; no round-level imputation needed.
MICRO_ATTRS = [
    'ppltrst', 'trstplt', 'trstlgl', 'stflife', 'stfeco',
    'stfdem',  'lrscale', 'imwbcnt', 'gincdif',
    'rlgdgr',  'aesfdrk',
]

# (column, axis label, [range_min, range_max])
# gincdif and aesfdrk are stored inverted (see load_micro_individual) so that
# higher always means "more positive" on the axis.
MICRO_ATTR_META = [
    ('ppltrst',       'Interpersonal\nTrust',       [0, 10]),
    ('trstplt',       'Trust in\nPoliticians',      [0, 10]),
    ('trstlgl',       'Trust:\nLegal System',       [0, 10]),
    ('stflife',       'Life\nSatisfaction',         [0, 10]),
    ('stfeco',        'Econ.\nSatisfaction',        [0, 10]),
    ('stfdem',        'Democracy\nSatisfaction',    [0, 10]),
    ('lrscale',       'Left-Right\nScale',          [0, 10]),
    ('imwbcnt',       'Immigration\nAttitude',      [0, 10]),
    ('redistr_supp',  'Redistribution\nSupport',    [1, 5]),
    ('rlgdgr',        'Religiosity',                [0, 10]),
    ('safety',        'Safety\nAfter Dark',         [1, 4]),
]

# PVQ items → higher-order dimension (consistent with load_data() mapping)
_PVQ_TO_DIM = {
    'ipcrtiv': 'oc', 'ipadvnt': 'oc', 'ipgdtim': 'oc',
    'iphlppl': 'st', 'ipeqopt': 'st', 'ipudrst': 'st',
    'iplylfr': 'co', 'ipmodst': 'co', 'ipbhprp': 'co', 'ipfrule': 'co',
    'ipshabt': 'se', 'ipsuces': 'se', 'iprspot': 'se', 'ipstrgv': 'se',
}


# ── ESS Schwartz aggregation from raw CSVs ────────────────────────────────────

_PVQ_ITEMS = [
    'ipcrtiv', 'ipadvnt', 'ipgdtim', 'iphlppl', 'ipeqopt',
    'ipudrst', 'iplylfr', 'ipmodst', 'ipbhprp', 'ipfrule',
    'ipshabt', 'ipsuces', 'iprspot', 'ipstrgv',
]
_MIN_RESPONDENTS = 30  # minimum country-round cell size to include


def _aggregate_ess_values() -> pd.DataFrame:
    """Aggregate PVQ-21 item means from raw ESS CSVs for all COUNTRIES."""
    records = []
    for r in range(1, 12):
        csvs = glob.glob(str(ESS_DIR / f'ESS{r}' / '*.csv'))
        if not csvs:
            continue
        year = ROUND_TO_YEAR[r]

        # Discover available columns (casing varies across rounds)
        header = pd.read_csv(csvs[0], nrows=0)
        header.columns = header.columns.str.lower()
        needed = ['cntry'] + _PVQ_ITEMS
        avail  = [c for c in needed if c in header.columns]
        missing_pvq = [c for c in _PVQ_ITEMS if c not in header.columns]

        raw = pd.read_csv(csvs[0], usecols=avail, low_memory=False)
        raw.columns = raw.columns.str.lower()
        for col in missing_pvq:
            raw[col] = np.nan

        # Scale 1-6; codes 7/8/9 = missing
        for col in _PVQ_ITEMS:
            raw[col] = pd.to_numeric(raw[col], errors='coerce')
            raw[col] = raw[col].where(raw[col] <= 6)

        for cntry, grp in raw.groupby('cntry'):
            if cntry not in COUNTRIES:
                continue
            row = {'cntry': cntry, 'year': year}
            for col in _PVQ_ITEMS:
                vals = grp[col].dropna()
                if len(vals) >= _MIN_RESPONDENTS:
                    row[f'{col}_mean']   = float(vals.mean())
                    row[f'{col}_median'] = float(vals.median())
                else:
                    row[f'{col}_mean']   = np.nan
                    row[f'{col}_median'] = np.nan
            records.append(row)

    return pd.DataFrame(records)


# ── XML helpers (shared by both xlsx files) ────────────────────────────────────

def _xlsx_rows(path: Path, sheet: str = 'xl/worksheets/sheet1.xml') -> list:
    """Parse an xlsx file and return all rows as lists of cell values (strings)."""
    with zipfile.ZipFile(path) as z:
        with z.open('xl/sharedStrings.xml') as f:
            ss_tree = ET.parse(f)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings = []
        for si in ss_tree.findall('.//ns:si', ns):
            t = ''.join((n.text or '') for n in si.findall('.//ns:t', ns))
            strings.append(t)

        with z.open(sheet) as f:
            ws_tree = ET.parse(f)

    rows = []
    for row in ws_tree.findall('.//ns:row', ns):
        row_data = []
        for cell in row.findall('ns:c', ns):
            v = cell.find('ns:v', ns)
            t = cell.get('t', '')
            if v is not None:
                row_data.append(strings[int(v.text)] if t == 's' else v.text)
            else:
                row_data.append('')
        rows.append(row_data)
    return rows


# ── Macro data loaders ─────────────────────────────────────────────────────────

def _load_vdem() -> pd.DataFrame:
    df = pd.read_csv(
        VDEM_PATH,
        usecols=['country_name', 'year', 'v2x_libdem'],
        low_memory=False,
    )
    df['cntry'] = df['country_name'].map(_VDEM_NAME_TO_ISO2)
    df = df.dropna(subset=['cntry'])
    df = df[df['year'].isin(ALL_YEARS)][['cntry', 'year', 'v2x_libdem']]
    return df.rename(columns={'v2x_libdem': 'ldi'})


def _load_gini() -> pd.DataFrame:
    rows = _xlsx_rows(GINI_PATH)
    # Row 5 (index 5) holds the year columns starting at col index 2
    year_row = rows[5]
    years = []
    for x in year_row[2:]:
        try:
            years.append(int(float(x)))
        except (ValueError, TypeError):
            years.append(None)

    records = []
    for row in rows[7:]:
        if not row or not row[0]:
            continue
        cntry = _GINI_NAME_TO_ISO2.get(row[0])
        if cntry is None:
            continue
        yr_vals = {}
        for i, yr in enumerate(years):
            if yr is None:
                continue
            raw = row[2 + i] if (2 + i) < len(row) else ''
            if raw:
                try:
                    yr_vals[yr] = float(raw) * 100  # convert 0-1 → 0-100
                except ValueError:
                    pass
        if not yr_vals:
            continue
        avail = sorted(yr_vals.keys())
        for ess_yr in ALL_YEARS:
            closest = min(avail, key=lambda y: abs(y - ess_yr))
            records.append({'cntry': cntry, 'year': ess_yr, 'gini': yr_vals[closest]})

    # Ireland absent from source xlsx - Eurostat EU-SILC.
    _IE_GINI = {
        2003: 31.1, 2004: 31.8, 2006: 32.4, 2007: 31.3, 2008: 30.7,
        2010: 31.4, 2012: 30.0, 2014: 31.1, 2016: 29.5, 2018: 28.7,
        2020: 27.8, 2022: 27.5, 2023: 26.9,
    }
    _avail_ie = sorted(_IE_GINI.keys())
    for ess_yr in ALL_YEARS:
        closest = min(_avail_ie, key=lambda y: abs(y - ess_yr))
        records.append({'cntry': 'IE', 'year': ess_yr, 'gini': _IE_GINI[closest]})

    # World Bank Development Indicators SI.POV.GINI (fetched 2025-04) for
    # countries absent from the OECD source file. EU/EEA values use Eurostat
    # EU-SILC as the underlying source; others use national household surveys.
    # Closest-year matching is applied to map available survey years to ESS rounds.
    _WB_GINI = {
        'AL': {2002: 31.7, 2005: 30.6, 2008: 30.0, 2012: 29.0, 2014: 34.6,
               2016: 33.7, 2018: 30.1, 2020: 29.4},
        'AT': {2000: 29.0, 2003: 29.5, 2004: 29.8, 2006: 29.6, 2008: 30.4,
               2010: 30.3, 2012: 30.5, 2014: 30.5, 2016: 30.8, 2018: 30.8,
               2020: 29.8, 2022: 30.9, 2023: 31.2},
        'BG': {2001: 32.7, 2003: 28.9, 2006: 35.7, 2008: 33.6, 2010: 35.7,
               2012: 36.0, 2014: 37.4, 2016: 40.6, 2018: 41.3, 2020: 40.5,
               2022: 38.2, 2023: 39.5},
        'CY': {2004: 30.1, 2006: 31.1, 2008: 31.7, 2010: 31.5, 2012: 34.3,
               2014: 35.6, 2016: 32.9, 2018: 32.7, 2020: 31.7, 2022: 31.5,
               2023: 31.8},
        'CZ': {2002: 26.6, 2004: 27.5, 2006: 26.7, 2008: 26.3, 2010: 26.6,
               2012: 26.1, 2014: 25.9, 2016: 25.4, 2018: 25.0, 2020: 26.2,
               2022: 25.9, 2023: 25.7},
        'EE': {2002: 35.8, 2004: 33.6, 2006: 33.7, 2008: 31.9, 2010: 32.0,
               2012: 32.9, 2014: 34.6, 2016: 31.2, 2018: 30.3, 2020: 30.7,
               2022: 32.3, 2023: 30.7},
        'GR': {2002: 35.5, 2004: 33.6, 2006: 35.1, 2008: 33.6, 2010: 34.1,
               2012: 36.3, 2014: 35.8, 2016: 35.0, 2018: 32.9, 2020: 33.6,
               2022: 33.4, 2023: 33.4},
        'HR': {2004: 29.7, 2008: 33.7, 2010: 32.4, 2012: 32.5, 2014: 32.1,
               2016: 30.9, 2018: 29.7, 2020: 29.5, 2022: 30.0, 2023: 30.1},
        'IS': {2003: 26.8, 2004: 28.0, 2006: 30.2, 2008: 31.8, 2010: 26.2,
               2012: 26.8, 2014: 27.8, 2016: 27.2, 2018: 26.6, 2019: 26.8},
        'IL': {2002: 39.6, 2004: 41.5, 2006: 41.6, 2008: 41.6, 2010: 42.6,
               2012: 41.3, 2014: 39.8, 2016: 39.0, 2018: 38.6, 2020: 37.8,
               2022: 38.3},
        'IT': {2002: 34.7, 2004: 34.3, 2006: 33.7, 2008: 33.8, 2010: 34.7,
               2012: 35.2, 2014: 34.7, 2016: 35.2, 2018: 35.2, 2020: 35.2,
               2022: 33.7, 2023: 34.3},
        'LT': {2002: 31.9, 2004: 37.0, 2006: 34.4, 2008: 35.7, 2010: 33.6,
               2012: 35.1, 2014: 37.7, 2016: 38.4, 2018: 35.7, 2020: 36.0,
               2022: 36.6, 2023: 36.0},
        'LU': {2002: 31.1, 2004: 30.2, 2006: 30.9, 2008: 32.6, 2010: 30.5,
               2012: 34.3, 2014: 31.2, 2016: 31.7, 2018: 35.4, 2020: 33.4,
               2022: 34.1, 2023: 33.6},
        'LV': {2002: 35.1, 2004: 36.4, 2006: 35.6, 2008: 37.2, 2010: 35.0,
               2012: 35.2, 2014: 35.1, 2016: 34.3, 2018: 35.1, 2020: 35.7,
               2022: 33.7, 2023: 34.0},
        'ME': {2005: 30.2, 2006: 30.0, 2008: 30.5, 2010: 28.9, 2012: 41.2,
               2014: 38.8, 2016: 38.5, 2018: 36.8, 2020: 35.4, 2021: 34.3},
        'MK': {2002: 38.5, 2004: 38.4, 2006: 42.6, 2008: 46.1, 2010: 40.1,
               2012: 38.1, 2014: 35.2, 2016: 34.5, 2018: 33.0, 2019: 33.5},
        'RO': {2002: 30.2, 2004: 30.0, 2006: 39.6, 2008: 36.4, 2010: 35.5,
               2012: 36.5, 2014: 36.0, 2016: 34.4, 2018: 35.8, 2020: 34.6,
               2022: 32.3, 2023: 29.8},
        'RS': {2002: 32.7, 2004: 35.5, 2006: 29.7, 2008: 27.6, 2010: 29.0,
               2012: 39.9, 2014: 40.4, 2016: 38.8, 2018: 35.0, 2020: 35.0,
               2022: 32.8, 2023: 32.8},
        'RU': {2002: 37.3, 2004: 40.3, 2006: 41.0, 2008: 41.6, 2010: 39.5,
               2012: 40.7, 2014: 36.9, 2016: 36.7, 2018: 35.3, 2020: 33.7,
               2022: 33.9, 2023: 33.0},
        'SK': {2004: 27.1, 2006: 25.8, 2008: 26.0, 2010: 27.3, 2012: 26.1,
               2014: 26.1, 2016: 25.2, 2018: 25.0, 2020: 24.2, 2022: 24.1,
               2023: 23.8},
        'TR': {2002: 41.4, 2004: 41.3, 2006: 39.6, 2008: 39.0, 2010: 38.8,
               2012: 40.2, 2014: 41.2, 2016: 41.9, 2018: 42.4, 2020: 43.0,
               2022: 44.5, 2023: 43.7},
        'UA': {2002: 29.0, 2004: 28.9, 2006: 29.8, 2008: 26.6, 2010: 24.8,
               2012: 24.7, 2014: 24.0, 2016: 25.0, 2018: 26.1, 2020: 25.6},
        'XK': {2003: 29.0, 2005: 31.2, 2006: 30.3, 2009: 31.8, 2010: 33.3,
               2011: 27.8, 2012: 29.0, 2013: 26.3, 2014: 27.3, 2015: 26.5,
               2016: 26.7},
    }
    for cntry, yr_vals in _WB_GINI.items():
        avail = sorted(yr_vals.keys())
        for ess_yr in ALL_YEARS:
            closest = min(avail, key=lambda y: abs(y - ess_yr))
            records.append({'cntry': cntry, 'year': ess_yr,
                            'gini': yr_vals[closest]})

    return pd.DataFrame(records)


def _load_unemployment() -> pd.DataFrame:
    rows = _xlsx_rows(UNEMP_PATH)
    # Row 5 has the year columns
    year_row = rows[5]
    years = []
    for x in year_row[2:]:
        m = re.search(r'\((\d{4})\)', x) if x else None
        years.append(int(m.group(1)) if m else None)

    # Find the "Total" sex section start (row label contains "_T")
    total_start = None
    for i, r in enumerate(rows):
        if r and r[0] and '_T' in r[0] and 'Total' in r[0]:
            total_start = i + 1  # data rows start after the header
            break

    if total_start is None:
        print('[!] Unemployment: Total sex section not found')
        return pd.DataFrame(columns=['cntry', 'year', 'unemployment_rate'])

    records = []
    for row in rows[total_start:]:
        if not row or not row[0]:
            break
        m = re.search(r'\(([A-Z]{3})\)', row[0])
        if not m:
            break
        cntry = _UNEMP_ISO3_TO_ISO2.get(m.group(1))
        if cntry is None:
            continue
        for i, yr in enumerate(years):
            if yr is None or yr not in ALL_YEARS:
                continue
            raw = row[2 + i] if (2 + i) < len(row) else ''
            if raw:
                try:
                    records.append({'cntry': cntry, 'year': yr,
                                    'unemployment_rate': float(raw)})
                except ValueError:
                    pass

    # Switzerland - OECD harmonized rates (EU states only in source file).
    _CH_UNEMP = {
        2002: 3.1, 2004: 4.4, 2006: 4.0, 2008: 3.4, 2010: 4.5,
        2012: 4.2, 2014: 4.9, 2016: 4.9, 2018: 4.7, 2020: 5.3, 2023: 4.1,
    }
    for ess_yr in ALL_YEARS:
        if ess_yr in _CH_UNEMP:
            records.append({'cntry': 'CH', 'year': ess_yr,
                            'unemployment_rate': _CH_UNEMP[ess_yr]})

    # World Bank / ILO modelled unemployment estimates (SL.UEM.TOTL.ZS,
    # fetched 2025-04) for countries absent from the OECD source file.
    _WB_UNEMP = {
        'AL': {2002: 17.89, 2004: 16.31, 2006: 15.63, 2008: 13.06, 2010: 14.09,
               2012: 13.38, 2014: 18.05, 2016: 15.42, 2018: 12.30, 2020: 11.64,
               2023: 10.67},
        'AT': {2002: 4.85, 2004: 5.97, 2006: 5.32, 2008: 4.20, 2010: 4.88,
               2012: 4.91, 2014: 5.67, 2016: 6.06, 2018: 4.93, 2020: 5.20,
               2023: 5.26},
        'BG': {2002: 18.11, 2004: 12.04, 2006: 8.95, 2008: 5.61, 2010: 10.28,
               2012: 12.27, 2014: 11.42, 2016: 7.58, 2018: 5.21, 2020: 5.04,
               2023: 4.32},
        'CY': {2002: 3.34, 2004: 4.77, 2006: 4.59, 2008: 3.76, 2010: 6.36,
               2012: 12.10, 2014: 16.28, 2016: 13.01, 2018: 8.50, 2020: 7.75,
               2023: 5.83},
        'CZ': {2002: 7.28, 2004: 8.30, 2006: 7.14, 2008: 4.39, 2010: 7.28,
               2012: 6.98, 2014: 6.11, 2016: 3.95, 2018: 2.25, 2020: 2.55,
               2023: 2.58},
        'EE': {2002: 10.03, 2004: 10.25, 2006: 5.92, 2008: 5.46, 2010: 16.71,
               2012: 10.02, 2014: 7.35, 2016: 6.88, 2018: 5.41, 2020: 6.96,
               2023: 6.38},
        'GR': {2002: 10.35, 2004: 10.63, 2006: 8.91, 2008: 7.66, 2010: 12.72,
               2012: 24.73, 2014: 26.71, 2016: 23.51, 2018: 19.18, 2020: 15.90,
               2023: 11.02},
        'HR': {2002: 15.05, 2004: 13.66, 2006: 11.13, 2008: 8.53, 2010: 11.62,
               2012: 16.05, 2014: 17.21, 2016: 13.02, 2018: 8.32, 2020: 7.39,
               2023: 6.12},
        'IL': {2002: 12.89, 2004: 13.03, 2006: 10.71, 2008: 7.70, 2010: 8.48,
               2012: 6.76, 2014: 5.79, 2016: 4.72, 2018: 3.92, 2020: 4.17,
               2023: 3.37},
        'IS': {2002: 2.99, 2004: 4.03, 2006: 2.83, 2008: 2.95, 2010: 7.56,
               2012: 6.00, 2014: 4.90, 2016: 2.98, 2018: 2.70, 2020: 5.48,
               2023: 3.52},
        'IT': {2002: 9.21, 2004: 7.87, 2006: 6.78, 2008: 6.72, 2010: 8.36,
               2012: 10.65, 2014: 12.68, 2016: 11.69, 2018: 10.54, 2020: 9.19,
               2023: 7.63},
        'LT': {2002: 13.01, 2004: 10.68, 2006: 5.78, 2008: 5.83, 2010: 17.81,
               2012: 13.37, 2014: 10.70, 2016: 7.86, 2018: 6.15, 2020: 8.49,
               2023: 6.84},
        'LU': {2002: 2.62, 2004: 5.11, 2006: 4.73, 2008: 5.06, 2010: 4.42,
               2012: 5.03, 2014: 6.04, 2016: 6.67, 2018: 5.59, 2020: 6.77,
               2023: 5.18},
        'LV': {2002: 13.83, 2004: 11.71, 2006: 7.03, 2008: 7.74, 2010: 19.48,
               2012: 15.05, 2014: 10.85, 2016: 9.64, 2018: 7.41, 2020: 8.10,
               2023: 6.46},
        'ME': {2002: 30.36, 2004: 30.34, 2006: 24.82, 2008: 17.15, 2010: 19.65,
               2012: 19.81, 2014: 18.05, 2016: 17.73, 2018: 15.19, 2020: 17.88,
               2023: 13.15},
        'MK': {2002: 31.94, 2004: 37.16, 2006: 36.39, 2008: 33.93, 2010: 33.13,
               2012: 31.10, 2014: 28.21, 2016: 24.31, 2018: 21.21, 2020: 16.57,
               2023: 13.17},
        'RO': {2002: 8.11, 2004: 7.72, 2006: 7.27, 2008: 5.79, 2010: 6.96,
               2012: 6.79, 2014: 6.80, 2016: 5.90, 2018: 4.19, 2020: 5.04,
               2023: 5.59},
        'RS': {2002: 13.80, 2004: 18.50, 2006: 20.85, 2008: 13.67, 2010: 19.20,
               2012: 24.00, 2014: 19.22, 2016: 15.26, 2018: 12.73, 2020: 9.01,
               2023: 8.27},
        'RU': {2002: 7.88, 2004: 7.76, 2006: 7.05, 2008: 6.21, 2010: 7.41,
               2012: 5.48, 2014: 5.21, 2016: 5.59, 2018: 4.87, 2020: 5.62,
               2023: 3.08},
        'SK': {2002: 18.54, 2004: 18.21, 2006: 13.39, 2008: 9.51, 2010: 14.39,
               2012: 13.97, 2014: 11.54, 2016: 9.68, 2018: 6.54, 2020: 6.72,
               2023: 5.84},
        'TR': {2002: 10.36, 2004: 10.84, 2006: 10.23, 2008: 10.96, 2010: 11.88,
               2012: 9.21, 2014: 9.90, 2016: 10.90, 2018: 10.96, 2020: 13.15,
               2023: 9.39},
        'UA': {2002: 10.14, 2004: 8.59, 2006: 6.81, 2008: 6.36, 2010: 8.10,
               2012: 7.53, 2014: 9.27, 2016: 9.35, 2018: 8.80, 2020: 9.47,
               2023: 9.47},
    }
    for cntry, yr_vals in _WB_UNEMP.items():
        for ess_yr in ALL_YEARS:
            if ess_yr in yr_vals:
                records.append({'cntry': cntry, 'year': ess_yr,
                                'unemployment_rate': yr_vals[ess_yr]})

    return pd.DataFrame(records)


def _load_micro() -> pd.DataFrame:
    """Compute migration share and mean education from raw ESS CSVs."""
    target = set(COUNTRIES.keys())
    _MISS_MIGR = {7, 8, 9}
    _MISS_EDU  = {77, 88, 99}

    records = []
    for r in range(1, 12):
        csvs = glob.glob(str(ESS_DIR / f'ESS{r}' / '*.csv'))
        if not csvs:
            print(f'  [!] Micro: no CSV for ESS{r}')
            continue
        year = ROUND_TO_YEAR[r]

        df = pd.read_csv(
            csvs[0],
            usecols=['cntry', 'brncntr', 'facntr', 'mocntr', 'eduyrs'],
            low_memory=False,
        )
        df = df[df['cntry'].isin(target)].copy()

        # Migration: at least one of the three variables == 2 (born abroad)
        for col in ['brncntr', 'facntr', 'mocntr']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].where(~df[col].isin(_MISS_MIGR))
        df['migrant'] = (df[['brncntr', 'facntr', 'mocntr']] == 2).any(axis=1)

        # Education: exclude system-missing codes ≥ 77
        df['eduyrs'] = pd.to_numeric(df['eduyrs'], errors='coerce')
        edu = df['eduyrs'].where(~df['eduyrs'].isin(_MISS_EDU))

        for cntry, grp in df.groupby('cntry'):
            edu_grp = edu[grp.index]
            records.append({
                'cntry': cntry,
                'year':  year,
                'migration_share': round(grp['migrant'].mean() * 100, 2),
                'mean_eduyrs':     round(edu_grp.mean(), 2),
            })

    return pd.DataFrame(records)


# ── Precomputed dataset directory ─────────────────────────────────────────────
# On the server (Render), only the three small derived CSVs in this folder exist.
# On a local dev machine, the full raw data is used and the CSVs are regenerated
# by running `python dashboard/export_precomputed.py`.

PRECOMPUTED_DIR = Path(__file__).parent / 'precomputed'


def _load_precomputed(name: str) -> 'pd.DataFrame | None':
    path = PRECOMPUTED_DIR / f'{name}.csv'
    if path.exists():
        print(f'[precomputed] Loading {name}.csv')
        return pd.read_csv(path)
    return None


# ── Master data loader ─────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    cached = _load_precomputed('df_main')
    if cached is not None:
        return cached
    print('[data] Aggregating ESS values from raw CSVs...')
    df = _aggregate_ess_values()
    df['round']        = df['year'].map(YEAR_TO_ROUND)
    df['country_name'] = df['cntry'].map(COUNTRIES)

    # 10 basic Schwartz values (matching generate_radars_ess11_all.py mapping)
    df['v_SD'] = df['ipcrtiv_mean']
    df['v_ST'] = df['ipadvnt_mean']
    df['v_HE'] = df['ipgdtim_mean']
    df['v_AC'] = df['ipsuces_mean']
    df['v_PO'] = df['ipshabt_mean']
    df['v_SE'] = df['ipstrgv_mean']
    df['v_CO'] = df[['ipbhprp_mean', 'ipfrule_mean', 'ipmodst_mean']].mean(axis=1)
    df['v_TR'] = df['iprspot_mean']
    df['v_BE'] = df[['iphlppl_mean', 'iplylfr_mean']].mean(axis=1)
    df['v_UN'] = df[['ipeqopt_mean', 'ipudrst_mean']].mean(axis=1)

    # Δ-scores: subtract row mean across the 10 basic values
    v_cols   = [f'v_{k}' for k in VALUE_KEYS]
    row_mean = df[v_cols].mean(axis=1)
    for k in VALUE_KEYS:
        df[f'd_{k}'] = df[f'v_{k}'] - row_mean

    # 4 higher-order dimensions (raw means of PVQ items)
    df['dim_openness']      = df[['ipcrtiv_mean', 'ipadvnt_mean', 'ipgdtim_mean']].mean(axis=1)
    df['dim_conservation']  = df[['iplylfr_mean', 'ipmodst_mean', 'ipbhprp_mean', 'ipfrule_mean']].mean(axis=1)
    df['dim_enhancement']   = df[['ipshabt_mean', 'ipsuces_mean', 'iprspot_mean', 'ipstrgv_mean']].mean(axis=1)
    df['dim_transcendence'] = df[['iphlppl_mean', 'ipeqopt_mean', 'ipudrst_mean']].mean(axis=1)

    print('[data] Loading ESS micro (migration, education)...')
    micro = _load_micro()
    df = df.merge(micro, on=['cntry', 'year'], how='left')

    print('[data] Loading V-Dem...')
    vdem = _load_vdem()
    df = df.merge(vdem, on=['cntry', 'year'], how='left')

    print('[data] Loading Gini...')
    gini = _load_gini()
    df = df.merge(gini, on=['cntry', 'year'], how='left')

    print('[data] Loading Unemployment...')
    unemp = _load_unemployment()
    df = df.merge(unemp, on=['cntry', 'year'], how='left')

    macro_cols = ['ldi', 'gini', 'unemployment_rate', 'migration_share', 'mean_eduyrs']
    present = [c for c in macro_cols if c in df.columns]
    print(f'[data] Master dataset: {df.shape[0]} rows × {df.shape[1]} cols')
    print(f'[data] Macro coverage (non-NaN per column):')
    for c in present:
        print(f'  {c}: {df[c].notna().sum()}/{len(df)} rows')
    print(f'[data] Sample (DE, 2023):')
    sample = df[(df['cntry'] == 'DE') & (df['year'] == 2023)][
        ['cntry', 'year'] + present
    ]
    print(sample.to_string(index=False))

    return df


def load_scatter_data() -> pd.DataFrame:
    """Load macro_schwartz_analysis_data, compute Schwartz delta dim scores.

    Checks precomputed/df_scatter.csv first (server mode).
    Returns a DataFrame (up to 39 countries × 11 ESS rounds, ~248 rows) with all
    predictor and Schwartz dimension columns, plus 'ess_round' and
    'country_name'. Real data patches for wb_gini are applied from
    _GINI_PATCHES (World Bank / Eurostat, fetched 2026-04-28).
    """
    cached = _load_precomputed('df_scatter')
    if cached is not None:
        return cached

    df = pd.read_csv(SCATTER_PATH)
    df['ess_round'] = df['year'].map(YEAR_TO_ROUND)

    # Apply wb_gini real-data patches
    for (cntry, year), (value, _source) in _GINI_PATCHES.items():
        mask = (df['cntry'] == cntry) & (df['year'] == year)
        df.loc[mask, 'wb_gini'] = value

    # Basic Schwartz values from PVQ item means
    df['v_SD'] = df['ipcrtiv_mean']
    df['v_ST'] = df['ipadvnt_mean']
    df['v_HE'] = df['ipgdtim_mean']
    df['v_AC'] = df['ipsuces_mean']
    df['v_PO'] = df['ipshabt_mean']
    df['v_SE'] = df['ipstrgv_mean']
    df['v_CO'] = df[['ipbhprp_mean', 'ipfrule_mean', 'ipmodst_mean']].mean(axis=1)
    df['v_TR'] = df['iprspot_mean']
    df['v_BE'] = df[['iphlppl_mean', 'iplylfr_mean']].mean(axis=1)
    df['v_UN'] = df[['ipeqopt_mean', 'ipudrst_mean']].mean(axis=1)

    # Ipsatize per country-round row
    v_cols   = [f'v_{k}' for k in VALUE_KEYS]
    row_mean = df[v_cols].mean(axis=1)
    for k in VALUE_KEYS:
        df[f'd_{k}'] = df[f'v_{k}'] - row_mean

    # Higher-order dimension delta scores
    df['dim_openness']      = df[['d_SD', 'd_ST', 'd_HE']].mean(axis=1)
    df['dim_transcendence'] = df[['d_UN', 'd_BE']].mean(axis=1)
    df['dim_conservation']  = df[['d_TR', 'd_CO', 'd_SE']].mean(axis=1)
    df['dim_enhancement']   = df[['d_PO', 'd_AC']].mean(axis=1)

    df['country_name'] = df['cntry'].map(COUNTRIES)

    x_cols = [col for col, _, _ in SCATTER_X_META]
    y_cols = [col for col, _, _ in SCATTER_Y_META]
    keep   = ['cntry', 'country_name', 'year', 'ess_round'] + \
             [c for c in x_cols + y_cols if c in df.columns]
    df = df[keep].copy()

    n_patched = sum(1 for k in _GINI_PATCHES
                    if df[(df['cntry'] == k[0]) & (df['year'] == k[1])]['wb_gini'].notna().any())
    print(f'[scatter] {len(df)} rows, {len(keep)-4} variables, '
          f'{n_patched} Gini patches applied')
    return df


def load_micro_individual(sample_per_dim: int = 300, seed: int = 42) -> pd.DataFrame:
    """Load individual ESS respondents, classify by dominant Schwartz dimension, stratified-sample.

    Checks precomputed/df_micro.csv first (server mode, no raw ESS data needed).
    Returns a DataFrame with one row per sampled respondent containing:
    - cntry, essround
    - dominant_dim (str), dim_id (int 0-3)
    - 12 attitude variables (see MICRO_ATTRS / MICRO_ATTR_META)
      redistr_supp = 6 - gincdif  (higher = more redistribution support)
      safety       = 5 - aesfdrk  (higher = feels safer)
    """
    cached = _load_precomputed('df_micro')
    if cached is not None:
        return cached
    target_countries = set(COUNTRIES.keys())
    pvq_cols = list(_PVQ_TO_DIM.keys())
    needed   = pvq_cols + MICRO_ATTRS + ['cntry', 'essround']

    frames = []
    for r in range(1, 12):
        csvs = glob.glob(str(ESS_DIR / f'ESS{r}' / '*.csv'))
        if not csvs:
            print(f'  [micro] no CSV for ESS{r}')
            continue
        print(f'  [micro] loading ESS{r}...')
        header = pd.read_csv(csvs[0], nrows=0)
        header.columns = header.columns.str.lower()
        avail = [c for c in needed if c in header.columns]

        df_r = pd.read_csv(csvs[0], usecols=avail, low_memory=False)
        df_r.columns = df_r.columns.str.lower()
        df_r = df_r[df_r['cntry'].isin(target_countries)].copy()
        for c in needed:
            if c not in df_r.columns:
                df_r[c] = np.nan
        frames.append(df_r[needed])

    df = pd.concat(frames, ignore_index=True)

    # ── Clean PVQ items (scale 1-6; codes 7/8/9 = missing) ──
    for col in pvq_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].where(df[col] <= 6)

    # Drop rows with fewer than 10 valid PVQ items
    df = df[df[pvq_cols].notna().sum(axis=1) >= 10].copy()

    # Ipsatize per respondent (subtract personal mean across available items)
    pvq_mean = df[pvq_cols].mean(axis=1)
    ip = df[pvq_cols].sub(pvq_mean, axis=0)

    # Compute ipsatized higher-order dimension scores
    oc_items = [c for c, d in _PVQ_TO_DIM.items() if d == 'oc']
    st_items = [c for c, d in _PVQ_TO_DIM.items() if d == 'st']
    co_items = [c for c, d in _PVQ_TO_DIM.items() if d == 'co']
    se_items = [c for c, d in _PVQ_TO_DIM.items() if d == 'se']
    df['_oc'] = ip[oc_items].mean(axis=1)
    df['_st'] = ip[st_items].mean(axis=1)
    df['_co'] = ip[co_items].mean(axis=1)
    df['_se'] = ip[se_items].mean(axis=1)

    # Assign dominant dimension (argmax of ipsatized scores)
    dim_arr  = df[['_oc', '_st', '_co', '_se']].values
    dim_idx  = np.argmax(dim_arr, axis=1)
    dim_names = ['Openness to Change', 'Self-Transcendence', 'Conservation', 'Self-Enhancement']
    df['dominant_dim'] = [dim_names[i] for i in dim_idx]
    df['dim_id']       = dim_idx.astype(float)

    # ── Clean attitude variables ──
    # Per-variable valid max: any value above this is a missing code
    _valid_max = {
        'ppltrst': 10, 'trstplt': 10, 'trstlgl': 10, 'stflife': 10,
        'stfeco':  10, 'stfdem':  10, 'lrscale': 10, 'happy':   10,
        'imwbcnt': 10, 'rlgdgr':  10, 'gincdif': 5,  'aesfdrk': 4,
    }
    for col in MICRO_ATTRS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].where(df[col] <= _valid_max.get(col, 10))

    # Impute missing values with round-level median
    for col in MICRO_ATTRS:
        medians = df.groupby('essround')[col].transform('median')
        df[col] = df[col].fillna(medians)

    # Invert direction for two variables so higher = more positive on every axis
    df['redistr_supp'] = 6 - df['gincdif']   # 1=oppose → 1,  5=support → 5
    df['safety']       = 5 - df['aesfdrk']    # 1=unsafe → 1,  4=very safe → 4

    # Stratified sample: sample_per_dim rows per dominant dimension
    rng   = np.random.RandomState(seed)
    parts = []
    for dim in dim_names:
        sub = df[df['dominant_dim'] == dim]
        n   = min(sample_per_dim, len(sub))
        parts.append(sub.sample(n=n, random_state=rng))

    result = pd.concat(parts, ignore_index=True)
    attr_cols = [col for col, _, _ in MICRO_ATTR_META]
    keep = ['cntry', 'essround', 'dominant_dim', 'dim_id'] + attr_cols
    print(f'[micro] {len(result)} sampled respondents '
          f'({sample_per_dim}/dim across {len(dim_names)} dims)')
    return result[keep]


# ── Sociological indicator metadata and loader ────────────────────────────────

INDICATOR_META: dict[str, dict] = {
    'ess_trust_pct': {
        'label':   'Social Trust',
        'unit':    '% scoring 6-10',
        'desc':    'Share of ESS respondents scoring 6-10 on "Most people can be trusted or you can\'t be too careful" (ppltrst, 0-10). Weighted with pspwght.',
        'source':  'European Social Survey (ESS), most recent available round per country',
        'url':     'https://ess.nsd.no',
        'range':   (5, 85),
    },
    'ess_religiosity_pct': {
        'label':   'Religiosity',
        'unit':    '% scoring 6-10',
        'desc':    'Share of ESS respondents scoring 6-10 on "How religious are you?" (rlgdgr, 0-10). Weighted with pspwght.',
        'source':  'European Social Survey (ESS), most recent available round per country',
        'url':     'https://ess.nsd.no',
        'range':   (10, 80),
    },
    'estat_gini': {
        'label':   'Gini Index',
        'unit':    '0-100',
        'desc':    'Gini coefficient of equivalised disposable income. 0 = perfect equality, 100 = maximum inequality.',
        'source':  'Eurostat EU-SILC (ilc_di12); Ireland supplemented from Eurostat SILC',
        'url':     'https://ec.europa.eu/eurostat/databrowser/view/ilc_di12',
        'range':   (20, 50),
    },
    'estat_gdp_pps': {
        'label':   'GDP per Capita (PPS)',
        'unit':    'EU27 = 100',
        'desc':    'GDP per capita in Purchasing Power Standards, indexed to EU27 average = 100.',
        'source':  'Eurostat (tec00114)',
        'url':     'https://ec.europa.eu/eurostat/databrowser/view/tec00114',
        'range':   (20, 300),
    },
    'estat_tertiary_pct': {
        'label':   'Tertiary Attainment 25-34',
        'unit':    '%',
        'desc':    'Share of 25-34 year-olds with a tertiary qualification (ISCED 5-8).',
        'source':  'Eurostat (edat_lfse_03)',
        'url':     'https://ec.europa.eu/eurostat/databrowser/view/edat_lfse_03',
        'range':   (15, 80),
    },
    'estat_hly': {
        'label':   'Healthy Life Years',
        'unit':    'years at birth',
        'desc':    'Expected years lived in good health at birth (Sullivan method, self-assessed disability).',
        'source':  'Eurostat (hlth_hlye)',
        'url':     'https://ec.europa.eu/eurostat/databrowser/view/hlth_hlye',
        'range':   (50, 80),
    },
    'eige_gei': {
        'label':   'Gender Equality Index',
        'unit':    '0-100',
        'desc':    'EIGE composite index across work, money, knowledge, time, power, health (100 = full equality). EU27 only.',
        'source':  'European Institute for Gender Equality (EIGE), 2023 edition (data year 2021)',
        'url':     'https://eige.europa.eu/gender-equality-index/2023',
        'range':   (45, 90),
    },
    'ti_cpi': {
        'label':   'Corruption Perceptions Index',
        'unit':    '0-100',
        'desc':    'Perceived corruption in the public sector. 0 = highly corrupt, 100 = very clean.',
        'source':  'Transparency International CPI 2024 (via Our World in Data)',
        'url':     'https://www.transparency.org/en/cpi',
        'range':   (20, 100),
    },
    'vdem_ldi': {
        'label':   'Liberal Democracy Index',
        'unit':    '0-1',
        'desc':    'V-Dem Liberal Democracy Index: electoral democracy + rule of law + civil liberties + executive constraints.',
        'source':  'V-Dem Institute, Country-Year dataset v15 (v2x_libdem)',
        'url':     'https://www.v-dem.net',
        'range':   (0, 1),
    },
    'whr_ladder': {
        'label':   'Life Satisfaction',
        'unit':    '0-10 (Cantril ladder)',
        'desc':    'National average self-reported life satisfaction on the Cantril ladder (0 = worst, 10 = best possible life).',
        'source':  'World Happiness Report, 3-year average (via Our World in Data)',
        'url':     'https://worldhappiness.report',
        'range':   (3.5, 8.5),
    },
    'estat_foreign_born_pct': {
        'label':   'Foreign-born Share',
        'unit':    '% of population',
        'desc':    'International migrant stock as a share of total population.',
        'source':  'World Bank Development Indicators (SM.POP.TOTL.ZS)',
        'url':     'https://data.worldbank.org/indicator/SM.POP.TOTL.ZS',
        'range':   (0, 60),
    },
    'oecd_union_density': {
        'label':   'Trade Union Density',
        'unit':    '% of wage earners',
        'desc':    'Share of wage and salary earners who are trade union members.',
        'source':  'OECD Trade Union Dataset (DSD_TUD_CBC@DF_TUD)',
        'url':     'https://stats.oecd.org/index.aspx?DataSetCode=TUD',
        'range':   (2, 95),
    },
}

_INDICATORS_PATH = Path(__file__).parent / 'precomputed' / 'df_indicators.csv'
_SENTENCES_PATH  = Path(__file__).parent / 'precomputed' / 'indicator_sentences.json'


def load_indicators() -> tuple[pd.DataFrame, dict]:
    """Load per-country indicator values and contextualising sentences.

    Returns (df_indicators, sentences) where:
      df_indicators: DataFrame indexed by cntry with value + year columns
      sentences:     {cntry: {col: sentence_str}}
    """
    import json
    df = pd.read_csv(_INDICATORS_PATH).set_index('cntry') \
        if _INDICATORS_PATH.exists() else pd.DataFrame()
    sentences: dict = {}
    if _SENTENCES_PATH.exists():
        sentences = json.loads(_SENTENCES_PATH.read_text())
    return df, sentences


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


# ── PCA + clustering ────────────────────────────────────────────────────────────

# Higher-order dimension → indices into VALUE_KEYS (for loading interpretation)
_DIM_VALUE_IDX = {
    'Openness to Change': [VALUE_KEYS.index('SD'), VALUE_KEYS.index('HE'), VALUE_KEYS.index('ST')],
    'Self-Transcendence': [VALUE_KEYS.index('UN'), VALUE_KEYS.index('BE')],
    'Conservation':       [VALUE_KEYS.index('TR'), VALUE_KEYS.index('CO'), VALUE_KEYS.index('SE')],
    'Self-Enhancement':   [VALUE_KEYS.index('PO'), VALUE_KEYS.index('AC')],
}


def compute_pca_clustering(df: pd.DataFrame, round_year: int, n_clusters: int = 3):
    """PCA (2 components) + KMeans on the 10 Schwartz Δ-scores for one ESS round.

    Returns (result_df, explained_variance, pc1_label, pc2_label).
    result_df columns: cntry, country_name, d_SD … d_ST, pc1, pc2, cluster.
    Returns (None, None, None, None) if no data for round_year.
    """
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans

    data = df[df['year'] == round_year].copy().reset_index(drop=True)
    if data.empty:
        return None, None, None, None

    d_cols = [f'd_{k}' for k in VALUE_KEYS]
    X = data[d_cols].values  # (n_countries, 10)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = km.fit_predict(X)

    # Label each PC by the dominant Schwartz dimension contrast
    pc_labels = []
    for loading in pca.components_:
        dim_mean = {
            dim: float(np.mean(loading[idxs]))
            for dim, idxs in _DIM_VALUE_IDX.items()
        }
        ordered = sorted(dim_mean.items(), key=lambda x: x[1])
        neg_dim, pos_dim = ordered[0][0], ordered[-1][0]
        if abs(dim_mean[pos_dim]) > 0.10 and abs(dim_mean[neg_dim]) > 0.10:
            label = f'{pos_dim} ↔ {neg_dim}'
        else:
            label = 'Mixed dimension'
        pc_labels.append(label)

    result = data[['cntry', 'country_name'] + d_cols].copy()
    result['pc1']     = coords[:, 0]
    result['pc2']     = coords[:, 1]
    result['cluster'] = clusters

    return result, pca.explained_variance_ratio_.tolist(), pc_labels[0], pc_labels[1]


