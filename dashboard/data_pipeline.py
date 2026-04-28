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
    'BE': 'Belgium',     'CH': 'Switzerland', 'DE': 'Germany',
    'ES': 'Spain',       'FI': 'Finland',     'FR': 'France',
    'HU': 'Hungary',     'IE': 'Ireland',     'NL': 'Netherlands',
    'NO': 'Norway',      'PL': 'Poland',      'PT': 'Portugal',
    'SE': 'Sweden',      'SI': 'Slovenia',
}

COUNTRY_FLAGS = {
    'BE': '🇧🇪', 'CH': '🇨🇭', 'DE': '🇩🇪', 'ES': '🇪🇸',
    'FI': '🇫🇮', 'FR': '🇫🇷', 'HU': '🇭🇺', 'IE': '🇮🇪',
    'NL': '🇳🇱', 'NO': '🇳🇴', 'PL': '🇵🇱', 'PT': '🇵🇹',
    'SE': '🇸🇪', 'SI': '🇸🇮',
}

# V-Dem country names → ISO-2
_VDEM_NAME_TO_ISO2 = {v: k for k, v in COUNTRIES.items()}

# Unemployment xlsx ISO-3 → ISO-2
_UNEMP_ISO3_TO_ISO2 = {
    'BEL': 'BE', 'CHE': 'CH', 'DEU': 'DE', 'ESP': 'ES',
    'FIN': 'FI', 'FRA': 'FR', 'HUN': 'HU', 'IRL': 'IE',
    'NLD': 'NL', 'NOR': 'NO', 'POL': 'PL', 'PRT': 'PT',
    'SWE': 'SE', 'SVN': 'SI',
}

# Gini xlsx country names → ISO-2
_GINI_NAME_TO_ISO2 = {
    'Belgium': 'BE', 'Switzerland': 'CH', 'Germany': 'DE', 'Spain': 'ES',
    'Finland': 'FI', 'France': 'FR', 'Hungary': 'HU', 'Ireland': 'IE',
    'Netherlands': 'NL', 'Norway': 'NO', 'Poland': 'PL', 'Portugal': 'PT',
    'Sweden': 'SE', 'Slovenia': 'SI',
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
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896',
]
COUNTRY_COLORS = {c: _PALETTE[i] for i, c in enumerate(sorted(COUNTRIES.keys()))}

BG_COLOR    = '#f4f6fb'
RADAR_BG    = '#e8edf5'
DELTA_RANGE = [-1.4, 1.75]

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
    ('gov_exp_health',        'Gov. Health Exp.',        'COFOG: health (% of total gov. spending)'),
    ('gov_exp_education',     'Gov. Education Exp.',     'COFOG: education (% of total gov. spending)'),
    ('gov_exp_social',        'Gov. Social Exp.',        'COFOG: social protection (% of total gov. spending)'),
    ('gov_exp_defence',       'Gov. Defence Exp.',       'COFOG: defence (% of total gov. spending)'),
    ('gov_exp_economic',      'Gov. Economic Exp.',      'COFOG: economic affairs (% of total gov. spending)'),
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
        'scale':       '% of total government expenditure',
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

    # Ireland is absent from the source xlsx.
    # Values: Eurostat SILC, net income Gini (already ×100 scale).
    _IE_GINI = {
        2003: 31.1, 2004: 31.8, 2006: 32.4, 2007: 31.3, 2008: 30.7,
        2010: 31.4, 2012: 30.0, 2014: 31.1, 2016: 29.5, 2018: 28.7,
        2020: 27.8, 2022: 27.5, 2023: 26.9,
    }
    _avail_ie = sorted(_IE_GINI.keys())
    for ess_yr in ALL_YEARS:
        closest = min(_avail_ie, key=lambda y: abs(y - ess_yr))
        records.append({'cntry': 'IE', 'year': ess_yr, 'gini': _IE_GINI[closest]})

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

    # Switzerland is absent from the source xlsx (file covers EU states only).
    # Values: OECD harmonized unemployment rate, annual averages.
    _CH_UNEMP = {
        2002: 3.1, 2004: 4.4, 2006: 4.0, 2008: 3.4, 2010: 4.5,
        2012: 4.2, 2014: 4.9, 2016: 4.9, 2018: 4.7, 2020: 5.3, 2023: 4.1,
    }
    for ess_yr in ALL_YEARS:
        if ess_yr in _CH_UNEMP:
            records.append({'cntry': 'CH', 'year': ess_yr,
                            'unemployment_rate': _CH_UNEMP[ess_yr]})

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
    print('[data] Loading ESS aggregated values...')
    df = pd.read_csv(DATA_PATH)
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
    Returns a 150-row DataFrame (14 countries × 11 ESS rounds) with all
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


