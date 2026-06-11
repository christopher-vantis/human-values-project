"""Build the regional assets for the Country Deep Dive tab (run locally).

Produces two files in dashboard/precomputed/:
  - nuts_regions.geojson         trimmed GISCO NUTS-2021 boundaries for
                                 every region observed in df_regional.csv
                                 (plus same-level context regions so areas
                                 without respondents can be greyed out)
  - df_regional_indicators.csv   Eurostat regional indicators, latest
                                 available year per region

Run AFTER export_precomputed.py - the region list is read from the
precomputed regional aggregates, so no raw ESS data is needed here.

Usage:
    python dashboard/build_regional.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

PRECOMPUTED_DIR = Path(__file__).parent / 'precomputed'
REGIONAL_CSV    = PRECOMPUTED_DIR / 'df_regional.csv'

# Overseas territories distort fitbounds so badly that the mainland map
# becomes unreadable - they are dropped from the context geometry.
OVERSEAS_PREFIXES = ('FRY', 'ES70', 'PT20', 'PT30')

_GISCO_BASE = ('https://gisco-services.ec.europa.eu/distribution/v2/nuts/'
               'geojson/NUTS_RG_10M_2021_4326_LEVL_{level}.geojson')
_ESTAT_BASE = ('https://ec.europa.eu/eurostat/api/dissemination/'
               'statistics/1.0/data/{dataset}')
_GEO_BATCH = 40   # regions per Eurostat API call (keeps URLs short)

# indicator key -> (dataset, fixed dimension filters)
REGIONAL_DATASETS: dict[str, tuple[str, dict]] = {
    'gdp_pps':      ('nama_10r_2gdp',   {'unit': 'PPS_EU27_2020_HAB'}),
    'unemployment': ('lfst_r_lfu3rt',   {'sex': 'T', 'age': 'Y15-74',
                                         'isced11': 'TOTAL', 'unit': 'PC'}),
    'tertiary_pct': ('edat_lfse_04',    {'sex': 'T', 'age': 'Y25-64',
                                         'isced11': 'ED5-8', 'unit': 'PC'}),
    'median_age':   ('demo_r_pjanind2', {'indic_de': 'MEDAGEPOP', 'unit': 'YR'}),
    'pop_density':  ('demo_r_d3dens',   {'unit': 'PER_KM2'}),
}


def load_observed_regions() -> pd.DataFrame:
    """Region codes observed in the ESS11 aggregates (from precomputed CSV).

    Returns:
        df_regional with cntry and region columns.

    Raises:
        FileNotFoundError: if export_precomputed.py has not been run yet.
    """
    if not REGIONAL_CSV.exists():
        raise FileNotFoundError(
            'precomputed/df_regional.csv missing - run '
            'export_precomputed.py first')
    return pd.read_csv(REGIONAL_CSV)


def _wanted_context(observed: set[str]) -> tuple[set[str], set[tuple[str, int]]]:
    """Compute which (prefix, level) combinations the map needs.

    Args:
        observed: Region codes seen in the ESS data.

    Returns:
        (observed codes, {(nuts_prefix, level)}) - context combinations so
        that regions without respondents can still be drawn in grey.
    """
    combos = {(code[:2], len(code) - 2) for code in observed}
    return observed, combos


def fetch_geojson(observed: set[str]) -> dict:
    """Download GISCO NUTS boundaries and trim to the needed regions.

    Args:
        observed: Region codes present in df_regional.

    Returns:
        FeatureCollection with all observed regions plus same-country,
        same-level context regions (overseas territories excluded);
        properties reduced to NUTS_ID and NUTS_NAME.
    """
    observed, combos = _wanted_context(observed)
    levels = sorted({level for _, level in combos})
    features = []
    for level in levels:
        url = _GISCO_BASE.format(level=level)
        log.info('Downloading GISCO level %d ...', level)
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        for feat in resp.json()['features']:
            nuts_id = feat['properties'].get('NUTS_ID', '')
            in_context = (nuts_id[:2], level) in combos
            if nuts_id.startswith(OVERSEAS_PREFIXES):
                continue
            if nuts_id in observed or in_context:
                features.append({
                    'type': 'Feature',
                    'geometry': feat['geometry'],
                    'properties': {
                        'NUTS_ID':   nuts_id,
                        'NUTS_NAME': feat['properties'].get('NUTS_NAME',
                                                            nuts_id),
                    },
                })
    log.info('Kept %d region features', len(features))
    return {'type': 'FeatureCollection', 'features': features}


def _parse_jsonstat(payload: dict) -> pd.DataFrame:
    """Flatten a Eurostat JSON-stat 2.0 response into (geo, time, value) rows.

    Args:
        payload: Parsed JSON response from the Eurostat dissemination API.

    Returns:
        DataFrame with columns geo, time (int year), value (float).
    """
    dims  = payload['id']
    sizes = payload['size']
    cat_by_dim = []
    for dim in dims:
        index = payload['dimension'][dim]['category']['index']
        cat_by_dim.append(sorted(index, key=index.get))

    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    geo_pos, time_pos = dims.index('geo'), dims.index('time')
    rows = []
    for flat_str, value in payload['value'].items():
        flat = int(flat_str)
        coords = [(flat // strides[i]) % sizes[i] for i in range(len(sizes))]
        rows.append({
            'geo':   cat_by_dim[geo_pos][coords[geo_pos]],
            'time':  int(cat_by_dim[time_pos][coords[time_pos]]),
            'value': float(value),
        })
    return pd.DataFrame(rows)


def fetch_indicator(key: str, dataset: str, filters: dict,
                    regions: list[str]) -> pd.DataFrame:
    """Fetch one Eurostat regional indicator for all regions (batched).

    Args:
        key: Indicator key (used in the output 'indicator' column).
        dataset: Eurostat dataset code.
        filters: Fixed dimension filters for the API call.
        regions: NUTS region codes to query.

    Returns:
        DataFrame (region, indicator, value, year) - latest available year
        per region; regions the dataset does not cover are simply absent.
    """
    frames = []
    for start in range(0, len(regions), _GEO_BATCH):
        batch = regions[start:start + _GEO_BATCH]
        params: list[tuple[str, str]] = [('format', 'JSON'), ('lang', 'EN')]
        params += list(filters.items())
        params += [('geo', g) for g in batch]
        resp = requests.get(_ESTAT_BASE.format(dataset=dataset),
                            params=params, timeout=180)
        if resp.status_code != 200:
            log.warning('%s: batch %d-%d failed (%d)', key, start,
                        start + len(batch), resp.status_code)
            continue
        frames.append(_parse_jsonstat(resp.json()))
    df = (pd.concat(frames, ignore_index=True)
          if frames else pd.DataFrame(columns=['geo', 'time', 'value']))
    if df.empty:
        log.warning('%s: no data returned', key)
        return pd.DataFrame(columns=['region', 'indicator', 'value', 'year'])

    latest = (df.sort_values('time').groupby('geo', as_index=False).tail(1)
                .rename(columns={'geo': 'region', 'time': 'year'}))
    latest['indicator'] = key
    log.info('%s: %d regions, years %d-%d', key, len(latest),
             latest['year'].min(), latest['year'].max())
    return latest[['region', 'indicator', 'value', 'year']]


def main() -> None:
    """Build and write both regional asset files."""
    observed = set(load_observed_regions()['region'])
    log.info('%d observed ESS11 regions', len(observed))

    geojson = fetch_geojson(observed)
    geo_path = PRECOMPUTED_DIR / 'nuts_regions.geojson'
    geo_path.write_text(json.dumps(geojson, separators=(',', ':')))
    log.info('Wrote %s (%d KB)', geo_path, geo_path.stat().st_size // 1024)

    all_regions = sorted(f['properties']['NUTS_ID']
                         for f in geojson['features'])
    frames = [fetch_indicator(key, dataset, filters, all_regions)
              for key, (dataset, filters) in REGIONAL_DATASETS.items()]
    out = pd.concat(frames, ignore_index=True)
    csv_path = PRECOMPUTED_DIR / 'df_regional_indicators.csv'
    out.to_csv(csv_path, index=False)
    log.info('Wrote %s (%d rows)', csv_path, len(out))


if __name__ == '__main__':
    main()
