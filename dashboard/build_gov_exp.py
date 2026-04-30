"""
Build comprehensive government expenditure by COFOG function dataset.

Sources:
  1. Eurostat gov_10a_exp (EU + EEA, unit=PC_GDP) — ~30 countries
  2. World Bank Development Indicators API (non-EU countries)

Output:
  data/raw/indicators/gov_exp_full.csv
  dashboard/precomputed/df_gov_exp.csv  (merged, committed)

Run: python3 dashboard/build_gov_exp.py
Retrieved: 2026-04-30
"""
from __future__ import annotations
import logging, sys
from pathlib import Path
import pandas as pd
import numpy as np
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s",
                    stream=sys.stdout)
log = logging.getLogger(__name__)

ROOT    = Path(__file__).parent.parent
RAW_IND = ROOT / "data" / "raw" / "indicators"
PRECOMP = Path(__file__).parent / "precomputed"
RAW_IND.mkdir(parents=True, exist_ok=True)

# All 39 ESS countries
COUNTRIES = [
    "AL","AT","BE","BG","CH","CY","CZ","DE","DK","EE",
    "ES","FI","FR","GB","GR","HR","HU","IE","IL","IS",
    "IT","LT","LU","LV","ME","MK","NL","NO","PL","PT",
    "RO","RS","RU","SE","SI","SK","TR","UA","XK",
]

# ESS reference years
ESS_YEARS = [2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2023]

# Eurostat: uses EL for Greece, UK for United Kingdom
_ESTAT_REMAP = {"EL": "GR", "UK": "GB"}

# ISO-3 → ISO-2 for World Bank
ISO3_TO_ISO2 = {
    "ALB":"AL","AUT":"AT","BEL":"BE","BGR":"BG","CHE":"CH","CYP":"CY",
    "CZE":"CZ","DEU":"DE","DNK":"DK","EST":"EE","ESP":"ES","FIN":"FI",
    "FRA":"FR","GBR":"GB","GRC":"GR","HRV":"HR","HUN":"HU","IRL":"IE",
    "ISR":"IL","ISL":"IS","ITA":"IT","LTU":"LT","LUX":"LU","LVA":"LV",
    "MNE":"ME","MKD":"MK","NLD":"NL","NOR":"NO","POL":"PL","PRT":"PT",
    "ROU":"RO","SRB":"RS","RUS":"RU","SWE":"SE","SVN":"SI","SVK":"SK",
    "TUR":"TR","UKR":"UA","XKX":"XK",
}

# COFOG categories we extract
COFOG_COLS = {
    "GF01": "gov_exp_public_services",
    "GF02": "gov_exp_defence",
    "GF04": "gov_exp_economic",
    "GF07": "gov_exp_health",
    "GF08": "gov_exp_culture",
    "GF09": "gov_exp_education",
    "GF10": "gov_exp_social",
}
ALL_GOV_COLS = list(COFOG_COLS.values())


def _nearest_ess_year(year: int) -> int | None:
    """Map a calendar year to the nearest ESS reference year (≤2 year gap)."""
    dists = [(abs(year - y), y) for y in ESS_YEARS]
    dist, nearest = min(dists)
    return nearest if dist <= 2 else None


# ── Source 1: Eurostat gov_10a_exp ────────────────────────────────────────────

def build_eurostat() -> pd.DataFrame:
    """
    Fetch Eurostat gov_10a_exp for all available countries.
    Unit: PC_GDP (% of GDP), Sector: S13 (general government), na_item: TE.
    """
    log.info("=== Eurostat gov_10a_exp ===")
    import eurostat
    cache = RAW_IND / "estat_gov_10a_exp.csv"
    if not cache.exists():
        log.info("  downloading from Eurostat API...")
        df = eurostat.get_data_df("gov_10a_exp", flags=False)
        df.to_csv(cache, index=False)
        log.info("  saved (%d KB)", cache.stat().st_size // 1024)
    else:
        log.info("  cached → %s", cache.name)

    df = pd.read_csv(cache)
    df.columns = df.columns.str.strip()

    geo_col = next(c for c in df.columns if c.lower().startswith("geo"))
    year_cols = [c for c in df.columns if str(c).isdigit() and 2000 <= int(c) <= 2030]

    # Filter: S13 general gov, TE total expenditure, PC_GDP
    mask = (df.get("sector", pd.Series("")) == "S13") & \
           (df.get("na_item", pd.Series("")) == "TE") & \
           (df.get("unit", pd.Series("")) == "PC_GDP")
    sub = df[mask].copy()
    sub[geo_col] = sub[geo_col].replace(_ESTAT_REMAP)

    records = []
    for _, row in sub.iterrows():
        geo  = str(row[geo_col]).strip()
        cofog = str(row.get("cofog99", "")).strip()
        col   = COFOG_COLS.get(cofog)
        if col is None or geo not in COUNTRIES:
            continue
        for yr_str in year_cols:
            yr  = int(yr_str)
            val = pd.to_numeric(row[yr_str], errors="coerce")
            if pd.isna(val):
                continue
            ess_yr = _nearest_ess_year(yr)
            if ess_yr is None:
                continue
            records.append({"cntry": geo, "year": ess_yr, col: val,
                            f"{col}_source": "Eurostat gov_10a_exp"})

    df_long = pd.DataFrame(records)
    if df_long.empty:
        log.error("Eurostat: no data extracted")
        return pd.DataFrame()

    # Aggregate by (cntry, year): take the value closest to the ESS year
    # Multiple calendar years may map to the same ESS year — take the mean
    id_cols = ["cntry", "year"]
    val_cols = [c for c in df_long.columns if c in ALL_GOV_COLS]
    result = df_long.groupby(id_cols)[val_cols].mean().reset_index()

    n_ctry = len(result["cntry"].unique())
    log.info("  Eurostat: %d rows, %d countries, cols: %s",
             len(result), n_ctry, val_cols)
    return result


# ── Source 2: World Bank API ───────────────────────────────────────────────────
# For non-Eurostat countries: GB, AL, ME, MK, RS, RU, UA, XK, IL, TR
# World Bank COFOG-aligned indicators:
WB_INDICATORS = {
    "gov_exp_health":    "SH.XPD.GHED.GD.ZS",   # domestic general gov health % GDP
    "gov_exp_education": "SE.XPD.TOTL.GD.ZS",    # gov education expenditure % GDP
    "gov_exp_defence":   "MS.MIL.XPND.GD.ZS",    # military expenditure % GDP
    "gov_exp_social":    "SP.SPD.TOTL.GD.ZS",     # social protection % GDP
}
# GF01 (public services), GF04 (economic), GF08 (culture) not available in WB;
# they will remain NaN for countries not covered by Eurostat.


def build_worldbank(target_countries: list[str]) -> pd.DataFrame:
    """Fetch World Bank COFOG-aligned indicators for given ISO-2 country list."""
    if not target_countries:
        return pd.DataFrame()
    log.info("=== World Bank gov_exp for %d countries ===", len(target_countries))
    iso2_str = ";".join(target_countries)

    records = []
    for col, indicator in WB_INDICATORS.items():
        cache = RAW_IND / f"wb_{indicator.replace('.','_')}.json"
        if not cache.exists():
            url = (f"https://api.worldbank.org/v2/country/{iso2_str}/"
                   f"indicator/{indicator}?format=json&per_page=1000&date=2000:2024")
            log.info("  downloading WB %s (%s)...", indicator, col)
            try:
                r = requests.get(url, timeout=30,
                                 headers={"User-Agent": "human-values/1.0"})
                r.raise_for_status()
                import json
                cache.write_text(r.text)
            except Exception as e:
                log.warning("  WB %s failed: %s", indicator, e)
                continue
        import json
        try:
            data = json.loads(cache.read_text())
            rows = data[1] if len(data) > 1 and data[1] else []
        except Exception:
            continue

        for row in rows:
            if row["value"] is None:
                continue
            iso3 = row.get("countryiso3code", "")
            iso2 = ISO3_TO_ISO2.get(iso3)
            if iso2 not in target_countries:
                continue
            yr = int(row["date"])
            ess_yr = _nearest_ess_year(yr)
            if ess_yr is None:
                continue
            records.append({
                "cntry": iso2,
                "year":  ess_yr,
                col:     round(float(row["value"]), 3),
                f"{col}_source": f"World Bank {indicator}",
            })

    if not records:
        log.warning("World Bank: no records fetched")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    id_cols  = ["cntry", "year"]
    val_cols = [c for c in df.columns if c in ALL_GOV_COLS]
    result   = df.groupby(id_cols)[val_cols].mean().reset_index()
    log.info("  WB: %d rows, %d countries", len(result), len(result["cntry"].unique()))
    return result


# ── Merge and validate ─────────────────────────────────────────────────────────

def build_gov_exp_full() -> pd.DataFrame:
    df_estat = build_eurostat()
    estat_countries = set(df_estat["cntry"].unique()) if not df_estat.empty else set()
    wb_countries = [c for c in COUNTRIES if c not in estat_countries]
    log.info("Eurostat covers: %s", sorted(estat_countries))
    log.info("WB targets: %s", wb_countries)

    df_wb = build_worldbank(wb_countries)

    # Combine
    frames = [f for f in [df_estat, df_wb] if f is not None and not f.empty]
    if not frames:
        log.error("No data from any source")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # Aggregate again in case of overlaps
    id_cols  = ["cntry", "year"]
    val_cols = [c for c in combined.columns if c in ALL_GOV_COLS]
    result   = combined.groupby(id_cols)[val_cols].mean().reset_index().round(3)

    log.info("\n=== Coverage ===")
    for col in val_cols:
        n_c = result[result[col].notna()]["cntry"].nunique()
        log.info("  %-30s  %d/39 countries", col, n_c)

    # Save raw
    raw_out = RAW_IND / "gov_exp_full.csv"
    result.to_csv(raw_out, index=False)
    log.info("Saved raw → %s (%d rows)", raw_out.name, len(result))

    # Save precomputed (committed to git)
    pre_out = PRECOMP / "df_gov_exp.csv"
    result.to_csv(pre_out, index=False)
    log.info("Saved precomputed → %s", pre_out.name)

    return result


if __name__ == "__main__":
    df = build_gov_exp_full()
    log.info("\nDone. %d rows × %d cols", len(df), len(df.columns))
