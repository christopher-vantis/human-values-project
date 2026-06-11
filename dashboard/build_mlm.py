"""Precompute multilevel (mixed-effects) models for the dashboard (run locally).

For each of the four higher-order Schwartz dimensions, fits a linear
mixed-effects model on ESS11 individual-level data:

    dim_score_ij = b0 + b * individual_ij + g * country_j + u_j + e_ij

with random country intercepts u_j. Individual predictors: age, gender,
years of education, urban residence, religiosity. Country predictors:
GDP per capita (PPP) and Gini index (both z-scored across countries).

The point of the exercise (vs. the bivariate country-level correlations in
the Correlations tab): it separates compositional from contextual effects
and quantifies how much of the variance actually sits between countries
(ICC). Results are written to precomputed/mlm_results.json.

Usage:
    python dashboard/build_mlm.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

import data_pipeline as dp

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

OUT_PATH = dp.PRECOMPUTED_DIR / 'mlm_results.json'

# (model term, display label)
PREDICTOR_LABELS = [
    ('age_z',     'Age (z)'),
    ('female',    'Female'),
    ('eduyrs_z',  'Education years (z)'),
    ('urban',     'Urban residence'),
    ('relig_z',   'Religiosity (z)'),
    ('gdp_z',     'GDP per capita, country (z)'),
    ('gini_z',    'Gini index, country (z)'),
]

_FORMULA_RHS = ' + '.join(term for term, _ in PREDICTOR_LABELS)


def _zscore(series: pd.Series) -> pd.Series:
    """Z-standardise a Series (NaN-safe)."""
    return (series - series.mean()) / series.std()


def prepare_analysis_frame() -> pd.DataFrame:
    """Build the individual-level analysis dataset with all model variables.

    Returns:
        One row per respondent with the four dimension outcomes, z-scored
        individual predictors, and z-scored country-level macro predictors.
        Listwise deletion on all model variables.
    """
    micro = dp.add_person_scores(dp.read_ess11_micro())
    scatter = dp.load_scatter_data()
    macro = scatter[['cntry', 'wb_gdp_per_capita_ppp', 'wb_gini']].copy()
    macro['gdp_z']  = _zscore(macro['wb_gdp_per_capita_ppp'])
    macro['gini_z'] = _zscore(macro['wb_gini'])

    df = micro.merge(macro[['cntry', 'gdp_z', 'gini_z']], on='cntry', how='left')
    df['age_z']    = _zscore(df['agea'])
    df['female']   = df['gndr'].map({1.0: 0.0, 2.0: 1.0})
    df['eduyrs_z'] = _zscore(df['eduyrs'].clip(upper=30))
    df['urban']    = (df['domicil'].isin([1, 2]).astype(float)
                      .where(df['domicil'].notna()))
    df['relig_z']  = _zscore(df['rlgdgr'])

    model_vars = ([t for t, _ in PREDICTOR_LABELS]
                  + list(dp.DIM_COLS.values()) + ['cntry'])
    df = df.dropna(subset=model_vars)
    log.info('Analysis frame: %d respondents, %d countries',
             len(df), df['cntry'].nunique())
    return df


def _icc_null_model(df: pd.DataFrame, outcome: str) -> float:
    """Intraclass correlation from an intercept-only random-effects model.

    Args:
        df: Analysis frame.
        outcome: Dimension column name.

    Returns:
        Share of total variance located between countries.
    """
    import statsmodels.formula.api as smf

    null = smf.mixedlm(f'{outcome} ~ 1', df, groups=df['cntry']).fit(reml=True)
    var_u = float(null.cov_re.iloc[0, 0])
    var_e = float(null.scale)
    return var_u / (var_u + var_e)


def fit_dimension(df: pd.DataFrame, outcome: str) -> dict:
    """Fit the full mixed model for one Schwartz dimension.

    Args:
        df: Analysis frame.
        outcome: Dimension column name (e.g. 'dim_openness').

    Returns:
        Serialisable dict with coefficients, ICC, and sample sizes.
    """
    import statsmodels.formula.api as smf

    model = smf.mixedlm(f'{outcome} ~ {_FORMULA_RHS}', df,
                        groups=df['cntry']).fit(reml=True)
    coefs = []
    for term, label in PREDICTOR_LABELS:
        coefs.append({
            'term':  term,
            'label': label,
            'coef':  round(float(model.params[term]), 4),
            'se':    round(float(model.bse[term]), 4),
            'p':     float(model.pvalues[term]),
        })
    return {
        'outcome':      outcome,
        'coefficients': coefs,
        'icc':          round(_icc_null_model(df, outcome), 4),
        'n_obs':        int(model.nobs),
        'n_countries':  int(df['cntry'].nunique()),
    }


def main() -> None:
    """Fit all four dimension models and write the results JSON."""
    df = prepare_analysis_frame()
    results = {}
    for dim_label, col in dp.DIM_COLS.items():
        log.info('Fitting %s ...', dim_label)
        results[col] = fit_dimension(df, col)
        results[col]['label'] = dim_label

    payload = {
        'method': ('Linear mixed-effects models (statsmodels MixedLM, REML), '
                   'random country intercepts. Individual predictors z-scored '
                   'on the analysis sample; country predictors z-scored across '
                   'countries. Unweighted ESS11 microdata.'),
        'models': results,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=1))
    log.info('Wrote %s', OUT_PATH)


if __name__ == '__main__':
    main()
