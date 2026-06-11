"""Data layer for the Human Values dashboard - ESS Round 11 (2023) only.

Responsibilities:
  - Constants: country metadata, Schwartz value model, variable metadata
  - Build functions: compute all derived datasets from the raw ESS11 CSV
    (run locally via export_precomputed.py; raw microdata never deployed)
  - Load functions: read the small precomputed CSVs at app start (server mode)
  - Analysis helpers: PCA + K-Means with silhouette validation

Methodology (see the About tab for the user-facing version):
  - Full PVQ-21 item battery with the standard ESS item-to-value mapping
  - Items are reverse-coded (7 - x) so higher = stronger endorsement
  - Scores are ipsatized at the person level (centred at each respondent's
    own mean across all valid items) following Schwartz's recommendation
  - All aggregates use the ESS analysis weight (anweight)
"""
from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_THIS_DIR       = Path(__file__).parent
_DATA_DIR       = _THIS_DIR.parent / 'data'
ESS11_DIR       = _DATA_DIR / 'raw' / 'ess' / 'ESS11'
MACRO_CSV       = _DATA_DIR / 'merged_datasets' / 'macro_schwartz_analysis_data.csv'
PRECOMPUTED_DIR = _THIS_DIR / 'precomputed'

# ── Survey constants ───────────────────────────────────────────────────────────
ESS_YEAR  = 2023   # ESS Round 11 reference year
ESS_ROUND = 11

# Quality thresholds
MIN_VALID_PVQ = 16   # respondent needs >= 16 of 21 valid PVQ items
MIN_REGION_N  = 50   # minimum unweighted respondents per NUTS region
MIN_GROUP_N   = 30   # minimum unweighted respondents per gradient group

# ── Country metadata ───────────────────────────────────────────────────────────
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

# The 30 countries fielded in ESS Round 11
ESS11_COUNTRIES = [
    'AT', 'BE', 'BG', 'CH', 'CY', 'DE', 'EE', 'ES', 'FI', 'FR',
    'GB', 'GR', 'HR', 'HU', 'IE', 'IL', 'IS', 'IT', 'LT', 'LV',
    'ME', 'NL', 'NO', 'PL', 'PT', 'RS', 'SE', 'SI', 'SK', 'UA',
]

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

# (capital, population_millions, area_km2, political_system, eu_status)
COUNTRY_INFO = {
    'AT': ('Vienna',        9.1,    83871,   'Federal Parliamentary Republic',       'EU 1995'),
    'BE': ('Brussels',     11.6,    30528,   'Federal Constitutional Monarchy',      'EU 1952'),
    'BG': ('Sofia',         6.5,   110879,   'Parliamentary Republic',              'EU 2007'),
    'CH': ('Bern',          8.7,    41285,   'Federal Council / Direct Democracy',  'EEA'),
    'CY': ('Nicosia',       1.2,     9251,   'Presidential Republic',               'EU 2004'),
    'DE': ('Berlin',       84.4,   357114,   'Federal Parliamentary Republic',       'EU 1952'),
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
    'LV': ('Riga',          1.8,    64589,   'Parliamentary Republic',              'EU 2004'),
    'ME': ('Podgorica',     0.6,    13812,   'Parliamentary Republic',              'Candidate'),
    'NL': ('Amsterdam',    17.8,    41543,   'Constitutional Monarchy',             'EU 1952'),
    'NO': ('Oslo',          5.5,   385207,   'Constitutional Monarchy',             'EEA'),
    'PL': ('Warsaw',       38.0,   312696,   'Parliamentary Republic',              'EU 2004'),
    'PT': ('Lisbon',       10.3,    92212,   'Semi-Presidential Republic',          'EU 1986'),
    'RS': ('Belgrade',      6.8,    77474,   'Parliamentary Republic',              'Candidate'),
    'SE': ('Stockholm',    10.5,   450295,   'Constitutional Monarchy',             'EU 1995'),
    'SI': ('Ljubljana',     2.1,    20273,   'Parliamentary Republic',              'EU 2004'),
    'SK': ('Bratislava',    5.5,    49035,   'Parliamentary Republic',              'EU 2004'),
    'UA': ('Kyiv',         43.5,   603550,   'Semi-Presidential Republic',          'Candidate'),
}

# ── Schwartz value model ───────────────────────────────────────────────────────
VALUE_KEYS = ['SD', 'UN', 'BE', 'TR', 'CO', 'SE', 'PO', 'AC', 'HE', 'ST']
VALUE_LABELS = {
    'SD': 'Self-Direction', 'UN': 'Universalism', 'BE': 'Benevolence',
    'TR': 'Tradition',      'CO': 'Conformity',   'SE': 'Security',
    'PO': 'Power',          'AC': 'Achievement',  'HE': 'Hedonism',
    'ST': 'Stimulation',
}

# Standard ESS PVQ-21 item-to-value assignment (ESS Data Documentation).
# ESS11 stores these with an 'a' suffix (e.g. ipcrtiva) which is stripped
# on load. All 21 items are used - earlier versions of this project used
# only 14 items with a partially incorrect mapping.
PVQ21_ITEMS: dict[str, list[str]] = {
    'SD': ['ipcrtiv', 'impfree'],
    'PO': ['imprich', 'iprspot'],
    'UN': ['ipeqopt', 'ipudrst', 'impenv'],
    'AC': ['ipshabt', 'ipsuces'],
    'SE': ['impsafe', 'ipstrgv'],
    'ST': ['impdiff', 'ipadvnt'],
    'CO': ['ipfrule', 'ipbhprp'],
    'TR': ['ipmodst', 'imptrad'],
    'HE': ['ipgdtim', 'impfun'],
    'BE': ['iphlppl', 'iplylfr'],
}
ALL_PVQ_ITEMS = [item for items in PVQ21_ITEMS.values() for item in items]

VALUE_TO_DIM = {
    'SD': 'Openness to Change', 'HE': 'Openness to Change', 'ST': 'Openness to Change',
    'UN': 'Self-Transcendence', 'BE': 'Self-Transcendence',
    'TR': 'Conservation',       'CO': 'Conservation',       'SE': 'Conservation',
    'PO': 'Self-Enhancement',   'AC': 'Self-Enhancement',
}

DIM_COLS = {
    'Openness to Change': 'dim_openness',
    'Self-Transcendence': 'dim_transcendence',
    'Conservation':       'dim_conservation',
    'Self-Enhancement':   'dim_enhancement',
}
DIMS = list(DIM_COLS.keys())

_DIM_VALUES = {
    'dim_openness':      ['SD', 'HE', 'ST'],
    'dim_transcendence': ['UN', 'BE'],
    'dim_conservation':  ['TR', 'CO', 'SE'],
    'dim_enhancement':   ['PO', 'AC'],
}

# Radial axis range for the country radar (country-level Δ-scores comfortably
# fit inside; verified against the ESS11 build output)
DELTA_RANGE = [-1.5, 1.5]

# ── Deep-dive (regional) configuration ─────────────────────────────────────────
DEEP_DIVE_COUNTRIES = {
    'DE': {'label': 'Germany',     'nuts_level': 1, 'prefix': 'DE'},
    'CH': {'label': 'Switzerland', 'nuts_level': 2, 'prefix': 'CH'},
}

# East/West classification of German NUTS-1 regions (new Länder vs. old)
_DE_EAST   = {'DE4', 'DE8', 'DED', 'DEE', 'DEG'}
_DE_BERLIN = {'DE3'}

# Swiss NUTS-2 language regions
_CH_LANGUAGE = {
    'CH01': 'French-speaking (Romandie)',
    'CH02': 'Mixed FR/DE (Mittelland)',
    'CH03': 'German-speaking',
    'CH04': 'German-speaking',
    'CH05': 'German-speaking',
    'CH06': 'German-speaking',
    'CH07': 'Italian-speaking (Ticino)',
}

# Eurostat regional indicators offered in the deep-dive scatter
# (key matches the 'indicator' column written by build_regional.py)
REGIONAL_INDICATOR_META = {
    'gdp_pps': {
        'label':  'GDP per capita (PPS)',
        'desc':   'Regional GDP per inhabitant in Purchasing Power Standards.',
        'source': 'Eurostat nama_10r_2gdp (not available for Swiss regions)',
    },
    'unemployment': {
        'label':  'Unemployment rate (%)',
        'desc':   'Unemployment rate, ages 15-74, % of the labour force.',
        'source': 'Eurostat lfst_r_lfu3rt',
    },
    'tertiary_pct': {
        'label':  'Tertiary attainment 25-64 (%)',
        'desc':   'Share of 25-64 year-olds with a tertiary degree (ISCED 5-8).',
        'source': 'Eurostat edat_lfse_04',
    },
    'median_age': {
        'label':  'Median age (years)',
        'desc':   'Median age of the regional population.',
        'source': 'Eurostat demo_r_pjanind2',
    },
    'pop_density': {
        'label':  'Population density (per km²)',
        'desc':   'Inhabitants per square kilometre.',
        'source': 'Eurostat demo_r_d3dens',
    },
}

GRADIENT_VARS = {
    'age':         {'label': 'Age group'},
    'education':   {'label': 'Education'},
    'domicil':     {'label': 'Urbanisation'},
    'gender':      {'label': 'Gender'},
    'religiosity': {'label': 'Religiosity'},
    'region_block': {'label': 'East / West (Germany)', 'countries': ['DE']},
    'language':     {'label': 'Language region (Switzerland)', 'countries': ['CH']},
}

# ── ESS11 microdata: reading and person-level scoring ──────────────────────────

_ATTITUDE_COLS = ['ppltrst', 'rlgdgr', 'lrscale', 'aesfdrk',
                  'brncntr', 'facntr', 'mocntr']
_DEMO_COLS     = ['gndr', 'agea', 'eduyrs', 'domicil']

# Per-variable maximum valid code; anything above is an ESS missing code
_VALID_MAX = {
    'ppltrst': 10, 'rlgdgr': 10, 'lrscale': 10, 'aesfdrk': 4,
    'brncntr': 2,  'facntr':  2, 'mocntr':  2,
    'gndr':    2,  'agea':  120, 'eduyrs': 60,  'domicil': 5,
}


def _find_ess11_csv() -> Path:
    """Locate the raw ESS11 CSV (one file expected in data/raw/ess/ESS11).

    Returns:
        Path to the CSV.

    Raises:
        FileNotFoundError: if no CSV is present (server deployments only
            ship precomputed aggregates, never the raw file).
    """
    matches = glob.glob(str(ESS11_DIR / '*.csv'))
    if not matches:
        raise FileNotFoundError(f'No raw ESS11 CSV found in {ESS11_DIR}')
    return Path(matches[0])


def read_ess11_micro() -> pd.DataFrame:
    """Read and clean the ESS11 microdata needed by all build functions.

    Returns:
        One row per respondent with cleaned PVQ items (1-6, NaN otherwise),
        attitude and demographic variables (missing codes -> NaN), the
        analysis weight ``anweight``, and the NUTS ``region`` code.
    """
    csv_path = _find_ess11_csv()
    pvq_raw  = [item + 'a' for item in ALL_PVQ_ITEMS]   # ESS11 suffixed names
    usecols  = (['cntry', 'region', 'anweight'] + pvq_raw
                + _ATTITUDE_COLS + _DEMO_COLS)
    df = pd.read_csv(csv_path, usecols=usecols, low_memory=False)
    df.rename(columns={raw: raw[:-1] for raw in pvq_raw}, inplace=True)

    for col in ALL_PVQ_ITEMS:
        vals = pd.to_numeric(df[col], errors='coerce')
        df[col] = vals.where((vals >= 1) & (vals <= 6))

    for col, vmax in _VALID_MAX.items():
        vals = pd.to_numeric(df[col], errors='coerce')
        df[col] = vals.where(vals <= vmax)

    df['region'] = df['region'].astype(str).str.strip()
    log.info('ESS11 micro: %d respondents, %d countries',
             len(df), df['cntry'].nunique())
    return df


def add_person_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute reverse-coded, person-centred Schwartz scores per respondent.

    Steps (Schwartz's recommended procedure):
      1. Reverse-code each PVQ item: z = 7 - x, so higher = "more like me".
      2. Drop respondents with fewer than MIN_VALID_PVQ valid items.
      3. Value score s_K = mean of that value's valid items.
      4. Centre at the person mean (mrat) across all valid items: c_K = s_K - mrat.
      5. Higher-order dimensions = mean of their constituent centred values.

    Args:
        df: Output of read_ess11_micro().

    Returns:
        Copy of df (filtered) with columns ``c_<KEY>`` and ``dim_*`` added.
    """
    rev = 7 - df[ALL_PVQ_ITEMS]
    valid_count = rev.notna().sum(axis=1)
    keep = valid_count >= MIN_VALID_PVQ
    df, rev = df[keep].copy(), rev[keep]
    log.info('Person scores: kept %d respondents (>= %d valid PVQ items)',
             len(df), MIN_VALID_PVQ)

    mrat = rev.mean(axis=1)
    for key, items in PVQ21_ITEMS.items():
        df[f'c_{key}'] = rev[items].mean(axis=1) - mrat
    for dim_col, keys in _DIM_VALUES.items():
        df[dim_col] = df[[f'c_{k}' for k in keys]].mean(axis=1)
    return df


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Weighted mean ignoring NaN values (NaN if nothing valid)."""
    mask = values.notna() & weights.notna()
    if not mask.any():
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


_SCORE_COLS = [f'c_{k}' for k in VALUE_KEYS] + list(_DIM_VALUES.keys())


def _aggregate_scores(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Weighted aggregation of person-level Schwartz scores.

    Args:
        df: Microdata with person scores (add_person_scores output).
        by: Grouping columns, e.g. ['cntry'] or ['cntry', 'region'].

    Returns:
        One row per group: d_<KEY> / dim_* weighted means + unweighted ``n``.
    """
    records = []
    for group_keys, grp in df.groupby(by):
        if not isinstance(group_keys, tuple):
            group_keys = (group_keys,)
        row = dict(zip(by, group_keys))
        row['n'] = len(grp)
        for col in _SCORE_COLS:
            out = col.replace('c_', 'd_')   # country-level Δ naming
            row[out] = _weighted_mean(grp[col], grp['anweight'])
        records.append(row)
    return pd.DataFrame(records)


# ── Build functions (local only - need the raw ESS11 CSV) ──────────────────────

def build_country_aggregates(micro: pd.DataFrame) -> pd.DataFrame:
    """Country-level weighted Schwartz aggregates (df_main).

    Args:
        micro: Person-scored microdata.

    Returns:
        One row per ESS11 country with d_* / dim_* scores, n, and metadata.
    """
    agg = _aggregate_scores(micro, ['cntry'])
    agg = agg[agg['cntry'].isin(COUNTRIES)].copy()
    agg['country_name'] = agg['cntry'].map(COUNTRIES)
    agg['year']  = ESS_YEAR
    agg['round'] = ESS_ROUND
    return agg.sort_values('cntry').reset_index(drop=True)


def build_regional_aggregates(micro: pd.DataFrame) -> pd.DataFrame:
    """NUTS-region weighted Schwartz aggregates for the deep-dive countries.

    Regions with fewer than MIN_REGION_N respondents are kept but flagged
    via ``below_min_n`` so the UI can grey them out.

    Args:
        micro: Person-scored microdata.

    Returns:
        One row per (cntry, region) for DE (NUTS-1) and CH (NUTS-2).
    """
    sub = micro[micro['cntry'].isin(DEEP_DIVE_COUNTRIES)].copy()
    sub = sub[sub['region'].str.match(r'^(DE.|CH..)$', na=False)]
    agg = _aggregate_scores(sub, ['cntry', 'region'])
    agg['below_min_n'] = agg['n'] < MIN_REGION_N
    return agg.sort_values(['cntry', 'region']).reset_index(drop=True)


def _gradient_groups(df: pd.DataFrame, var: str) -> pd.Series:
    """Map raw microdata to labelled gradient groups for one variable.

    Args:
        df: Person-scored microdata (one deep-dive country).
        var: Key in GRADIENT_VARS.

    Returns:
        Series of group labels (NaN = respondent not classifiable).
    """
    if var == 'age':
        return pd.cut(df['agea'], bins=[14, 29, 44, 59, 74, 120],
                      labels=['15-29', '30-44', '45-59', '60-74', '75+'])
    if var == 'education':
        return pd.cut(df['eduyrs'], bins=[-1, 11.5, 15.5, 60],
                      labels=['Low (<12 yrs)', 'Medium (12-15 yrs)', 'High (16+ yrs)'])
    if var == 'domicil':
        return pd.cut(df['domicil'], bins=[0, 2, 3, 5],
                      labels=['City & suburbs', 'Town', 'Village / rural'])
    if var == 'gender':
        return df['gndr'].map({1.0: 'Men', 2.0: 'Women'})
    if var == 'religiosity':
        return pd.cut(df['rlgdgr'], bins=[-1, 3, 6, 10],
                      labels=['Low (0-3)', 'Medium (4-6)', 'High (7-10)'])
    if var == 'region_block':
        return df['region'].map(
            lambda r: 'East Germany' if r in _DE_EAST
            else 'Berlin' if r in _DE_BERLIN
            else 'West Germany' if str(r).startswith('DE') else np.nan)
    if var == 'language':
        return df['region'].map(_CH_LANGUAGE)
    raise ValueError(f'Unknown gradient variable: {var}')


def build_gradients(micro: pd.DataFrame) -> pd.DataFrame:
    """Within-country social gradients for the deep-dive countries.

    Args:
        micro: Person-scored microdata.

    Returns:
        Long DataFrame: one row per (cntry, variable, group) with weighted
        d_* / dim_* scores and unweighted n. Groups below MIN_GROUP_N are
        dropped.
    """
    frames = []
    for cntry in DEEP_DIVE_COUNTRIES:
        sub = micro[micro['cntry'] == cntry]
        for var, meta in GRADIENT_VARS.items():
            if 'countries' in meta and cntry not in meta['countries']:
                continue
            groups = _gradient_groups(sub, var)
            tmp = sub.assign(_group=groups.astype(object)).dropna(subset=['_group'])
            agg = _aggregate_scores(tmp, ['_group'])
            agg = agg[agg['n'] >= MIN_GROUP_N]
            order = (list(groups.cat.categories)
                     if hasattr(groups, 'cat') else sorted(agg['_group']))
            agg['group_order'] = agg['_group'].map(
                {g: i for i, g in enumerate(order)})
            agg['cntry'], agg['variable'], agg['var_label'] = cntry, var, meta['label']
            frames.append(agg.rename(columns={'_group': 'group'}))
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(['cntry', 'variable', 'group_order']).reset_index(drop=True)


def _build_ess_predictors(micro: pd.DataFrame) -> pd.DataFrame:
    """Weighted country-level ESS-derived predictors (trust, religiosity, ...).

    Args:
        micro: Person-scored microdata.

    Returns:
        One row per country with the eight ESS-derived X variables.
    """
    records = []
    for cntry, grp in micro.groupby('cntry'):
        w = grp['anweight']
        urban   = grp['domicil'].isin([1, 2]).astype(float).where(grp['domicil'].notna())
        migrant = ((grp[['brncntr', 'facntr', 'mocntr']] == 2).any(axis=1)
                   .astype(float)
                   .where(grp[['brncntr', 'facntr', 'mocntr']].notna().any(axis=1)))
        records.append({
            'cntry':            cntry,
            'trust_mean':       _weighted_mean(grp['ppltrst'], w),
            'religiosity_mean': _weighted_mean(grp['rlgdgr'], w),
            'eduyrs_mean':      _weighted_mean(grp['eduyrs'], w),
            'safety_mean':      _weighted_mean(grp['aesfdrk'], w),
            'lrscale_mean':     _weighted_mean(grp['lrscale'], w),
            'age_mean':         _weighted_mean(grp['agea'], w),
            'urban_pct':        _weighted_mean(urban, w) * 100,
            'diversity_pct':    _weighted_mean(migrant, w) * 100,
        })
    return pd.DataFrame(records)


# Real-data Gini patches for 2023 (World Bank / Eurostat, fetched 2026-04-28)
_GINI_PATCHES_2023 = {
    'HU': 28.6,   # Eurostat EU-SILC 2023 (series break)
    'CH': 33.8,   # World Bank 2022 (forward-carry)
    'DE': 33.7,   # World Bank 2022 (forward-carry)
    'NL': 25.7,   # World Bank 2021 (forward-carry)
}

_EXTERNAL_X_COLS = ['v2x_libdem', 'wb_gini', 'wb_unemployment',
                    'wb_gdp_per_capita_ppp']
GOV_EXP_COLS = [
    'gov_exp_health', 'gov_exp_education', 'gov_exp_social',
    'gov_exp_defence', 'gov_exp_economic', 'gov_exp_public_services',
    'gov_exp_culture',
]


def _load_external_macro_2023() -> pd.DataFrame:
    """External macro X variables for 2023 from the merged analysis dataset.

    Returns:
        One row per country: V-Dem LDI, World Bank Gini / unemployment / GDP,
        with documented real-data Gini patches applied.
    """
    df = pd.read_csv(MACRO_CSV)
    df = df[df['year'] == ESS_YEAR].copy()
    for cntry, value in _GINI_PATCHES_2023.items():
        df.loc[df['cntry'] == cntry, 'wb_gini'] = value
    keep = ['cntry'] + [c for c in _EXTERNAL_X_COLS if c in df.columns]
    return df[keep].reset_index(drop=True)


def _load_gov_exp_latest() -> pd.DataFrame:
    """Latest available COFOG expenditure (% of GDP) per country.

    Returns:
        One row per country with GOV_EXP_COLS and ``gov_exp_year``.
    """
    path = PRECOMPUTED_DIR / 'df_gov_exp.csv'
    if not path.exists():
        return pd.DataFrame(columns=['cntry', 'gov_exp_year'] + GOV_EXP_COLS)
    df = pd.read_csv(path)
    df = df.sort_values('year').groupby('cntry', as_index=False).tail(1)
    df = df.rename(columns={'year': 'gov_exp_year'})
    return df[['cntry', 'gov_exp_year']
              + [c for c in GOV_EXP_COLS if c in df.columns]]


def build_scatter(micro: pd.DataFrame, df_main: pd.DataFrame) -> pd.DataFrame:
    """Country-level cross-section for the Correlations tab (df_scatter).

    X: weighted ESS-derived predictors + newest external macro indicators.
    Y: the same person-centred dimension scores shown everywhere else.

    Args:
        micro: Person-scored microdata.
        df_main: Output of build_country_aggregates().

    Returns:
        One row per ESS11 country.
    """
    df = _build_ess_predictors(micro)
    df = df.merge(_load_external_macro_2023(), on='cntry', how='left')
    df = df.merge(_load_gov_exp_latest(), on='cntry', how='left')
    y_cols = ['cntry'] + list(_DIM_VALUES.keys()) + [f'd_{k}' for k in VALUE_KEYS]
    df = df.merge(df_main[y_cols], on='cntry', how='left')
    df['country_name'] = df['cntry'].map(COUNTRIES)
    df['year'] = ESS_YEAR
    return df.sort_values('cntry').reset_index(drop=True)


# ── Precomputed loaders (server mode) ──────────────────────────────────────────

def _load_precomputed(name: str) -> pd.DataFrame | None:
    """Read a precomputed CSV if present, else None."""
    path = PRECOMPUTED_DIR / f'{name}.csv'
    if path.exists():
        return pd.read_csv(path)
    return None


def load_data() -> pd.DataFrame:
    """Country-level ESS11 Schwartz aggregates (precomputed-first)."""
    cached = _load_precomputed('df_main')
    if cached is not None:
        return cached
    micro = add_person_scores(read_ess11_micro())
    return build_country_aggregates(micro)


def load_scatter_data() -> pd.DataFrame:
    """Country-level correlation dataset (precomputed-first)."""
    cached = _load_precomputed('df_scatter')
    if cached is not None:
        return cached
    micro = add_person_scores(read_ess11_micro())
    return build_scatter(micro, build_country_aggregates(micro))


def load_regional() -> pd.DataFrame:
    """Regional (NUTS) Schwartz aggregates for DE / CH (precomputed-first)."""
    cached = _load_precomputed('df_regional')
    if cached is not None:
        return cached
    micro = add_person_scores(read_ess11_micro())
    return build_regional_aggregates(micro)


def load_gradients() -> pd.DataFrame:
    """Social-gradient aggregates for DE / CH (precomputed-first)."""
    cached = _load_precomputed('df_gradients')
    if cached is not None:
        return cached
    micro = add_person_scores(read_ess11_micro())
    return build_gradients(micro)


def load_regional_indicators() -> pd.DataFrame:
    """Eurostat regional indicators (built by build_regional.py)."""
    df = _load_precomputed('df_regional_indicators')
    return df if df is not None else pd.DataFrame(
        columns=['region', 'indicator', 'value', 'year'])


def load_geojson() -> dict:
    """Trimmed GISCO NUTS GeoJSON for DE NUTS-1 + CH NUTS-2 regions."""
    path = PRECOMPUTED_DIR / 'nuts_regions.geojson'
    if not path.exists():
        return {'type': 'FeatureCollection', 'features': []}
    return json.loads(path.read_text())


def load_mlm_results() -> dict:
    """Precomputed multilevel-model results (built by build_mlm.py)."""
    path = PRECOMPUTED_DIR / 'mlm_results.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_gov_exp() -> pd.DataFrame:
    """Latest COFOG government expenditure per country (for Value Space)."""
    return _load_gov_exp_latest()


# ── Structural indicators (Country Profile sidebar) ────────────────────────────

INDICATOR_META: dict[str, dict] = {
    'ess_trust_mean': {
        'label':   'Social Trust',
        'unit':    'mean 0-10',
        'desc':    'Country mean on "Most people can be trusted or you can\'t be too careful" (ESS variable ppltrst, 0-10, where 10 = most people can be trusted). Most recent ESS round available per country.',
        'source':  'European Social Survey (ESS), most recent available round per country',
        'url':     'https://ess.nsd.no',
        'range':   (1.5, 8.5),
    },
    'ess_religiosity_mean': {
        'label':   'Religiosity',
        'unit':    'mean 0-10',
        'desc':    'Country mean on "How religious are you?" (ESS variable rlgdgr, 0 = not religious at all, 10 = very religious). Most recent ESS round available per country.',
        'source':  'European Social Survey (ESS), most recent available round per country',
        'url':     'https://ess.nsd.no',
        'range':   (1.0, 9.0),
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


def load_indicators() -> tuple[pd.DataFrame, dict]:
    """Load per-country indicator values and contextualising sentences.

    Returns:
        (df_indicators, sentences): df indexed by cntry; sentences keyed
        {cntry: {col: sentence}}.
    """
    ind_path  = PRECOMPUTED_DIR / 'df_indicators.csv'
    sent_path = PRECOMPUTED_DIR / 'indicator_sentences.json'
    df = (pd.read_csv(ind_path).set_index('cntry')
          if ind_path.exists() else pd.DataFrame())
    sentences = json.loads(sent_path.read_text()) if sent_path.exists() else {}
    return df, sentences


# ── Correlation tab metadata ───────────────────────────────────────────────────

_ESS_AGG_NOTE = ('Weighted country mean (ESS analysis weight anweight), '
                 'ESS Round 11 (2023)')

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
    ('v2x_libdem',            'Liberal Democracy',       'V-Dem v15 v2x_libdem (0-1), 2023'),
    ('wb_gini',               'Gini Index',              'World Bank GINI index (0-100), 2023'),
    ('wb_unemployment',       'Unemployment (%)',        'World Bank unemployment rate (% of labour force), 2023'),
    ('wb_gdp_per_capita_ppp', 'GDP per Capita (PPP)',    'World Bank GDP/cap, PPP, constant 2017 int\'l $, 2023'),
    ('gov_exp_health',           'Gov. Health Exp.',            'COFOG GF07: health (% of GDP), latest year'),
    ('gov_exp_education',        'Gov. Education Exp.',         'COFOG GF09: education (% of GDP), latest year'),
    ('gov_exp_social',           'Gov. Social Exp.',            'COFOG GF10: social protection (% of GDP), latest year'),
    ('gov_exp_defence',          'Gov. Defence Exp.',           'COFOG GF02: defence (% of GDP), latest year'),
    ('gov_exp_economic',         'Gov. Economic Exp.',          'COFOG GF04: economic affairs (% of GDP), latest year'),
    ('gov_exp_public_services',  'Gov. Public Services Exp.',   'COFOG GF01: general public services (% of GDP), latest year'),
    ('gov_exp_culture',          'Gov. Culture & Recreation Exp.', 'COFOG GF08: recreation, culture and religion (% of GDP), latest year'),
]

SCATTER_X_DETAIL = {
    'trust_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'ppltrst - "Most people can be trusted, or you can\'t be too careful"',
        'scale':       '0 = can\'t be too careful · 10 = most people can be trusted',
        'aggregation': _ESS_AGG_NOTE,
    },
    'religiosity_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'rlgdgr - "Regardless of whether you belong to a particular religion, how religious are you?"',
        'scale':       '0 = not religious at all · 10 = very religious',
        'aggregation': _ESS_AGG_NOTE,
    },
    'eduyrs_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'eduyrs - Years of full-time education completed',
        'scale':       'Years (continuous); missing codes excluded',
        'aggregation': _ESS_AGG_NOTE,
    },
    'safety_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'aesfdrk - "How safe do you feel walking alone in your local area after dark?"',
        'scale':       '1 = very safe · 4 = very unsafe (lower = safer)',
        'aggregation': _ESS_AGG_NOTE,
    },
    'lrscale_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'lrscale - "In politics people sometimes talk of \'left\' and \'right\'. Where would you place yourself?"',
        'scale':       '0 = left · 10 = right',
        'aggregation': _ESS_AGG_NOTE,
    },
    'age_mean': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'agea - Age of respondent (calculated)',
        'scale':       'Years (continuous)',
        'aggregation': _ESS_AGG_NOTE,
    },
    'urban_pct': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'domicil - "Which phrase on this card best describes the area where you live?"',
        'scale':       '% of respondents in "a big city" or "suburbs / outskirts of big city"',
        'aggregation': _ESS_AGG_NOTE,
    },
    'diversity_pct': {
        'source':      'European Social Survey (ESS), Round 11 (2023)',
        'variable':    'brncntr, facntr, mocntr - born abroad or at least one parent born abroad',
        'scale':       '% of respondents with migration background',
        'aggregation': _ESS_AGG_NOTE,
    },
    'v2x_libdem': {
        'source':      'V-Dem Project, Country-Year Dataset v15 (Coppedge et al., 2024)',
        'variable':    'v2x_libdem - Liberal Democracy Index',
        'scale':       '0-1 (higher = more liberal-democratic); composite of electoral, liberal, and participatory components',
        'aggregation': 'Value for 2023 (newest ESS reference year)',
    },
    'wb_gini': {
        'source':      'World Bank WDI (SI.POV.GINI) · Eurostat EU-SILC for HU',
        'variable':    'SI.POV.GINI - Gini index of equivalised disposable income',
        'scale':       '0-100 (higher = more unequal). Gaps filled with the nearest '
                       'recent survey year (CH, DE, NL) or Eurostat EU-SILC (HU).',
        'aggregation': 'Value for 2023; no imputation - all values from primary sources',
    },
    'wb_unemployment': {
        'source':      'World Bank World Development Indicators (WDI)',
        'variable':    'SL.UEM.TOTL.ZS - Unemployment, total (% of total labour force)',
        'scale':       '% of labour force (ILO modelled estimates)',
        'aggregation': 'Value for 2023',
    },
    'wb_gdp_per_capita_ppp': {
        'source':      'World Bank World Development Indicators (WDI)',
        'variable':    'NY.GDP.PCAP.PP.KD - GDP per capita, PPP (constant 2017 international $)',
        'scale':       'Purchasing-power-parity adjusted, in 2017 USD',
        'aggregation': 'Value for 2023',
    },
    'gov_exp_health': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF07 - Health',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_education': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF09 - Education',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_social': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF10 - Social protection',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_defence': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF02 - Defence',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_economic': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF04 - Economic affairs',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_public_services': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF01 - General public services',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
    'gov_exp_culture': {
        'source':      'Eurostat Government Finance Statistics (COFOG classification)',
        'variable':    'GF08 - Recreation, culture and religion',
        'scale':       '% of GDP (sector S13 general government)',
        'aggregation': 'Most recent available year per country',
    },
}

# (column, display label) - colours come from theme.DIM_COLORS at figure level
SCATTER_Y_META = [
    ('dim_openness',      'Openness to Change'),
    ('dim_transcendence', 'Self-Transcendence'),
    ('dim_conservation',  'Conservation'),
    ('dim_enhancement',   'Self-Enhancement'),
]

# ── Value Space dimension groups ───────────────────────────────────────────────
DIMENSION_GROUPS: dict[str, dict] = {
    'values': {
        'label':        'Value Orientations',
        'desc':         '10 Schwartz basic value Δ-scores (person-centred, weighted '
                        'country means). Captures what people prioritise relative '
                        'to their own response baseline.',
        'cols':         [f'd_{k}' for k in VALUE_KEYS],
        'spoke_labels': ['Self-Dir.', 'Universalism', 'Benevolence', 'Tradition',
                         'Conformity', 'Security', 'Power', 'Achievement',
                         'Hedonism', 'Stimulation'],
        'source':       'df_main',
    },
    'attitudes': {
        'label':        'Social Attitudes',
        'desc':         'Weighted country means of six ESS attitude variables: '
                        'interpersonal trust, religiosity, left-right self-placement, '
                        'perceived safety, urbanisation rate, and mean age.',
        'cols':         ['trust_mean', 'religiosity_mean', 'lrscale_mean',
                         'safety_mean', 'urban_pct', 'age_mean'],
        'spoke_labels': ['Trust', 'Religiosity', 'Left-Right', 'Safety',
                         'Urban %', 'Mean Age'],
        'source':       'df_scatter',
    },
    'economy': {
        'label':        'Economic Structure',
        'desc':         'Five macro-economic indicators: GDP per capita (PPP), '
                        'income inequality (Gini), unemployment rate, migration '
                        'background share, and mean years of education.',
        'cols':         ['wb_gdp_per_capita_ppp', 'wb_gini', 'wb_unemployment',
                         'diversity_pct', 'eduyrs_mean'],
        'spoke_labels': ['GDP/cap', 'Gini', 'Unemployment', 'Migration %', 'Education'],
        'source':       'df_scatter',
    },
    'gov_spending': {
        'label':        'Government Spending',
        'desc':         'Government expenditure by COFOG function as % of GDP: '
                        'health, education, social protection, defence, and economic '
                        'affairs. Source: Eurostat; most recent available year.',
        'cols':         ['gov_exp_health', 'gov_exp_education', 'gov_exp_social',
                         'gov_exp_defence', 'gov_exp_economic'],
        'spoke_labels': ['Health', 'Education', 'Social', 'Defence', 'Economic'],
        'source':       'df_gov_exp',
    },
}

# ── PCA + K-Means with validation ──────────────────────────────────────────────

_DIM_VALUE_IDX = {
    'Openness to Change': ['SD', 'HE', 'ST'],
    'Self-Transcendence': ['UN', 'BE'],
    'Conservation':       ['TR', 'CO', 'SE'],
    'Self-Enhancement':   ['PO', 'AC'],
}


def _pc_axis_label(loading: np.ndarray, avail_cols: list[str],
                   spoke_labels: list[str], is_values_group: bool) -> str:
    """Human-readable label for one principal-component axis."""
    if is_values_group:
        dim_mean = {}
        for dim, keys in _DIM_VALUE_IDX.items():
            idx = [avail_cols.index(f'd_{k}') for k in keys
                   if f'd_{k}' in avail_cols]
            dim_mean[dim] = float(np.mean(loading[idx])) if idx else 0.0
        ordered = sorted(dim_mean.items(), key=lambda kv: kv[1])
        neg_dim, pos_dim = ordered[0][0], ordered[-1][0]
        if abs(dim_mean[pos_dim]) > 0.10 and abs(dim_mean[neg_dim]) > 0.10:
            return f'{pos_dim} ↔ {neg_dim}'
        return 'Mixed'
    top = int(np.argmax(np.abs(loading[:len(avail_cols)])))
    label = spoke_labels[top] if top < len(spoke_labels) else avail_cols[top]
    sign = '+' if loading[top] > 0 else '-'
    return f'{sign}{label} (dominant)'


def compute_k_validation(X: np.ndarray, k_range: range = range(2, 7)) -> dict:
    """Silhouette scores for a range of K-Means cluster counts.

    Args:
        X: Feature matrix used for clustering.
        k_range: Candidate cluster counts.

    Returns:
        {'scores': {k: silhouette}, 'best_k': k with the highest score}.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    scores: dict[int, float] = {}
    for k in k_range:
        if k >= len(X):
            continue
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
        scores[k] = float(silhouette_score(X, labels))
    best_k = max(scores, key=scores.get) if scores else None
    return {'scores': scores, 'best_k': best_k}


def compute_pca_clustering(df: pd.DataFrame, n_clusters: int = 3,
                           dim_group: str = 'values') -> tuple:
    """PCA (2 components) + K-Means for a chosen dimension group (ESS11 data).

    Args:
        df: Source DataFrame (df_main, df_scatter, or df_gov_exp).
        n_clusters: Number of K-Means clusters.
        dim_group: Key into DIMENSION_GROUPS.

    Returns:
        (result_df, explained_variance, pc1_label, pc2_label, validation)
        where validation = {'scores': {k: silhouette}, 'best_k': int,
        'chosen_score': float}; or (None, None, None, None, None) if there
        is insufficient data.
    """
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    group  = DIMENSION_GROUPS[dim_group]
    is_val = dim_group == 'values'

    data = df.copy().reset_index(drop=True)
    if 'country_name' not in data.columns:
        data['country_name'] = data['cntry'].map(COUNTRIES)
    avail_cols = [c for c in group['cols'] if c in data.columns]
    if len(avail_cols) < 2:
        return None, None, None, None, None
    data = data.dropna(subset=avail_cols).reset_index(drop=True)
    if len(data) < 3:
        return None, None, None, None, None

    X_raw = data[avail_cols].values.astype(float)
    # Schwartz Δ-scores share one scale already; other groups need z-scoring
    X = X_raw if is_val else StandardScaler().fit_transform(X_raw)

    pca      = PCA(n_components=2, random_state=42)
    coords   = pca.fit_transform(X)
    k        = min(n_clusters, len(data) - 1)
    km       = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = km.fit_predict(X)

    validation = compute_k_validation(X)
    validation['chosen_score'] = (
        float(silhouette_score(X, clusters)) if k >= 2 else np.nan)

    labels = [_pc_axis_label(l, avail_cols, group.get('spoke_labels', avail_cols),
                             is_val)
              for l in pca.components_]

    result = data[['cntry', 'country_name'] + avail_cols].copy()
    result['pc1'], result['pc2'] = coords[:, 0], coords[:, 1]
    result['cluster'] = clusters
    return (result, pca.explained_variance_ratio_.tolist(),
            labels[0], labels[1], validation)
