"""Independent-world uncertainty; auction regressions are exploratory only."""
import numpy as np
from scipy.stats import t


def paired_seed_summary(differences, seed_ids):
    d = np.asarray(differences, float)
    if len(d) != len(seed_ids) or len(set(seed_ids)) != len(seed_ids):
        raise ValueError('Exactly one paired difference per independent seed is required')
    if len(d) < 2 or not np.isfinite(d).all():
        raise ValueError('At least two finite independent seed differences are required')
    sd = float(d.std(ddof=1))
    se = sd / np.sqrt(len(d))
    mean = float(d.mean())
    margin = float(t.ppf(.975, len(d)-1) * se)
    rng = np.random.default_rng(20261030)
    boot = d[rng.integers(0, len(d), size=(5000, len(d)))].mean(axis=1)
    return {'n_independent_worlds': len(d), 'mean': mean, 'sd_between_worlds': sd,
            'se_of_mean': float(se), 'ci95_t': [mean-margin, mean+margin],
            'ci95_seed_bootstrap_percentile': np.quantile(boot, [.025, .975]).tolist(),
            'per_seed': dict(zip(map(str, seed_ids), d.tolist())),
            'interpretation': 'Monte Carlo uncertainty conditional on this model and configuration; not real-market uncertainty.'}


def exploratory_cluster_ols(y, x, groups):
    from statsmodels.api import OLS, add_constant
    from statsmodels.stats.sandwich_covariance import cov_cluster
    y, x, groups = np.asarray(y, float), np.asarray(x, float), np.asarray(groups)
    if len(y) != len(x) or len(y) != len(groups) or not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError('Mismatched or nonfinite regression inputs')
    design = add_constant(x, has_constant='add')
    clusters = len(np.unique(groups))
    if clusters < 2 or np.linalg.matrix_rank(design) < design.shape[1]:
        return {'estimable': False, 'n_clusters': clusters, 'reason': 'Insufficient clusters or rank-deficient design'}
    fit = OLS(y, design).fit()
    covariance = cov_cluster(fit, groups, use_correction=True)
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    margin = t.ppf(.975, clusters-1) * se
    return {'estimable': True, 'n_rows': len(y), 'n_clusters': clusters,
            'beta': fit.params.tolist(), 'naive_iid_se_for_comparison_only': fit.bse.tolist(),
            'seed_cluster_se': se.tolist(), 'ci95_seed_cluster_t':
            np.column_stack([fit.params-margin, fit.params+margin]).tolist(),
            'cluster_df': clusters-1, 'r2': float(fit.rsquared),
            'interpretation': 'Exploratory association under interference; small-cluster approximation, not a direct collision causal effect.'}
