"""Build the regional assets for the Country Deep Dive tab (run locally).

Produces two files in dashboard/precomputed/:
  - nuts_regions.geojson         trimmed GISCO NUTS-2021 boundaries
                                 (Germany NUTS-1 + Switzerland NUTS-2)
  - df_regional_indicators.csv   Eurostat regional indicators, latest
                                 available year per region

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

# German NUTS-1 (Bundesländer) + Swiss NUTS-2 (Grossregionen), NUTS 2021
DE_NUTS1 = ['DE1', 'DE2', 'DE3', 'DE4', 'DE5', 'DE6', 'DE7', 'DE8', 'DE9',
            'DEA', 'DEB', 'DEC', 'DED', 'DEE', 'DEF', 'DEG']
CH_NUTS2 = ['CH01', 'CH02', 'CH03', 'CH04', 'CH05', 'CH06', 'CH07']
ALL_REGIONS = DE_NUTS1 + CH_NUTS2

_GISCO_BASE = ('https://gisco-services.ec.europa.eu/distribution/v2/nuts/'
               'geojson/NUTS_RG_10M_2021_4326_LEVL_{level}.geojson')
_ESTAT_BASE = ('https://ec.europa.eu/eurostat/api/dissemination/'
               'statistics/1.0/data/{dataset}')

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


def fetch_geojson() -> dict:
    """Download GISCO NUTS boundaries and trim to the deep-dive regions.

    Returns:
        FeatureCollection with DE NUTS-1 and CH NUTS-2 features; properties
        reduced to NUTS_ID and NUTS_NAME.
    """
    features = []
    for level, wanted in ((1, set(DE_NUTS1)), (2, set(CH_NUTS2))):
        url = _GISCO_BASE.format(level=level)
        log.info('Downloading GISCO level %d ...', level)
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        for feat in resp.json()['features']:
            nuts_id = feat['properties'].get('NUTS_ID')
            if nuts_id in wanted:
                features.append({
                    'type': 'Feature',
                    'geometry': feat['geometry'],
                    'properties': {
                        'NUTS_ID':   nuts_id,
                        'NUTS_NAME': feat['properties'].get('NUTS_NAME', nuts_id),
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
    # index position of each category, per dimension
    cat_by_dim = []
    for dim in dims:
        index = payload['dimension'][dim]['category']['index']
        ordered = sorted(index, key=index.get)
        cat_by_dim.append(ordered)

    # strides for converting a flat index into per-dimension positions
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


def fetch_indicator(key: str, dataset: str, filters: dict) -> pd.DataFrame:
    """Fetch one Eurostat regional indicator for all deep-dive regions.

    Args:
        key: Indicator key (used in the output 'indicator' column).
        dataset: Eurostat dataset code.
        filters: Fixed dimension filters for the API call.

    Returns:
        DataFrame (region, indicator, value, year) - latest available year
        per region; empty if the dataset has no data for these regions.
    """
    params: list[tuple[str, str]] = [('format', 'JSON'), ('lang', 'EN')]
    params += list(filters.items())
    params += [('geo', g) for g in ALL_REGIONS]
    resp = requests.get(_ESTAT_BASE.format(dataset=dataset),
                        params=params, timeout=120)
    resp.raise_for_status()
    df = _parse_jsonstat(resp.json())
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
    PRECOMPUTED_DIR.mkdir(exist_ok=True)

    geojson = fetch_geojson()
    geo_path = PRECOMPUTED_DIR / 'nuts_regions.geojson'
    geo_path.write_text(json.dumps(geojson, separators=(',', ':')))
    log.info('Wrote %s (%d KB)', geo_path, geo_path.stat().st_size // 1024)

    frames = [fetch_indicator(key, dataset, filters)
              for key, (dataset, filters) in REGIONAL_DATASETS.items()]
    out = pd.concat(frames, ignore_index=True)
    csv_path = PRECOMPUTED_DIR / 'df_regional_indicators.csv'
    out.to_csv(csv_path, index=False)
    log.info('Wrote %s (%d rows)', csv_path, len(out))


if __name__ == '__main__':
    main()
