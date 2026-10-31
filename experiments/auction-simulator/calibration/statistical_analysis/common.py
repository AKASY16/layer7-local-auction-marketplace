"""Shared paths and helpers for the statistical analysis scripts."""
import json
import os
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

DATA = Path(os.environ.get("LAYER7_DATA", Path.home() / "Desktop" / "Data"))
OUT = ROOT / "calibration" / "statistical_analysis" / "results"
FIG = ROOT / "calibration" / "statistical_analysis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def is_holdout(key, share=0.3):
    """Deterministic 70/30 split by id (crc32), same on every machine."""
    return (zlib.crc32(str(key).encode()) % 1000) < share * 1000


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.ndarray):
        return to_jsonable(o.tolist())
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def save(name, obj):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(to_jsonable(obj), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", p)


def describe(x, qs=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99)):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    d = {"n": len(x), "mean": x.mean(), "sd": x.std(ddof=1) if len(x) > 1 else 0.0,
         "min": x.min(), "max": x.max()}
    for q in qs:
        d[f"q{int(q * 100)}"] = float(np.quantile(x, q))
    return d


def fit_counts(k, zero_truncated=False):
    """Compare Poisson, negative binomial and geometric fits for count data.

    Returns parameters, log-likelihood, AIC and BIC so the choice is made by data.
    With zero_truncated=True the pmf is renormalised over k >= 1 (used for
    data where zero-bid auctions are not observed).
    """
    k = np.asarray(k, int)
    n = len(k)
    res = {}

    def trunc(logpmf0):
        return np.log1p(-np.exp(logpmf0)) if zero_truncated else 0.0

    # Poisson
    def nll_p(t):
        lam = np.exp(t[0])
        return -(stats.poisson.logpmf(k, lam).sum() - n * trunc(stats.poisson.logpmf(0, lam)))
    r = optimize.minimize(nll_p, [np.log(max(k.mean(), 0.1))], method="L-BFGS-B")
    res["poisson"] = {"lambda": float(np.exp(r.x[0])), "loglik": -r.fun, "k": 1}

    # NB with mean mu and size r (var = mu + mu^2 / r)
    def nll_nb(t):
        mu, size = np.exp(t)
        p = size / (size + mu)
        return -(stats.nbinom.logpmf(k, size, p).sum() - n * trunc(stats.nbinom.logpmf(0, size, p)))
    best = None
    for s0 in (0.5, 2.0, 10.0):
        r = optimize.minimize(nll_nb, [np.log(max(k.mean(), 0.1)), np.log(s0)], method="L-BFGS-B",
                              bounds=[(-5, 10), (-6, 8)])
        if best is None or r.fun < best.fun:
            best = r
    mu, size = np.exp(best.x)
    res["negbin"] = {"mu": float(mu), "size": float(size), "loglik": -best.fun, "k": 2}

    # geometric (NB with size 1)
    def nll_g(t):
        mu = np.exp(t[0])
        p = 1 / (1 + mu)
        return -(stats.nbinom.logpmf(k, 1, p).sum() - n * trunc(stats.nbinom.logpmf(0, 1, p)))
    r = optimize.minimize(nll_g, [np.log(max(k.mean(), 0.1))], method="L-BFGS-B")
    res["geometric"] = {"mu": float(np.exp(r.x[0])), "loglik": -r.fun, "k": 1}

    for v in res.values():
        v["aic"] = 2 * v["k"] - 2 * v["loglik"]
        v["bic"] = v["k"] * np.log(n) - 2 * v["loglik"]
    res["best_by_aic"] = min((m for m in res if isinstance(res[m], dict)), key=lambda m: res[m]["aic"])
    res["n"] = n
    res["zero_truncated"] = zero_truncated
    return res


def fit_positive(x):
    """Compare lognormal, gamma, Weibull and exponential fits for positive data."""
    x = np.asarray(x, float)
    x = x[x > 0]
    n = len(x)
    res = {}
    cands = {"lognorm": (stats.lognorm, {"floc": 0}), "gamma": (stats.gamma, {"floc": 0}),
             "weibull": (stats.weibull_min, {"floc": 0}), "expon": (stats.expon, {"floc": 0})}
    for name, (dist, kw) in cands.items():
        try:
            p = dist.fit(x, **kw)
            ll = dist.logpdf(x, *p).sum()
            k = len(p) - 1
            res[name] = {"params": [float(v) for v in p], "loglik": float(ll), "k": k,
                         "aic": 2 * k - 2 * ll, "bic": k * np.log(n) - 2 * ll,
                         "ks_D": float(stats.kstest(x, dist.cdf, args=p).statistic)}
        except Exception as e:  # keep the comparison going
            res[name] = {"error": str(e)}
    ok = [m for m in res if "aic" in res[m]]
    res["best_by_aic"] = min(ok, key=lambda m: res[m]["aic"])
    res["n"] = n
    if "lognorm" in res and "params" in res["lognorm"]:
        res["lognorm_mu_log"] = float(np.log(res["lognorm"]["params"][2]))
        res["lognorm_sigma_log"] = float(res["lognorm"]["params"][0])
    return res


def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))
