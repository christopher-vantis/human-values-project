"""Regenerate the precomputed datasets deployed with the dashboard (run locally).

Builds, from the raw ESS11 CSV (which is never deployed):
  - df_main.csv       country-level weighted Schwartz aggregates
  - df_scatter.csv    country-level cross-section for the Correlations tab
  - df_regional.csv   NUTS-region aggregates for Germany + Switzerland
  - df_gradients.csv  within-country social gradients for Germany + Switzerland

Not touched here (built by their own scripts):
  - df_gov_exp.csv, df_indicators.csv, indicator_sentences.json
  - nuts_regions.geojson + df_regional_indicators.csv (build_regional.py)
  - mlm_results.json (build_mlm.py)

Usage:
    python dashboard/export_precomputed.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

import data_pipeline as dp

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

# Legacy artefact of the removed Parallel Coordinates tab
_OBSOLETE = ['df_micro.csv']


def _write(df: pd.DataFrame, name: str) -> None:
    """Write one precomputed CSV and log its size."""
    path = dp.PRECOMPUTED_DIR / f'{name}.csv'
    df.to_csv(path, index=False)
    log.info('%s: %d rows, %d KB', path.name, len(df),
             path.stat().st_size // 1024)


def main() -> None:
    """Build all ESS11-derived datasets and remove obsolete files."""
    dp.PRECOMPUTED_DIR.mkdir(exist_ok=True)

    log.info('Reading + scoring ESS11 microdata ...')
    micro   = dp.add_person_scores(dp.read_ess11_micro())
    df_main = dp.build_country_aggregates(micro)

    _write(df_main, 'df_main')
    _write(dp.build_scatter(micro, df_main), 'df_scatter')
    _write(dp.build_regional_aggregates(micro), 'df_regional')
    _write(dp.build_gradients(micro), 'df_gradients')

    for name in _OBSOLETE:
        path = dp.PRECOMPUTED_DIR / name
        if path.exists():
            path.unlink()
            log.info('Removed obsolete %s', name)

    log.info('Done. Next: python dashboard/build_regional.py (if needed) '
             'and python dashboard/build_mlm.py')


if __name__ == '__main__':
    main()
