"""Rebuild macro_schwartz_analysis_data.csv and ess_schwartz_aggregated.csv
for all 39 ESS countries.

Run from project root:
    python3 scripts/rebuild_full_dataset.py
"""

import csv
import glob
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE     = Path(__file__).parent.parent
ESS_DIR  = BASE / 'data' / 'raw' / 'ess'
MAKRO    = BASE / 'data' / 'raw' / 'makro'
OUT_DIR  = BASE / 'data' / 'merged_datasets'
OUT_DIR.mkdir(exist_ok=True)

ROUND_YEARS = {1:2002, 2:2004, 3:2006, 4:2008, 5:2010,
               6:2012, 7:2014, 8:2016, 9:2018, 10:2020, 11:2023}

ALL_COUNTRIES = [
    'AL','AT','BE','BG','CH','CY','CZ','DE','DK','EE',
    'ES','FI','FR','GB','GR','HR','HU','IE','IL','IS',
    'IT','LT','LU','LV','ME','MK','NL','NO','PL','PT',
    'RO','RS','RU','SE','SI','SK','TR','UA','XK',
]

# WB ISO-3 lookup
_ISO2_TO_ISO3 = {
    'AL':'ALB','AT':'AUT','BE':'BEL','BG':'BGR','CH':'CHE','CY':'CYP',
    'CZ':'CZE','DE':'DEU','DK':'DNK','EE':'EST','ES':'ESP','FI':'FIN',
    'FR':'FRA','GB':'GBR','GR':'GRC','HR':'HRV','HU':'HUN','IE':'IRL',
    'IL':'ISR','IS':'ISL','IT':'ITA','LT':'LTU','LU':'LUX','LV':'LVA',
    'ME':'MNE','MK':'MKD','NL':'NLD','NO':'NOR','PL':'POL','PT':'PRT',
    'RO':'ROU','RS':'SRB','RU':'RUS','SE':'SWE','SI':'SVN','SK':'SVK',
    'TR':'TUR','UA':'UKR','XK':'XKX',
}

# ESS variables to aggregate as country-round means
MISS_GENERIC = {77, 88, 99}
MISS_SMALL   = {7, 8, 9}

# PVQ-21 items (scale 1-6, missing 7/8/9)
PVQ_ITEMS = [
    'ipcrtiv','ipadvnt','ipgdtim','iphlppl','ipeqopt','ipudrst',
    'iplylfr','ipmodst','ipbhprp','ipfrule','ipshabt','ipsuces',
    'iprspot','ipstrgv',
]

# Social variables: (col, max_valid)
SOCIAL_VARS = {
    'trust_mean':       ('ppltrst',  10),
    'religiosity_mean': ('rlgdgr',   10),
    'eduyrs_mean':      ('eduyrs',   30),
    'safety_mean':      ('aesfdrk',   4),
    'lrscale_mean':     ('lrscale',  10),
    'age_mean':         ('agea',     99),
    'urban_pct':        ('domicil',   5),   # 1-2 = urban/suburban → share computed below
    'diversity_pct':    None,               # computed from brncntr/facntr/mocntr
}


# ── Step 1: Aggregate ESS (PVQ + social) ─────────────────────────────────────

print('Step 1: Aggregating ESS raw data for all 39 countries...')

pvq_agg   = defaultdict(lambda: defaultdict(list))   # (cntry,year) -> {col: [vals]}
soc_agg   = defaultdict(lambda: defaultdict(list))
urban_agg = defaultdict(list)
migr_agg  = defaultdict(list)

for r in range(1, 12):
    csvs = glob.glob(str(ESS_DIR / f'ESS{r}' / '*.csv'))
    if not csvs:
        print(f'  ESS{r}: no CSV found')
        continue
    year = ROUND_YEARS[r]

    header_df = pd.read_csv(csvs[0], nrows=0)
    header_df.columns = header_df.columns.str.lower()
    avail = set(header_df.columns)

    # PVQ items may have 'a'/'b' suffix in some ESS rounds (e.g. 'ipcrtiva' in ESS11)
    def norm_pvq(col):
        if col.startswith('ip') and len(col) > 5 and col[-1] in ('a', 'b'):
            return col[:-1]
        return col

    pvq_col_map = {}  # actual_col -> normalized_name
    for col in avail:
        norm = norm_pvq(col)
        if norm in PVQ_ITEMS:
            pvq_col_map[col] = norm

    needed = ['cntry', 'essround'] + list(pvq_col_map.keys()) + \
             [spec[0] for spec in SOCIAL_VARS.values() if spec is not None] + \
             ['brncntr', 'facntr', 'mocntr']
    usecols = [c for c in needed if c in avail]

    df = pd.read_csv(csvs[0], usecols=usecols, low_memory=False)
    df.columns = df.columns.str.lower()
    # Normalize PVQ column names (remove 'a'/'b' suffix)
    df.rename(columns={k: v for k, v in pvq_col_map.items() if k in df.columns}, inplace=True)
    df = df[df['cntry'].str.upper().isin(ALL_COUNTRIES)].copy()
    df['cntry'] = df['cntry'].str.upper()

    # PVQ-21
    for col in PVQ_ITEMS:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors='coerce')
        s = s.where((s >= 1) & (s <= 6))
        for cntry, grp in df.groupby('cntry'):
            vals = s[grp.index].dropna().tolist()
            if vals:
                pvq_agg[(cntry, year)][col].extend(vals)

    # Social variables
    for out_col, spec in SOCIAL_VARS.items():
        if spec is None:
            continue
        src_col, max_v = spec
        if src_col not in df.columns:
            continue
        s = pd.to_numeric(df[src_col], errors='coerce')
        s = s.where(s <= max_v)
        for cntry, grp in df.groupby('cntry'):
            vals = s[grp.index].dropna()
            if out_col == 'urban_pct':
                # domicil 1=big city, 2=suburbs → urban if <=2
                urban = (vals <= 2).mean() * 100 if len(vals) else np.nan
                urban_agg[(cntry, year)].append(urban)
            else:
                mean_v = vals.mean() if len(vals) else np.nan
                soc_agg[(cntry, year)][out_col].append(mean_v)

    # Migration background
    for col in ['brncntr', 'facntr', 'mocntr']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].where(df[col].isin([1, 2]))
    if all(c in df.columns for c in ['brncntr','facntr','mocntr']):
        migrant = (df[['brncntr','facntr','mocntr']] == 2).any(axis=1)
        for cntry, grp in df.groupby('cntry'):
            pct = migrant[grp.index].mean() * 100
            migr_agg[(cntry, year)].append(pct)

    print(f'  ESS{r} ({year}): {df["cntry"].nunique()} countries, {len(df):,} rows')

# Build ESS aggregated table (PVQ medians + means)
print('\nBuilding ess_schwartz_aggregated.csv...')
records = []
for (cntry, year), pvq_data in sorted(pvq_agg.items()):
    row = {'cntry': cntry, 'year': year}
    for col in PVQ_ITEMS:
        vals = pvq_data.get(col, [])
        row[f'{col}_mean']   = round(float(np.mean(vals)), 4)   if vals else None
        row[f'{col}_median'] = round(float(np.median(vals)), 4) if vals else None
    records.append(row)

ess_agg = pd.DataFrame(records)
ess_path = ESS_DIR / 'ess_schwartz_aggregated.csv'
ess_agg.to_csv(ess_path, index=False)
print(f'  -> {ess_path}  ({len(ess_agg)} rows, {ess_agg["cntry"].nunique()} countries)')

# Build social aggregates
social_records = {}
for (cntry, year), soc_data in soc_agg.items():
    row = social_records.setdefault((cntry, year), {'cntry': cntry, 'year': year})
    for col, vals in soc_data.items():
        row[col] = round(float(np.nanmean(vals)), 4) if vals else None
for (cntry, year), vals in urban_agg.items():
    social_records.setdefault((cntry, year), {'cntry': cntry, 'year': year})
    social_records[(cntry, year)]['urban_pct'] = round(float(np.nanmean(vals)), 4)
for (cntry, year), vals in migr_agg.items():
    social_records.setdefault((cntry, year), {'cntry': cntry, 'year': year})
    social_records[(cntry, year)]['diversity_pct'] = round(float(np.nanmean(vals)), 4)

social_df = pd.DataFrame(list(social_records.values()))


# ── Step 2: V-Dem ─────────────────────────────────────────────────────────────

print('\nStep 2: V-Dem...')
vdem_iso3 = set(_ISO2_TO_ISO3.values())
vdem = pd.read_csv(MAKRO / 'V-Dem-CY-FullOthers-v15_csv' / 'V-Dem-CY-Full+Others-v15.csv',
                   usecols=['country_text_id', 'year', 'v2x_libdem'],
                   low_memory=False)
vdem = vdem[vdem['country_text_id'].isin(vdem_iso3) &
            vdem['year'].isin(ROUND_YEARS.values())].copy()
iso3_to_iso2 = {v: k for k, v in _ISO2_TO_ISO3.items()}
vdem['cntry'] = vdem['country_text_id'].map(iso3_to_iso2)
vdem = vdem.dropna(subset=['cntry'])[['cntry', 'year', 'v2x_libdem']]
print(f'  V-Dem: {vdem["cntry"].nunique()} countries')


# ── Step 3: World Bank (existing file + API for new countries) ────────────────

print('\nStep 3: World Bank data...')
wb_existing = pd.read_csv(MAKRO / 'worldbank_data.csv')
existing_cntrys = set(wb_existing['cntry'].unique())
new_cntrys = [c for c in ALL_COUNTRIES if c not in existing_cntrys]
print(f'  Existing: {len(existing_cntrys)} countries. Fetching {len(new_cntrys)} new: {new_cntrys}')

WB_INDICATORS = {
    'wb_gdp_per_capita_ppp': 'NY.GDP.PCAP.PP.KD',
    'wb_gini':               'SI.POV.GINI',
    'wb_unemployment':       'SL.UEM.TOTL.ZS',
}

def fetch_wb(iso3_list, indicator):
    iso3_str = ';'.join(iso3_list)
    url = (f'https://api.worldbank.org/v2/country/{iso3_str}/indicator/{indicator}'
           f'?format=json&date=2000:2024&per_page=1000')
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        if len(data) < 2 or not data[1]:
            return {}
        results = {}
        for entry in data[1]:
            if entry['value'] is None:
                continue
            iso3 = entry['countryiso3code']
            yr   = int(entry['date'])
            results[(iso3, yr)] = float(entry['value'])
        return results
    except Exception as e:
        print(f'  WB API error ({indicator}): {e}')
        return {}

new_wb_records = defaultdict(dict)
if new_cntrys:
    iso3_new = [_ISO2_TO_ISO3[c] for c in new_cntrys if c in _ISO2_TO_ISO3]
    for col, indicator in WB_INDICATORS.items():
        print(f'  Fetching {indicator}...')
        data = fetch_wb(iso3_new, indicator)
        for (iso3, yr), val in data.items():
            iso2 = iso3_to_iso2.get(iso3)
            if iso2:
                new_wb_records[(iso2, yr)][col] = val
        time.sleep(0.5)

# Match WB values to ESS reference years (nearest available year per country)
def match_wb_to_ess(records_dict, ess_years):
    """For each country, find nearest available WB year for each ESS round year."""
    by_country = defaultdict(dict)  # cntry -> {ess_year: {col: val}}
    for (cntry, yr), cols in records_dict.items():
        by_country[cntry][yr] = cols

    rows = []
    for cntry, yr_data in by_country.items():
        avail_years = sorted(yr_data.keys())
        for ess_yr in ess_years:
            nearest = min(avail_years, key=lambda y: abs(y - ess_yr))
            if abs(nearest - ess_yr) <= 4:   # accept within 4 years
                row = {'cntry': cntry, 'year': ess_yr}
                row.update(yr_data[nearest])
                rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

new_wb_df = match_wb_to_ess(new_wb_records, list(ROUND_YEARS.values()))
wb_all = pd.concat([wb_existing, new_wb_df], ignore_index=True).drop_duplicates(
    subset=['cntry', 'year'], keep='first')
print(f'  WB combined: {wb_all["cntry"].nunique()} countries')


# ── Step 4: COFOG ─────────────────────────────────────────────────────────────

print('\nStep 4: COFOG government expenditure...')
# Re-use extract_cofog_final.py logic inline
import zipfile, xml.etree.ElementTree as ET

COFOG_PATH = MAKRO / 'gov_10a_exp__custom_20250909_spreadsheet.xlsx'

# The file has one sheet per country. Parse workbook to get sheet names.
cofog_records = []
try:
    with zipfile.ZipFile(COFOG_PATH) as z:
        # Read workbook for sheet names
        with z.open('xl/workbook.xml') as f:
            wb_tree = ET.parse(f)
        wb_ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheets_xml = wb_tree.findall('.//ns:sheet', wb_ns)
        sheet_names = {s.get('sheetId'): s.get('name') for s in sheets_xml}

        with z.open('xl/sharedStrings.xml') as f:
            ss_tree = ET.parse(f)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings = [''.join(n.text or '' for n in si.findall('.//ns:t', ns))
                   for si in ss_tree.findall('.//ns:si', ns)]

        print(f'  COFOG has {len(sheet_names)} sheets: {list(sheet_names.values())[:5]}...')

        # Country name to ISO-2 mapping for COFOG
        cofog_name_map = {
            'Austria': 'AT', 'Belgium': 'BE', 'Bulgaria': 'BG',
            'Croatia': 'HR', 'Cyprus': 'CY', 'Czech Republic': 'CZ', 'Czechia': 'CZ',
            'Denmark': 'DK', 'Estonia': 'EE', 'Finland': 'FI', 'France': 'FR',
            'Germany': 'DE', 'Greece': 'GR', 'Hungary': 'HU', 'Iceland': 'IS',
            'Ireland': 'IE', 'Italy': 'IT', 'Latvia': 'LV', 'Lithuania': 'LT',
            'Luxembourg': 'LU', 'Malta': 'MT', 'Montenegro': 'ME',
            'Netherlands': 'NL', 'North Macedonia': 'MK', 'Norway': 'NO',
            'Poland': 'PL', 'Portugal': 'PT', 'Romania': 'RO', 'Serbia': 'RS',
            'Slovakia': 'SK', 'Slovenia': 'SI', 'Spain': 'ES', 'Sweden': 'SE',
            'Switzerland': 'CH', 'Turkiye': 'TR', 'Turkey': 'TR',
            'United Kingdom': 'GB', 'Albania': 'AL', 'Kosovo': 'XK',
            'Ukraine': 'UA', 'Israel': 'IL',
        }

        COFOG_FUNCS = {
            'GF01': 'gov_exp_public_services',
            'GF02': 'gov_exp_defence',
            'GF03': 'gov_exp_public_order',
            'GF04': 'gov_exp_economic',
            'GF05': 'gov_exp_environment',
            'GF06': 'gov_exp_housing',
            'GF07': 'gov_exp_health',
            'GF08': 'gov_exp_culture',
            'GF09': 'gov_exp_education',
            'GF10': 'gov_exp_social',
            'GF00': 'gov_exp_total',
        }

        for sheet_id, sheet_name in sheet_names.items():
            cntry = cofog_name_map.get(sheet_name)
            if not cntry:
                continue
            sheet_file = f'xl/worksheets/sheet{sheet_id}.xml'
            if sheet_file not in z.namelist():
                # try without leading zeros
                continue
            try:
                with z.open(sheet_file) as f:
                    ws_tree = ET.parse(f)
            except Exception:
                continue

            rows_xml = ws_tree.findall('.//ns:row', ns)
            if not rows_xml:
                continue

            def get_row(row_el):
                cells = []
                for cell in row_el.findall('ns:c', ns):
                    v = cell.find('ns:v', ns)
                    t = cell.get('t', '')
                    if v is not None:
                        cells.append(strings[int(v.text)] if t == 's' else v.text)
                    else:
                        cells.append('')
                return cells

            all_rows = [get_row(r) for r in rows_xml]
            # Find year header row
            year_row_idx = None
            year_cols = {}
            for i, row in enumerate(all_rows):
                for j, val in enumerate(row):
                    if val and str(val).strip().isdigit() and 2000 <= int(str(val).strip()) <= 2025:
                        year_cols[j] = int(str(val).strip())
                if len(year_cols) >= 5:
                    year_row_idx = i
                    break

            if not year_cols:
                continue

            # Parse data rows: look for COFOG function codes
            for row in all_rows[year_row_idx + 1:]:
                if not row:
                    continue
                row_str = ' '.join(str(v) for v in row[:3])
                matched_func = None
                for code, col_name in COFOG_FUNCS.items():
                    if code in row_str:
                        matched_func = col_name
                        break
                if not matched_func:
                    continue
                for col_j, yr in year_cols.items():
                    if yr not in ROUND_YEARS.values():
                        continue
                    if col_j < len(row) and row[col_j]:
                        try:
                            val = float(str(row[col_j]).replace(',', '.'))
                            cofog_records.append({
                                'cntry': cntry, 'year': yr,
                                matched_func: val,
                            })
                        except ValueError:
                            pass

    if cofog_records:
        cofog_df = pd.DataFrame(cofog_records)
        cofog_df = cofog_df.groupby(['cntry', 'year']).first().reset_index()
        print(f'  COFOG: {cofog_df["cntry"].nunique()} countries')
    else:
        print('  COFOG: no data parsed, skipping')
        cofog_df = pd.DataFrame(columns=['cntry', 'year'])

except Exception as e:
    print(f'  COFOG parse error: {e}')
    cofog_df = pd.DataFrame(columns=['cntry', 'year'])


# ── Step 5: Merge everything ──────────────────────────────────────────────────

print('\nStep 5: Merging all datasets...')

# Base: ESS aggregated (PVQ-21)
base = ess_agg.copy()

# Merge social vars
base = base.merge(social_df, on=['cntry', 'year'], how='left')

# Merge V-Dem
base = base.merge(vdem, on=['cntry', 'year'], how='left')

# Merge WB
base = base.merge(wb_all, on=['cntry', 'year'], how='left')

# Merge COFOG
if not cofog_df.empty and len(cofog_df.columns) > 2:
    base = base.merge(cofog_df, on=['cntry', 'year'], how='left')

# Reorder columns sensibly
id_cols   = ['cntry', 'year']
vdem_cols = ['v2x_libdem']
wb_cols   = [c for c in ['wb_gdp_per_capita_ppp','wb_gini','wb_unemployment'] if c in base.columns]
soc_cols  = [c for c in ['diversity_pct','eduyrs_mean','religiosity_mean','trust_mean',
                          'lrscale_mean','urban_pct','age_mean','safety_mean'] if c in base.columns]
gov_cols  = sorted([c for c in base.columns if c.startswith('gov_exp_')])
pvq_cols  = sorted([c for c in base.columns if c.startswith('ip')])

ordered = id_cols + vdem_cols + wb_cols + soc_cols + gov_cols + pvq_cols
ordered = [c for c in ordered if c in base.columns]
base = base[ordered]

out_path = OUT_DIR / 'macro_schwartz_analysis_data.csv'
base.to_csv(out_path, index=False)

print(f'\nDone.')
print(f'  ess_schwartz_aggregated.csv : {len(ess_agg)} rows, {ess_agg["cntry"].nunique()} countries')
print(f'  macro_schwartz_analysis_data.csv : {len(base)} rows, {base["cntry"].nunique()} countries')
print(f'  Columns: {len(base.columns)}')
print(f'  Countries: {sorted(base["cntry"].unique())}')

# Coverage check
print('\nNaN summary per macro column (rows with missing / total):')
for col in vdem_cols + wb_cols + soc_cols + gov_cols[:3]:
    if col in base.columns:
        n_nan = base[col].isna().sum()
        print(f'  {col:<35}: {n_nan}/{len(base)} NaN')
