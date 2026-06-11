"""Pytest suite for statistical and mathematical correctness.

Covers five layers of the ESS11-only pipeline (dashboard/data_pipeline.py):

    1. Core math primitives  - reverse-coding, person-centring, weighted
                               means, Benjamini-Hochberg q-values, Pearson r
                               versus a scipy reference.
    2. Person-level scoring  - add_person_scores() on synthetic microdata:
                               PVQ-21 mapping, validity filter, centring.
    3. Dashboard precomputed - dashboard/precomputed/* invariants: ESS11
                               cross-section shape, dimension-formula
                               consistency across df_main and df_scatter,
                               regional / gradient / geojson / MLM outputs.
    4. Final analysis dataset - macro_schwartz_analysis_data.csv structural
                               invariants (legacy research dataset, unchanged).
    5. Cross-dataset consistency.

Tests that require raw ESS microdata (not in the repo) are skipped rather
than failed.

Run from the project root:

    pytest tests/test_statistics.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / 'dashboard'
DATA_DIR = PROJECT_ROOT / 'data' / 'merged_datasets'
PRECOMPUTED_DIR = DASHBOARD_DIR / 'precomputed'

sys.path.insert(0, str(DASHBOARD_DIR))

import data_pipeline as dp                      # noqa: E402
from figures.scatter import _bh_qvalues, _regress_ci   # noqa: E402

MAIN_CSV = DATA_DIR / 'macro_schwartz_analysis_data.csv'

ESS_REFERENCE_YEARS = {2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018,
                       2020, 2023}

EXPECTED_COUNTRIES = {
    'AL', 'AT', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI',
    'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IL', 'IS', 'IT', 'LT', 'LU', 'LV',
    'ME', 'MK', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'RU', 'SE', 'SI', 'SK',
    'TR', 'UA', 'XK',
}

D_COLS = [f'd_{k}' for k in dp.VALUE_KEYS]
DIM_DELTA_FORMULA = {
    'dim_openness':      ['d_SD', 'd_HE', 'd_ST'],
    'dim_transcendence': ['d_UN', 'd_BE'],
    'dim_conservation':  ['d_TR', 'd_CO', 'd_SE'],
    'dim_enhancement':   ['d_PO', 'd_AC'],
}


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def _load_csv_or_skip(path: Path) -> pd.DataFrame:
    """Load a CSV or skip the test if the file is missing."""
    if not path.exists():
        pytest.skip(f'required file not present: {path.relative_to(PROJECT_ROOT)}')
    return pd.read_csv(path)


@pytest.fixture(scope='module')
def df_main() -> pd.DataFrame:
    return _load_csv_or_skip(PRECOMPUTED_DIR / 'df_main.csv')


@pytest.fixture(scope='module')
def df_scatter() -> pd.DataFrame:
    return _load_csv_or_skip(PRECOMPUTED_DIR / 'df_scatter.csv')


@pytest.fixture(scope='module')
def df_regional() -> pd.DataFrame:
    return _load_csv_or_skip(PRECOMPUTED_DIR / 'df_regional.csv')


@pytest.fixture(scope='module')
def df_gradients() -> pd.DataFrame:
    return _load_csv_or_skip(PRECOMPUTED_DIR / 'df_gradients.csv')


@pytest.fixture(scope='module')
def df_reg_ind() -> pd.DataFrame:
    return _load_csv_or_skip(PRECOMPUTED_DIR / 'df_regional_indicators.csv')


@pytest.fixture(scope='module')
def geojson() -> dict:
    path = PRECOMPUTED_DIR / 'nuts_regions.geojson'
    if not path.exists():
        pytest.skip('nuts_regions.geojson not present')
    return json.loads(path.read_text())


@pytest.fixture(scope='module')
def mlm_results() -> dict:
    path = PRECOMPUTED_DIR / 'mlm_results.json'
    if not path.exists():
        pytest.skip('mlm_results.json not present')
    return json.loads(path.read_text())


@pytest.fixture(scope='module')
def df_main_csv() -> pd.DataFrame:
    return _load_csv_or_skip(MAIN_CSV)


def _synthetic_micro(n: int = 200, seed: int = 7) -> pd.DataFrame:
    """Synthetic ESS11-style microdata with all 21 PVQ items in [1, 6]."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({item: rng.integers(1, 7, size=n).astype(float)
                       for item in dp.ALL_PVQ_ITEMS})
    df['cntry'] = np.where(rng.random(n) < 0.5, 'DE', 'CH')
    df['region'] = 'DE1'
    df['anweight'] = rng.uniform(0.2, 3.0, size=n)
    for col in ['gndr', 'agea', 'eduyrs', 'domicil', 'rlgdgr', 'ppltrst',
                'lrscale', 'aesfdrk', 'brncntr', 'facntr', 'mocntr']:
        df[col] = 1.0
    return df


# ===========================================================================
# Section 1: Core math primitives
# ===========================================================================

class TestCoreMath:
    """Unit tests for the smallest mathematical building blocks."""

    # --- Reverse-coding & centring -------------------------------------------

    def test_reverse_coding_flips_scale(self) -> None:
        """7 - x maps 1 -> 6 and 6 -> 1, preserving distances."""
        x = np.array([1, 2, 3, 4, 5, 6], dtype=float)
        z = 7 - x
        assert z.tolist() == [6, 5, 4, 3, 2, 1]
        assert np.allclose(np.diff(z), -np.diff(x))

    def test_person_centring_sums_to_zero_over_items(self) -> None:
        """Centred item scores sum to zero per respondent."""
        rng = np.random.default_rng(42)
        for _ in range(50):
            row = rng.uniform(1, 6, size=21)
            centred = row - row.mean()
            assert np.isclose(centred.sum(), 0.0, atol=1e-12)

    def test_weighted_mean_matches_numpy(self) -> None:
        """_weighted_mean equals np.average and ignores NaN values."""
        vals = pd.Series([1.0, 2.0, np.nan, 4.0])
        w = pd.Series([1.0, 2.0, 5.0, 1.0])
        expected = np.average([1.0, 2.0, 4.0], weights=[1.0, 2.0, 1.0])
        assert np.isclose(dp._weighted_mean(vals, w), expected)

    def test_weighted_mean_all_nan_returns_nan(self) -> None:
        """No valid observations -> NaN, not an exception."""
        out = dp._weighted_mean(pd.Series([np.nan, np.nan]),
                                pd.Series([1.0, 1.0]))
        assert np.isnan(out)

    # --- PVQ-21 mapping -------------------------------------------------------

    def test_pvq21_mapping_covers_21_distinct_items(self) -> None:
        """All 21 PVQ items are assigned exactly once across the 10 values."""
        assert set(dp.PVQ21_ITEMS) == set(dp.VALUE_KEYS)
        assert len(dp.ALL_PVQ_ITEMS) == 21
        assert len(set(dp.ALL_PVQ_ITEMS)) == 21

    def test_pvq21_standard_assignments(self) -> None:
        """Spot-check the standard ESS assignment of contested items."""
        assert 'iprspot' in dp.PVQ21_ITEMS['PO']    # respect -> Power
        assert 'ipmodst' in dp.PVQ21_ITEMS['TR']    # modesty -> Tradition
        assert 'ipshabt' in dp.PVQ21_ITEMS['AC']    # show abilities -> Achievement

    # --- Benjamini-Hochberg ---------------------------------------------------

    def test_bh_qvalues_match_statsmodels(self) -> None:
        """BH q-values match statsmodels.multipletests where available."""
        sm = pytest.importorskip('statsmodels.stats.multitest')
        rng = np.random.default_rng(3)
        p = rng.uniform(0, 1, size=40)
        _, q_ref, _, _ = sm.multipletests(p, alpha=0.05, method='fdr_bh')
        q = _bh_qvalues(p)
        np.testing.assert_allclose(q, q_ref, atol=1e-12)

    def test_bh_qvalues_monotone_and_bounded(self) -> None:
        """q-values are >= raw p, <= 1, and order-preserving."""
        p = np.array([0.001, 0.01, 0.02, 0.5, 0.9])
        q = _bh_qvalues(p)
        assert (q >= p - 1e-12).all()
        assert (q <= 1.0).all()
        assert (np.argsort(q) == np.argsort(p)).all()

    def test_bh_qvalues_handle_nan(self) -> None:
        """NaN p-values stay NaN and do not affect the others."""
        p = np.array([0.01, np.nan, 0.04])
        q = _bh_qvalues(p)
        assert np.isnan(q[1])
        assert np.isfinite(q[0]) and np.isfinite(q[2])

    # --- Pearson r baseline ----------------------------------------------------

    def test_regress_ci_matches_scipy(self) -> None:
        """_regress_ci reproduces scipy.linregress r and p."""
        rng = np.random.default_rng(7)
        x = rng.uniform(0, 10, size=60)
        y = 0.6 * x + rng.normal(0, 1, size=60)
        reg = _regress_ci(x, y)
        r_ref, p_ref = scipy_stats.pearsonr(x, y)
        assert np.isclose(reg['r'], r_ref, atol=1e-12)
        assert np.isclose(reg['p'], p_ref, atol=1e-12)

    def test_regress_ci_too_few_points(self) -> None:
        """Fewer than 4 complete pairs -> None (no fit reported)."""
        assert _regress_ci(np.array([1.0, 2.0]), np.array([1.0, 2.0])) is None


# ===========================================================================
# Section 2: Person-level scoring on synthetic microdata
# ===========================================================================

class TestPersonScores:
    """add_person_scores() behaviour on controlled synthetic data."""

    def test_centred_scores_have_zero_weighted_combination(self) -> None:
        """Each respondent's item-weighted mean of centred scores is ~0.

        The c_K are means of centred items, so the item-count-weighted
        combination over the 10 values must vanish.
        """
        df = dp.add_person_scores(_synthetic_micro())
        weights = np.array([len(dp.PVQ21_ITEMS[k]) for k in dp.VALUE_KEYS])
        c = df[[f'c_{k}' for k in dp.VALUE_KEYS]].values
        combo = (c * weights).sum(axis=1) / weights.sum()
        assert np.abs(combo).max() < 1e-9

    def test_validity_filter_drops_sparse_respondents(self) -> None:
        """Respondents with > 5 missing PVQ items are removed."""
        df = _synthetic_micro(n=50)
        df.loc[df.index[:10], dp.ALL_PVQ_ITEMS[:6]] = np.nan   # 6 missing
        out = dp.add_person_scores(df)
        assert len(out) == 40

    def test_value_score_formula(self) -> None:
        """c_K equals mean of K's reversed items minus the person mean."""
        df = _synthetic_micro(n=20)
        out = dp.add_person_scores(df)
        rev = 7 - df.loc[out.index, dp.ALL_PVQ_ITEMS]
        mrat = rev.mean(axis=1)
        for key in ('BE', 'PO'):
            expected = rev[dp.PVQ21_ITEMS[key]].mean(axis=1) - mrat
            np.testing.assert_allclose(out[f'c_{key}'].values,
                                       expected.values, atol=1e-12)

    def test_dimension_is_mean_of_member_values(self) -> None:
        """dim_* equals the mean of its constituent centred values."""
        out = dp.add_person_scores(_synthetic_micro(n=30))
        for dim, members in DIM_DELTA_FORMULA.items():
            member_c = [m.replace('d_', 'c_') for m in members]
            np.testing.assert_allclose(out[dim].values,
                                       out[member_c].mean(axis=1).values,
                                       atol=1e-12)


# ===========================================================================
# Section 3: Dashboard precomputed data (ESS11 cross-section)
# ===========================================================================

class TestDashboardPrecomputed:
    """Invariants on the dashboard/precomputed/ outputs."""

    # --- df_main ---------------------------------------------------------------

    def test_df_main_is_ess11_cross_section(self, df_main) -> None:
        """One row per ESS11 country, all for the 2023 reference year."""
        assert len(df_main) == len(dp.ESS11_COUNTRIES)
        assert set(df_main['cntry']) == set(dp.ESS11_COUNTRIES)
        assert set(df_main['year']) == {2023}
        assert df_main['cntry'].is_unique

    def test_df_main_deltas_within_radar_range(self, df_main) -> None:
        """Country Δ-scores stay inside the radar's radial axis range."""
        lo, hi = dp.DELTA_RANGE
        vals = df_main[D_COLS].values
        assert np.nanmin(vals) >= lo
        assert np.nanmax(vals) <= hi

    def test_df_main_dims_consistent_with_values(self, df_main) -> None:
        """Aggregated dim_* approximate the mean of their aggregated d_*.

        Exact equality only holds with complete item data: respondents
        missing every item of one value contribute to the dimension mean
        but not to that value's aggregate. The deviation must stay tiny
        (well below any visible difference in the dashboard).
        """
        for dim, members in DIM_DELTA_FORMULA.items():
            np.testing.assert_allclose(df_main[dim].values,
                                       df_main[members].mean(axis=1).values,
                                       atol=5e-3, err_msg=dim)

    def test_df_main_universal_value_hierarchy(self, df_main) -> None:
        """Pan-cultural pattern: Benevolence positive, Power negative.

        Schwartz & Bardi (2001): if reverse-coding or centring were wrong,
        these signs would flip - this is the regression test for the
        historical sign bug.
        """
        assert (df_main['d_BE'] > 0).all()
        assert (df_main['d_PO'] < 0).all()

    def test_df_main_sample_sizes(self, df_main) -> None:
        """Every country retains a non-trivial weighted sample."""
        assert (df_main['n'] >= 400).all()

    # --- df_scatter --------------------------------------------------------------

    def test_df_scatter_matches_df_main_dimensions(self, df_scatter,
                                                   df_main) -> None:
        """The Correlations tab uses the exact same dimension scores
        as the rest of the dashboard (the historical inconsistency fix)."""
        merged = df_scatter.merge(df_main, on='cntry',
                                  suffixes=('_s', '_m'))
        for dim in DIM_DELTA_FORMULA:
            np.testing.assert_allclose(merged[f'{dim}_s'].values,
                                       merged[f'{dim}_m'].values,
                                       atol=1e-9, err_msg=dim)

    def test_df_scatter_predictor_ranges(self, df_scatter) -> None:
        """ESS-derived predictors stay within their documented domains."""
        bounds = {
            'trust_mean': (0, 10), 'religiosity_mean': (0, 10),
            'lrscale_mean': (0, 10), 'safety_mean': (1, 4),
            'urban_pct': (0, 100), 'diversity_pct': (0, 100),
            'eduyrs_mean': (3, 25), 'age_mean': (15, 100),
            'v2x_libdem': (0, 1), 'wb_gini': (15, 70),
        }
        for col, (lo, hi) in bounds.items():
            vals = df_scatter[col].dropna()
            assert vals.min() >= lo, f'{col} min {vals.min()}'
            assert vals.max() <= hi, f'{col} max {vals.max()}'

    # --- df_regional --------------------------------------------------------------

    def test_df_regional_region_codes(self, df_regional) -> None:
        """Regions are DE NUTS-1 or CH NUTS-2 codes, unique per country."""
        assert df_regional['region'].str.match(r'^(DE.|CH..)$').all()
        assert not df_regional.duplicated(['cntry', 'region']).any()

    def test_df_regional_min_n_flag(self, df_regional) -> None:
        """below_min_n is exactly n < MIN_REGION_N."""
        expected = df_regional['n'] < dp.MIN_REGION_N
        assert (df_regional['below_min_n'] == expected).all()

    def test_df_regional_scores_plausible(self, df_regional) -> None:
        """Regional Δ-scores stay within a plausible band around 0."""
        reliable = df_regional[~df_regional['below_min_n']]
        assert reliable[D_COLS].abs().values.max() < 2.0

    # --- df_gradients ---------------------------------------------------------------

    def test_df_gradients_group_sizes(self, df_gradients) -> None:
        """All gradient groups satisfy the minimum group size."""
        assert (df_gradients['n'] >= dp.MIN_GROUP_N).all()

    def test_df_gradients_variables_known(self, df_gradients) -> None:
        """Each gradient variable key exists in GRADIENT_VARS."""
        assert set(df_gradients['variable']) <= set(dp.GRADIENT_VARS)

    def test_df_gradients_country_specific_vars(self, df_gradients) -> None:
        """East/West only for DE; language regions only for CH."""
        east_west = df_gradients[df_gradients['variable'] == 'region_block']
        language = df_gradients[df_gradients['variable'] == 'language']
        assert set(east_west['cntry']) <= {'DE'}
        assert set(language['cntry']) <= {'CH'}

    # --- regional indicators / geojson / MLM ------------------------------------------

    def test_regional_indicators_known_keys(self, df_reg_ind) -> None:
        """Indicator keys match the metadata used by the UI."""
        assert set(df_reg_ind['indicator']) <= set(dp.REGIONAL_INDICATOR_META)
        assert (df_reg_ind['value'] > 0).all()
        assert df_reg_ind['year'].between(2015, 2026).all()

    def test_geojson_features(self, geojson) -> None:
        """GeoJSON holds the DE NUTS-1 + CH NUTS-2 features exactly once."""
        ids = [f['properties']['NUTS_ID'] for f in geojson['features']]
        assert len(ids) == len(set(ids))
        assert sum(i.startswith('DE') for i in ids) == 16   # incl. Bremen
        assert sum(i.startswith('CH') for i in ids) == 7

    def test_mlm_results_structure(self, mlm_results) -> None:
        """Four dimension models with sane ICCs and full coefficient sets."""
        models = mlm_results['models']
        assert set(models) == set(dp.DIM_COLS.values())
        for model in models.values():
            assert 0.0 < model['icc'] < 0.5
            assert model['n_obs'] > 40_000
            assert len(model['coefficients']) == 7
            for coef in model['coefficients']:
                assert 0.0 <= coef['p'] <= 1.0
                assert coef['se'] > 0

    # --- PCA / clustering ----------------------------------------------------------------

    def test_pca_clustering_returns_validation(self, df_main) -> None:
        """compute_pca_clustering yields silhouette scores for k = 2..6."""
        result, explained, _, _, validation = dp.compute_pca_clustering(
            df_main, n_clusters=3, dim_group='values')
        assert result is not None and len(result) == len(df_main)
        assert 0 < explained[0] <= 1
        assert set(validation['scores']) == {2, 3, 4, 5, 6}
        assert all(-1 <= s <= 1 for s in validation['scores'].values())
        assert validation['best_k'] in validation['scores']


# ===========================================================================
# Section 4: Final analysis dataset (legacy research output, unchanged)
# ===========================================================================

class TestFinalAnalysisDataset:
    """Structural invariants on macro_schwartz_analysis_data.csv."""

    def test_main_csv_loads(self, df_main_csv) -> None:
        assert len(df_main_csv) > 0
        assert {'cntry', 'year'} <= set(df_main_csv.columns)

    def test_main_csv_no_duplicate_country_year(self, df_main_csv) -> None:
        assert df_main_csv.duplicated(subset=['cntry', 'year']).sum() == 0

    def test_main_csv_years_within_ess_reference(self, df_main_csv) -> None:
        unexpected = set(df_main_csv['year']) - ESS_REFERENCE_YEARS
        assert not unexpected, f'unexpected years: {unexpected}'

    def test_main_csv_countries_within_universe(self, df_main_csv) -> None:
        unknown = set(df_main_csv['cntry']) - EXPECTED_COUNTRIES
        assert not unknown, f'unknown country codes: {unknown}'

    def test_main_csv_pvq_means_in_valid_range(self, df_main_csv) -> None:
        pvq_cols = [c for c in df_main_csv.columns
                    if c.startswith('ip') and c.endswith('_mean')]
        assert pvq_cols
        for col in pvq_cols:
            vals = df_main_csv[col].dropna()
            if vals.empty:
                continue
            assert vals.min() >= 1.0
            assert vals.max() <= 6.0

    def test_main_csv_macro_ranges(self, df_main_csv) -> None:
        bounds = {
            'v2x_libdem': (0.0, 1.0),
            'wb_gini': (15.0, 70.0),
            'wb_unemployment': (0.0, 30.0),
            'wb_gdp_per_capita_ppp': (1000.0, 200_000.0),
        }
        for col, (lo, hi) in bounds.items():
            if col not in df_main_csv.columns:
                continue
            vals = df_main_csv[col].dropna()
            assert vals.min() >= lo, f'{col} min {vals.min()}'
            assert vals.max() <= hi, f'{col} max {vals.max()}'


# ===========================================================================
# Section 5: Cross-dataset consistency
# ===========================================================================

class TestCrossDatasetConsistency:
    """Checks that span more than one precomputed file."""

    def test_scatter_countries_equal_main(self, df_scatter, df_main) -> None:
        """The correlation cross-section covers exactly the ESS11 countries."""
        assert set(df_scatter['cntry']) == set(df_main['cntry'])

    def test_regional_countries_are_deep_dive(self, df_regional) -> None:
        """Regional aggregates exist only for the deep-dive countries."""
        assert set(df_regional['cntry']) == set(dp.DEEP_DIVE_COUNTRIES)

    def test_gradients_countries_are_deep_dive(self, df_gradients) -> None:
        assert set(df_gradients['cntry']) == set(dp.DEEP_DIVE_COUNTRIES)

    def test_geojson_covers_regional_rows(self, geojson, df_regional) -> None:
        """Every regional aggregate has a matching boundary feature."""
        ids = {f['properties']['NUTS_ID'] for f in geojson['features']}
        missing = set(df_regional['region']) - ids
        assert not missing, f'regions without geometry: {missing}'

    def test_indicator_regions_covered_by_geojson(self, geojson,
                                                  df_reg_ind) -> None:
        ids = {f['properties']['NUTS_ID'] for f in geojson['features']}
        missing = set(df_reg_ind['region']) - ids
        assert not missing, f'indicator regions without geometry: {missing}'
