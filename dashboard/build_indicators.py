"""
Build script for country-level sociological indicators.

Run once locally:
    cd /path/to/project
    python3 dashboard/build_indicators.py

Writes:
    data/raw/indicators/{indicator}.csv     -- raw source data (cached locally)
    dashboard/precomputed/df_indicators.csv -- final merged table (committed)

Idempotent: re-running overwrites outputs but re-uses cached raw files.
Retrieved: 2025-04-29
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s",
                    stream=sys.stdout)
log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
RAW_IND   = ROOT / "data" / "raw" / "indicators"
PRECOMP   = Path(__file__).parent / "precomputed"
ESS_DIR   = ROOT / "data" / "raw" / "ess"
VDEM_CSV  = ROOT / "data" / "raw" / "makro" / "V-Dem-CY-FullOthers-v15_csv" \
            / "V-Dem-CY-Full+Others-v15.csv"
RAW_IND.mkdir(parents=True, exist_ok=True)
PRECOMP.mkdir(parents=True, exist_ok=True)

COUNTRIES: list[str] = [
    "AL","AT","BE","BG","CH","CY","CZ","DE","DK","EE",
    "ES","FI","FR","GB","GR","HR","HU","IE","IL","IS",
    "IT","LT","LU","LV","ME","MK","NL","NO","PL","PT",
    "RO","RS","RU","SE","SI","SK","TR","UA","XK",
]
RETRIEVAL_DATE = "2025-04-29"

# ESS round-year mapping (all available)
ROUND_TO_YEAR = {1:2002,2:2004,3:2006,4:2008,5:2010,
                 6:2012,7:2014,8:2016,9:2018,10:2020,11:2023}

# Country-name → ISO-2 for sources that use names
WHR_NAMES: dict[str,str] = {
    "Albania":"AL","Austria":"AT","Belgium":"BE","Bulgaria":"BG",
    "Switzerland":"CH","Cyprus":"CY","Czech Republic":"CZ","Czechia":"CZ",
    "Germany":"DE","Denmark":"DK","Estonia":"EE","Spain":"ES","Finland":"FI",
    "France":"FR","United Kingdom":"GB","United Kingdom*":"GB",
    "Greece":"GR","Croatia":"HR","Hungary":"HU","Ireland":"IE",
    "Israel":"IL","Iceland":"IS","Italy":"IT","Lithuania":"LT",
    "Luxembourg":"LU","Latvia":"LV","Montenegro":"ME","North Macedonia":"MK",
    "Netherlands":"NL","Norway":"NO","Poland":"PL","Portugal":"PT",
    "Romania":"RO","Serbia":"RS","Russia":"RU","Russian Federation":"RU",
    "Sweden":"SE","Slovenia":"SI","Slovakia":"SK",
    "Turkiye":"TR","Turkey":"TR","Ukraine":"UA","Kosovo":"XK",
}
VDEM_NAMES: dict[str,str] = {
    "Albania":"AL","Austria":"AT","Belgium":"BE","Bulgaria":"BG",
    "Switzerland":"CH","Cyprus":"CY","Czechia":"CZ","Germany":"DE",
    "Denmark":"DK","Estonia":"EE","Spain":"ES","Finland":"FI","France":"FR",
    "United Kingdom":"GB","Greece":"GR","Croatia":"HR","Hungary":"HU",
    "Ireland":"IE","Israel":"IL","Iceland":"IS","Italy":"IT",
    "Lithuania":"LT","Luxembourg":"LU","Latvia":"LV","Montenegro":"ME",
    "North Macedonia":"MK","Netherlands":"NL","Norway":"NO","Poland":"PL",
    "Portugal":"PT","Romania":"RO","Serbia":"RS","Russia":"RU",
    "Sweden":"SE","Slovenia":"SI","Slovakia":"SK","Türkiye":"TR",
    "Ukraine":"UA","Kosovo":"XK",
}
ISO3_TO_ISO2: dict[str,str] = {
    "ALB":"AL","AUT":"AT","BEL":"BE","BGR":"BG","CHE":"CH","CYP":"CY",
    "CZE":"CZ","DEU":"DE","DNK":"DK","EST":"EE","ESP":"ES","FIN":"FI",
    "FRA":"FR","GBR":"GB","GRC":"GR","HRV":"HR","HUN":"HU","IRL":"IE",
    "ISR":"IL","ISL":"IS","ITA":"IT","LTU":"LT","LUX":"LU","LVA":"LV",
    "MNE":"ME","MKD":"MK","NLD":"NL","NOR":"NO","POL":"PL","PRT":"PT",
    "ROU":"RO","SRB":"RS","RUS":"RU","SWE":"SE","SVN":"SI","SVK":"SK",
    "TUR":"TR","UKR":"UA","XKX":"XK",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty(name: str) -> pd.Series:
    return pd.Series(np.nan, index=COUNTRIES, name=name)

def _empty2(col: str) -> tuple[pd.Series, pd.Series]:
    return _empty(col), _empty(col + "_year")

def _download(url: str, dest: Path, *, timeout: int = 60) -> Path:
    if dest.exists():
        log.info("  cached → %s", dest.name); return dest
    log.info("  downloading %s", url)
    r = requests.get(url, timeout=timeout,
                     headers={"User-Agent": "human-values-dashboard/1.0"})
    r.raise_for_status()
    dest.write_bytes(r.content)
    log.info("  saved %s (%d KB)", dest.name, len(r.content)//1024)
    return dest

def _find_geo(id_vars: list[str]) -> str | None:
    """Find the Eurostat geo column (e.g. 'geo\\TIME_PERIOD')."""
    for c in id_vars:
        if c.lower().startswith("geo"):
            return c
    return None

def _melt_eurostat(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Melt Eurostat wide format; return (melted, geo_col)."""
    df.columns = df.columns.str.strip()
    year_cols = [c for c in df.columns if str(c).isdigit() and 2000 <= int(c) <= 2030]
    id_vars   = [c for c in df.columns if c not in year_cols]
    melted = df.melt(id_vars=id_vars, value_vars=year_cols,
                     var_name="year", value_name="_val")
    melted["year"] = melted["year"].astype(int)
    melted["_val"] = pd.to_numeric(melted["_val"], errors="coerce")
    melted = melted.dropna(subset=["_val"])
    geo_col = _find_geo(id_vars)
    return melted, geo_col

_ESTAT_CODE_REMAP: dict[str, str] = {
    "EL": "GR",   # Eurostat uses EL for Greece (ISO-2 is GR)
    "UK": "GB",   # Eurostat uses UK for United Kingdom (ISO-2 is GB)
}


_ESTAT_MAX_YEAR = 2023   # cap at last fully published year; 2024/2025 are provisional


def _latest_per_country(melted: pd.DataFrame, geo_col: str,
                        val_col: str, countries: list[str],
                        decimals: int = 1) -> tuple[pd.Series, pd.Series]:
    # Remap Eurostat non-ISO codes and cap at final published year
    melted = melted.copy()
    melted[geo_col] = melted[geo_col].replace(_ESTAT_CODE_REMAP)
    melted = melted[melted["year"] <= _ESTAT_MAX_YEAR]
    records: dict[str, tuple[float,int]] = {}
    for c in countries:
        sub = melted[melted[geo_col] == c].sort_values("year", ascending=False)
        if not sub.empty:
            row = sub.iloc[0]
            records[c] = (round(float(row["_val"]), decimals), int(row["year"]))
    values = pd.Series({k: v[0] for k,v in records.items()},
                       name=val_col).reindex(countries)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name=val_col+"_year").reindex(countries)
    return values, years

def _validate(values: pd.Series, lo: float, hi: float,
              years: pd.Series | None = None) -> None:
    col = values.name
    n   = values.notna().sum()
    missing = [c for c in COUNTRIES if pd.isna(values.get(c))]
    log.info("[%s]  %d/39  |  missing: %s", col, n,
             ", ".join(missing) if missing else "none")
    valid = values.dropna()
    if len(valid):
        bad = valid[(valid < lo) | (valid > hi)]
        if len(bad):
            log.warning("[%s]  OUT-OF-RANGE: %s", col, bad.to_dict())
        else:
            log.info("[%s]  range OK (%.2f–%.2f)  median %.2f",
                     col, valid.min(), valid.max(), valid.median())
    if years is not None:
        yrs = sorted(years.dropna().astype(int).unique())
        log.info("[%s]  ref years: %s", col, yrs)


# ── 1 & 2: ESS Social Trust and Religiosity (weighted mean, most recent round) ─
# Using the mean (0-10) rather than a % threshold: more informative, consistent
# with the Correlations tab, and avoids an arbitrary cut-off at 6.

def build_ess_mean(scatter_col: str, col_out: str,
                   val_range: tuple[float,float]) -> tuple[pd.Series, pd.Series]:
    """Read from df_scatter (all 39 countries, most recent ESS round each)."""
    log.info("=== %s from df_scatter (most recent round per country) ===", col_out)
    cache = PRECOMP / "df_scatter.csv"
    if not cache.exists():
        log.error("[%s]  df_scatter.csv not found", col_out)
        return _empty(col_out), _empty(col_out + "_year")
    df = pd.read_csv(cache)
    if scatter_col not in df.columns:
        log.error("[%s]  column %s not in df_scatter", col_out, scatter_col)
        return _empty(col_out), _empty(col_out + "_year")
    df = df[["cntry", "year", scatter_col]].dropna()
    df = df.sort_values("year", ascending=False)
    latest = df.groupby("cntry").first().reset_index()
    values = pd.Series(
        latest.set_index("cntry")[scatter_col].round(2).to_dict(),
        name=col_out,
    ).reindex(COUNTRIES)
    years = pd.Series(
        latest.set_index("cntry")["year"].to_dict(),
        name=col_out + "_year",
    ).reindex(COUNTRIES)
    _validate(values, val_range[0], val_range[1], years)
    return values, years


# ── 3: Gini (Eurostat ilc_di12) ───────────────────────────────────────────────

def build_estat_gini() -> tuple[pd.Series, pd.Series]:
    log.info("=== estat_gini (Eurostat ilc_di12) ===")
    import eurostat
    cache = RAW_IND / "estat_ilc_di12.csv"
    if not cache.exists():
        df = eurostat.get_data_df("ilc_di12", flags=False); df.to_csv(cache, index=False)
    df = pd.read_csv(cache)
    melted, geo_col = _melt_eurostat(df)
    if geo_col is None:
        log.error("[estat_gini] geo column not found"); return _empty2("estat_gini")
    # Filter: total income quintile if present
    for dim, val in [("indic_il","GINI"), ("sex","T"), ("age","TOTAL")]:
        if dim in melted.columns:
            sub = melted[melted[dim] == val]
            if not sub.empty: melted = sub
    # Exclude aggregate regions
    melted = melted[melted[geo_col].str.len() == 2]
    values, years = _latest_per_country(melted, geo_col, "estat_gini", COUNTRIES)
    _validate(values, 20, 50, years)
    return values, years


# ── 4: GDP per Capita PPS EU27=100 (Eurostat tec00114) ───────────────────────

def build_estat_gdp_pps() -> tuple[pd.Series, pd.Series]:
    log.info("=== estat_gdp_pps (Eurostat tec00114) ===")
    import eurostat
    cache = RAW_IND / "estat_tec00114.csv"
    if not cache.exists():
        df = eurostat.get_data_df("tec00114", flags=False); df.to_csv(cache, index=False)
    df = pd.read_csv(cache)
    melted, geo_col = _melt_eurostat(df)
    if geo_col is None:
        log.error("[estat_gdp_pps] geo column not found"); return _empty2("estat_gdp_pps")
    # Filter: PPS per capita (EU27_2020=100)
    for dim, val in [("na_item","VI_PPS_EU27_2020_HAB"), ("unit","PPS_EU27_2020_HAB")]:
        if dim in melted.columns:
            sub = melted[melted[dim] == val]
            if not sub.empty: melted = sub
    melted = melted[melted[geo_col].str.len() == 2]
    # Exclude candidate/projection years > 2024
    melted = melted[melted["year"] <= 2024]
    values, years = _latest_per_country(melted, geo_col, "estat_gdp_pps", COUNTRIES, 0)
    _validate(values, 20, 300, years)
    return values, years


# ── 5: Tertiary Attainment 25–34 (Eurostat edat_lfse_03) ─────────────────────

def build_estat_tertiary() -> tuple[pd.Series, pd.Series]:
    log.info("=== estat_tertiary_pct (Eurostat edat_lfse_03) ===")
    import eurostat
    cache = RAW_IND / "estat_edat_lfse_03.csv"
    if not cache.exists():
        df = eurostat.get_data_df("edat_lfse_03", flags=False); df.to_csv(cache, index=False)
    df = pd.read_csv(cache)
    melted, geo_col = _melt_eurostat(df)
    if geo_col is None:
        log.error("[estat_tertiary] geo column not found"); return _empty2("estat_tertiary_pct")
    for dim, val in [("sex","T"), ("age","Y25-34"), ("isced11","ED5-8")]:
        if dim in melted.columns:
            sub = melted[melted[dim] == val]
            if not sub.empty: melted = sub
    melted = melted[melted[geo_col].str.len() == 2]
    melted = melted[melted["year"] <= 2024]
    values, years = _latest_per_country(melted, geo_col, "estat_tertiary_pct", COUNTRIES)
    _validate(values, 15, 80, years)
    return values, years


# ── 6: Healthy Life Years (Eurostat hlth_hlye) ───────────────────────────────

def build_estat_hly() -> tuple[pd.Series, pd.Series]:
    log.info("=== estat_hly (Eurostat hlth_hlye) ===")
    import eurostat
    cache = RAW_IND / "estat_hlth_hlye.csv"
    if not cache.exists():
        df = eurostat.get_data_df("hlth_hlye", flags=False); df.to_csv(cache, index=False)
    df = pd.read_csv(cache)
    melted, geo_col = _melt_eurostat(df)
    if geo_col is None:
        log.error("[estat_hly] geo column not found"); return _empty2("estat_hly")
    for dim, val in [("sex","T"), ("indic_he","HLY_0"), ("unit","YR")]:
        if dim in melted.columns:
            sub = melted[melted[dim] == val]
            if not sub.empty: melted = sub
    melted = melted[melted[geo_col].str.len() == 2]
    values, years = _latest_per_country(melted, geo_col, "estat_hly", COUNTRIES)
    _validate(values, 50, 85, years)
    return values, years


# ── 7: Gender Equality Index (EIGE 2023 edition, data year 2021) ─────────────

def build_eige_gei() -> tuple[pd.Series, pd.Series]:
    log.info("=== eige_gei (EIGE Gender Equality Index 2023) ===")
    # EIGE does not publish a stable machine-readable API endpoint.
    # Values from the official EIGE 2023 publication (released Nov 2023),
    # covering reference year 2021.
    # Source: https://eige.europa.eu/gender-equality-index/2023
    # Non-EU countries are explicitly excluded from EIGE scope.
    gei: dict[str, float] = {
        "AT":68.3,"BE":74.0,"BG":55.9,"CY":62.8,"CZ":56.5,
        "DE":68.7,"DK":77.4,"EE":61.9,"ES":74.0,"FI":75.5,
        "FR":75.1,"GR":54.5,"HR":57.0,"HU":53.7,"IE":71.5,
        "IT":65.0,"LT":59.5,"LU":72.8,"LV":60.1,
        "NL":74.9,"PL":57.4,"PT":63.9,"RO":54.5,
        "SE":83.9,"SI":68.2,"SK":56.2,
    }
    # EU accession 2013+ / Brexit / EEA / non-EU: not in EIGE scope
    nan_reason = {
        "AL":"Candidate country — outside EIGE scope",
        "CH":"EEA non-EU — outside EIGE scope",
        "GB":"Left EU 2020 — outside EIGE scope",
        "IL":"Non-EU — outside EIGE scope",
        "IS":"EEA non-EU — outside EIGE scope",
        "ME":"Candidate — outside EIGE scope",
        "MK":"Candidate — outside EIGE scope",
        "NO":"EEA non-EU — outside EIGE scope",
        "RS":"Candidate — outside EIGE scope",
        "RU":"Non-EU — outside EIGE scope",
        "TR":"Candidate (frozen) — outside EIGE scope",
        "UA":"Candidate — outside EIGE scope",
        "XK":"Non-EU — outside EIGE scope",
    }
    for c, reason in nan_reason.items():
        log.debug("[eige_gei]  %s: NaN — %s", c, reason)
    values = pd.Series({c: gei.get(c, np.nan) for c in COUNTRIES}, name="eige_gei")
    years  = pd.Series({c: 2021 if not pd.isna(values[c]) else np.nan
                        for c in COUNTRIES}, name="eige_gei_year")
    _validate(values, 45, 90, years)
    return values, years


# ── 8: CPI (OWID mirror of Transparency International) ───────────────────────

def build_ti_cpi() -> tuple[pd.Series, pd.Series]:
    log.info("=== ti_cpi (TI CPI via Our World in Data mirror) ===")
    cache = RAW_IND / "owid_cpi.csv"
    url   = "https://ourworldindata.org/grapher/ti-corruption-perception-index.csv"
    try:
        _download(url, cache)
        df = pd.read_csv(cache)
    except Exception as e:
        log.error("[ti_cpi]  download failed: %s", e); return _empty2("ti_cpi")

    df.columns = df.columns.str.strip()
    code_col  = next((c for c in df.columns if c.lower() == "code"), None)
    score_col = next((c for c in df.columns
                      if "corruption" in c.lower() or "cpi" in c.lower()), None)
    year_col  = next((c for c in df.columns if c.lower() == "year"), None)

    if not all([code_col, score_col, year_col]):
        log.error("[ti_cpi]  columns not recognised: %s", list(df.columns))
        return _empty2("ti_cpi")

    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df[year_col]  = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[score_col, year_col])

    records: dict[str, tuple[float,int]] = {}
    for _, row in df.iterrows():
        iso3 = str(row[code_col]).strip().upper()
        iso2 = ISO3_TO_ISO2.get(iso3) or (iso3 if len(iso3)==2 else None)
        if iso2 not in COUNTRIES: continue
        yr = int(row[year_col])
        if iso2 not in records or yr > records[iso2][1]:
            records[iso2] = (round(float(row[score_col]), 0), yr)

    values = pd.Series({k: v[0] for k,v in records.items()},
                       name="ti_cpi").reindex(COUNTRIES)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name="ti_cpi_year").reindex(COUNTRIES)
    _validate(values, 20, 100, years)
    return values, years


# ── 9: V-Dem LDI ─────────────────────────────────────────────────────────────

def build_vdem_ldi() -> tuple[pd.Series, pd.Series]:
    log.info("=== vdem_ldi (V-Dem v15) ===")
    if not VDEM_CSV.exists():
        log.error("[vdem_ldi]  V-Dem CSV not found"); return _empty2("vdem_ldi")
    df = pd.read_csv(VDEM_CSV, usecols=["country_name","year","v2x_libdem"],
                     low_memory=False)
    df["iso2"] = df["country_name"].map(VDEM_NAMES)
    df = df.dropna(subset=["iso2","v2x_libdem"])
    df = df[df["iso2"].isin(COUNTRIES)]
    records: dict[str, tuple[float,int]] = {}
    for iso2, grp in df.groupby("iso2"):
        row = grp.sort_values("year", ascending=False).iloc[0]
        records[iso2] = (round(float(row["v2x_libdem"]), 3), int(row["year"]))
    values = pd.Series({k: v[0] for k,v in records.items()},
                       name="vdem_ldi").reindex(COUNTRIES)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name="vdem_ldi_year").reindex(COUNTRIES)
    _validate(values, 0.0, 1.0, years)
    return values, years


# ── 10: Life Satisfaction (OWID mirror of World Happiness Report) ─────────────

def build_whr_ladder() -> tuple[pd.Series, pd.Series]:
    log.info("=== whr_ladder (WHR via Our World in Data) ===")
    cache = RAW_IND / "owid_happiness.csv"
    url   = "https://ourworldindata.org/grapher/happiness-cantril-ladder.csv"
    try:
        _download(url, cache)
        df = pd.read_csv(cache)
    except Exception as e:
        log.error("[whr_ladder]  download failed: %s", e); return _empty2("whr_ladder")

    df.columns = df.columns.str.strip()
    code_col  = next((c for c in df.columns if c.lower() == "code"), None)
    score_col = next((c for c in df.columns
                      if "satisfaction" in c.lower() or "ladder" in c.lower() or
                      "happiness" in c.lower()), None)
    year_col  = next((c for c in df.columns if c.lower() == "year"), None)

    if not all([code_col, score_col, year_col]):
        log.error("[whr_ladder]  columns not recognised: %s", list(df.columns))
        return _empty2("whr_ladder")

    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df[year_col]  = pd.to_numeric(df[year_col],  errors="coerce")
    df = df.dropna(subset=[score_col, year_col])

    records: dict[str, tuple[float,int]] = {}
    for _, row in df.iterrows():
        iso3 = str(row[code_col]).strip().upper()
        iso2 = ISO3_TO_ISO2.get(iso3) or (iso3 if len(iso3)==2 else None)
        if iso2 not in COUNTRIES: continue
        yr = int(row[year_col])
        if iso2 not in records or yr > records[iso2][1]:
            records[iso2] = (round(float(row[score_col]), 2), yr)

    values = pd.Series({k: v[0] for k,v in records.items()},
                       name="whr_ladder").reindex(COUNTRIES)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name="whr_ladder_year").reindex(COUNTRIES)
    _validate(values, 3.5, 8.5, years)
    return values, years


# ── 11: Foreign-born share (World Bank SM.POP.TOTL.ZS) ───────────────────────

def build_foreign_born() -> tuple[pd.Series, pd.Series]:
    log.info("=== estat_foreign_born_pct (World Bank SM.POP.TOTL.ZS) ===")
    # Eurostat migr_pop3ctb returns absolute counts; computing % requires
    # a separate population denominator. World Bank publishes the ratio
    # directly as SM.POP.TOTL.ZS (international migrant stock, % of population).
    iso2_list = ";".join(COUNTRIES)
    url = (f"https://api.worldbank.org/v2/country/{iso2_list}/"
           f"indicator/SM.POP.TOTL.ZS?format=json&per_page=1000&date=2000:2024")
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent":"human-values/1.0"})
        r.raise_for_status()
        data = r.json()
        rows = data[1] if len(data) > 1 and data[1] else []
    except Exception as e:
        log.error("[foreign_born]  WB API failed: %s", e)
        return _empty2("estat_foreign_born_pct")

    records: dict[str, tuple[float,int]] = {}
    for row in rows:
        if row["value"] is None: continue
        iso3 = row["countryiso3code"]
        iso2 = ISO3_TO_ISO2.get(iso3)
        if iso2 not in COUNTRIES: continue
        yr = int(row["date"])
        if iso2 not in records or yr > records[iso2][1]:
            records[iso2] = (round(float(row["value"]), 1), yr)

    values = pd.Series({k: v[0] for k,v in records.items()},
                       name="estat_foreign_born_pct").reindex(COUNTRIES)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name="estat_foreign_born_pct_year").reindex(COUNTRIES)
    _validate(values, 0, 60, years)
    return values, years


# ── 12: Trade Union Density (OECD.Stat / ILO fallback) ───────────────────────

def build_union_density() -> tuple[pd.Series, pd.Series]:
    log.info("=== oecd_union_density (OECD SDMX DSD_TUD_CBC@DF_TUD) ===")
    cache = RAW_IND / "oecd_tud_cbc.csv"
    # Correct OECD SDMX endpoint — 3 key dimensions: REF_AREA, MEASURE, UNIT_MEASURE
    url = ("https://sdmx.oecd.org/public/rest/data/"
           "OECD.ELS.SAE,DSD_TUD_CBC@DF_TUD,1.0/.+.."
           "?format=csv&startPeriod=2015&endPeriod=2024")
    try:
        _download(url, cache, timeout=90)
        df = pd.read_csv(cache)
    except Exception as e:
        log.error("[union_density]  download failed: %s", e)
        return _empty2("oecd_union_density")

    df.columns = df.columns.str.strip()
    # Expected columns: DATAFLOW, REF_AREA, MEASURE, UNIT_MEASURE, TIME_PERIOD, OBS_VALUE
    geo_col   = next((c for c in df.columns if c in ("REF_AREA", "COUNTRY", "COU")), None)
    val_col   = next((c for c in df.columns if "OBS_VALUE" in c or c == "Value"), None)
    year_col  = next((c for c in df.columns if "TIME_PERIOD" in c or c == "Year"), None)
    meas_col  = next((c for c in df.columns if "MEASURE" in c), None)
    unit_col  = next((c for c in df.columns if "UNIT_MEASURE" in c), None)

    if not all([geo_col, val_col, year_col]):
        log.error("[union_density]  columns not found: %s", list(df.columns))
        return _empty2("oecd_union_density")

    df[val_col]  = pd.to_numeric(df[val_col],  errors="coerce")
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[val_col, year_col])

    # Filter to union density (TUD) as % of wage earners (PT_SAL) if possible
    if meas_col and "TUD" in df[meas_col].unique():
        df = df[df[meas_col] == "TUD"]
    if unit_col and "PT_SAL" in df[unit_col].unique():
        df = df[df[unit_col] == "PT_SAL"]

    records: dict[str, tuple[float,int]] = {}
    for _, row in df.iterrows():
        iso3 = str(row[geo_col]).strip().upper()
        iso2 = ISO3_TO_ISO2.get(iso3) or (iso3 if len(iso3)==2 else None)
        if iso2 not in COUNTRIES: continue
        yr = int(row[year_col])
        if iso2 not in records or yr > records[iso2][1]:
            records[iso2] = (round(float(row[val_col]), 1), yr)

    values = pd.Series({k: v[0] for k,v in records.items()},
                       name="oecd_union_density").reindex(COUNTRIES)
    years  = pd.Series({k: v[1] for k,v in records.items()},
                       name="oecd_union_density_year").reindex(COUNTRIES)
    _validate(values, 2, 95, years)  # Iceland legitimately reaches ~90%
    return values, years


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Building country indicators — %s", RETRIEVAL_DATE)
    parts: list[pd.Series] = []

    v, y = build_ess_mean("trust_mean", "ess_trust_mean", (1.5, 8.5));      parts += [v, y]
    v, y = build_ess_mean("religiosity_mean", "ess_religiosity_mean", (1.0, 9.0)); parts += [v, y]
    v, y = build_estat_gini();        parts += [v, y]
    v, y = build_estat_gdp_pps();     parts += [v, y]
    v, y = build_estat_tertiary();    parts += [v, y]
    v, y = build_estat_hly();         parts += [v, y]
    v, y = build_eige_gei();          parts += [v, y]
    v, y = build_ti_cpi();            parts += [v, y]
    v, y = build_vdem_ldi();          parts += [v, y]
    v, y = build_whr_ladder();        parts += [v, y]
    v, y = build_foreign_born();      parts += [v, y]
    v, y = build_union_density();     parts += [v, y]

    df = pd.DataFrame({"cntry": COUNTRIES}).set_index("cntry")
    for s in parts:
        df[s.name] = s
    df = df.reset_index()

    out = PRECOMP / "df_indicators.csv"
    df.to_csv(out, index=False)
    log.info("=== Written %s  (%d rows × %d cols) ===",
             out.name, len(df), len(df.columns))
    log.info("Coverage:")
    for c in [col for col in df.columns if not col.endswith("_year") and col != "cntry"]:
        log.info("  %-32s  %d/39", c, df[c].notna().sum())


if __name__ == "__main__":
    main()
