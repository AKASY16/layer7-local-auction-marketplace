"""End-time sensitivity experiments on the frozen baseline (baseline-v4).

Nothing here changes the generator; variations go through config overrides.

E1  policy level: 6 end-time assignments x 6 scenarios x 5 seeds, paired with the
    seller-default run of the same world (common random numbers).
E2  auction level: in each run 10% of auctions are moved to a random allowed end
    time; their outcome change is regressed on the change in (assumed) buyer
    activity at the end hour and in same-series conflicts within +-3 h.
    Unmoved auctions measure spillover.
E3  assumption sensitivity: E1 policies under alternative values of the ASSUMED
    drivers (scenario B, seeds 1-3). Does the policy ranking survive?

Decision criteria were fixed before running (see sensitivity_report.md, section 1).

  python validation/sensitivity.py [--workers 6]
"""
import argparse
import json
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation" / "sensitivity"
SCEN = ROOT / "config" / "scenarios"
POLICIES = ["seller_default", "uniform_any", "evening_spread", "concentrate_21", "night_03", "batch_days"]
E3_VARIANTS = {
    "B_base": {},
    "hour_blend_0.5": {"buyer_hour_blend_flat": 0.5},
    "hour_blend_0.9": {"buyer_hour_blend_flat": 0.9},
    "thickness_0": {"param_overrides": {"thickness_elasticity": 0.0}},
    "thickness_0.47_att1": {"param_overrides": {"thickness_elasticity": 0.47, "attention_thickness_elasticity": 1.0}},
    "substitution_0.3": {"similarity": {"same_series": 0.3, "same_subcategory": 0.1, "same_category": 0.0}},
    "substitution_0.95": {"similarity": {"same_series": 0.95, "same_subcategory": 0.6, "same_category": 0.2}},
    "appeal_wtp_0.5": {"param_overrides": {"appeal_wtp_elasticity": 0.5}},
}


def _imports():
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "validation"))
    import config as C
    import market_simulator as MS
    import mechanism_check as MC
    import world as W
    return C, MS, MC, W


def policy_ends(name, w, MC):
    if name == "seller_default":
        return {a["auction_id"]: a["default_end_at"] for a in w.auctions}
    if name == "uniform_any":
        return MC.spread(w)
    if name == "evening_spread":
        return MC.spread_evening(w)
    if name == "concentrate_21":
        return MC.concentrate(w, 21)
    if name == "night_03":
        return MC.concentrate(w, 3)
    if name == "batch_days":
        return MC.batch_days(w)
    raise ValueError(name)


def per_auction(m, w):
    val = {it["item_id"]: it["estimated_value"] for it in w.items}
    ids = sorted(m.auc)
    sold = np.array([m.auc[i]["leader"] is not None for i in ids])
    rev = np.array([(m.auc[i]["price"] / val[m.auc[i]["item_id"]]) if m.auc[i]["leader"] is not None else 0.0
                    for i in ids])
    bidders = np.array([len(m.auc[i]["bidders"]) for i in ids], float)
    return ids, sold, rev, bidders


def summary(sold, rev, bidders):
    return {"revenue_over_value_mean": float(rev.mean()), "sold": float(sold.mean()),
            "bidders": float(bidders.mean()),
            "price_over_value_sold": float(rev[sold].mean()) if sold.any() else None}


def job_policy(args):
    scen, seed, overrides, policies = args
    C, MS, MC, W = _imports()
    cfg = C.load(SCEN / f"scenario_{scen}.yaml", overrides=overrides)
    w = W.build(cfg, seed)
    out = {}
    for pol in policies:
        m = MS.simulate(w, policy_ends(pol, w, MC), seed)
        out[pol] = summary(*per_auction(m, w)[1:])
    return scen, seed, json.dumps(overrides, sort_keys=True), out


def conflicts(w, ends, window=180.0):
    grp = {}
    for it in w.items:
        grp.setdefault(it["similarity_group"], []).append(it["item_id"])
    c = {}
    for ids in grp.values():
        e = np.array([ends[i] for i in ids])
        for k, i in enumerate(ids):
            c[i] = int((np.abs(e - e[k]) <= window).sum() - 1)
    return c


def job_shift(args):
    scen, seed, n_runs, share = args
    C, MS, MC, W = _imports()
    cfg = C.load(SCEN / f"scenario_{scen}.yaml")
    w = W.build(cfg, seed)
    prof = w.buyer_hour_profile
    base = {a["auction_id"]: a["default_end_at"] for a in w.auctions}
    m0 = MS.simulate(w, base, seed)
    ids, s0, r0, b0 = per_auction(m0, w)
    c0 = conflicts(w, base)
    rows, spill = [], []
    for r in range(n_runs):
        rng = np.random.default_rng([seed, 7000 + r, ord(scen)])
        moved = set(rng.choice(ids, size=int(share * len(ids)), replace=False).tolist())
        ends = dict(base)
        for a in w.auctions:
            if a["auction_id"] in moved:
                ends[a["auction_id"]] = a["start_at"] + 1440 + float(rng.random()) * 2880
        m1 = MS.simulate(w, ends, seed)
        _, s1, r1, b1 = per_auction(m1, w)
        c1 = conflicts(w, ends)
        for k, i in enumerate(ids):
            if i in moved:
                rows.append([r1[k] - r0[k], b1[k] - b0[k],
                             prof[w.hour_of(ends[i])] - prof[w.hour_of(base[i])], c1[i] - c0[i],
                             r0[k], w.hour_of(ends[i])])
        un = np.array([i not in moved for i in ids])
        spill.append({"mean_abs_delta_rev_unmoved": float(np.abs(r1 - r0)[un].mean()),
                      "mean_delta_rev_unmoved": float((r1 - r0)[un].mean()),
                      "share_unmoved_identical": float(((r1 == r0) & (b1 == b0))[un].mean()),
                      "total_rev_delta": float((r1 - r0).sum())})
    return scen, seed, rows, spill


def ols(y, X):
    X1 = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    res = y - X1 @ beta
    n, k = X1.shape
    s2 = res @ res / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X1.T @ X1)))
    r2 = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    return beta.tolist(), se.tolist(), float(r2)


def paired(results, policies, ref="seller_default"):
    """results: list of {policy: summary} for seeds of one cell -> effect vs ref."""
    out = {}
    for pol in policies:
        if pol == ref:
            continue
        out[pol] = {}
        for k in ("revenue_over_value_mean", "bidders", "sold"):
            d = np.array([r[pol][k] - r[ref][k] for r in results])
            sd = d.std(ddof=1) if len(d) > 1 else float("nan")
            out[pol][k] = {"mean": float(d.mean()), "sd": float(sd),
                           "snr": float(d.mean() / sd) if sd > 0 else float("inf")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    with ProcessPoolExecutor(a.workers) as ex:
        # E1
        e1 = list(ex.map(job_policy, [(s, sd, {}, POLICIES) for s in "ABCDEF" for sd in (1, 2, 3, 4, 5)]))
        cells = {}
        for s, sd, _, out in e1:
            cells.setdefault(s, []).append(out)
        res["E1"] = {s: {"levels_seed_mean": {p: {k: float(np.mean([r[p][k] for r in rs if r[p][k] is not None]))
                                                 for k in rs[0][p]} for p in POLICIES},
                         "effects_vs_default": paired(rs, POLICIES),
                         "ranking_by_revenue": sorted(POLICIES, key=lambda p: -np.mean([r[p]["revenue_over_value_mean"] for r in rs])),
                         "best_policy_per_seed": [max(POLICIES, key=lambda p: r[p]["revenue_over_value_mean"]) for r in rs]}
                     for s, rs in cells.items()}
        print("E1 done", flush=True)
        # E2
        e2 = list(ex.map(job_shift, [(s, sd, 8, 0.10) for s in "ABCDE" for sd in (1, 2)]))
        res["E2"] = {}
        for s in "ABCDE":
            rows = np.array([r for sc, sd, rr, sp in e2 if sc == s for r in rr], float)
            spill = [x for sc, sd, rr, sp in e2 if sc == s for x in sp]
            dy, db, dh, dc = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3]
            b_rev = ols(dy, np.column_stack([dh, dc]))
            b_bid = ols(db, np.column_stack([dh, dc]))
            hours = rows[:, 5].astype(int)
            band = {f"{h0:02d}-{h0 + 6:02d}": float(dy[(hours >= h0) & (hours < h0 + 6)].mean()) for h0 in (0, 6, 12, 18)}
            res["E2"][s] = {
                "n_moves": int(len(rows)),
                "delta_rev_per_move": {"mean": float(dy.mean()), "sd": float(dy.std(ddof=1)),
                                       "q10": float(np.quantile(dy, 0.1)), "q90": float(np.quantile(dy, 0.9))},
                "ols_delta_rev_on_dhourweight_dconflict": {"beta": b_rev[0], "se": b_rev[1], "r2": b_rev[2]},
                "ols_delta_bidders_on_dhourweight_dconflict": {"beta": b_bid[0], "se": b_bid[1], "r2": b_bid[2]},
                "mean_delta_rev_by_new_end_hour_band": band,
                "spillover": {k: float(np.mean([x[k] for x in spill])) for k in spill[0]},
            }
        print("E2 done", flush=True)
        # E3
        pols3 = ["seller_default", "uniform_any", "evening_spread", "concentrate_21", "night_03"]
        e3 = list(ex.map(job_policy, [("B", sd, ov, pols3) for ov in E3_VARIANTS.values() for sd in (1, 2, 3)]))
        res["E3"] = {}
        for name, ov in E3_VARIANTS.items():
            key = json.dumps(ov, sort_keys=True)
            rs = [out for s, sd, k, out in e3 if k == key]
            res["E3"][name] = {"overrides": ov, "effects_vs_default": paired(rs, pols3),
                               "ranking_by_revenue": sorted(pols3, key=lambda p: -np.mean([r[p]["revenue_over_value_mean"] for r in rs])),
                               "levels_seed_mean": {p: float(np.mean([r[p]["revenue_over_value_mean"] for r in rs])) for p in pols3}}
        print("E3 done", flush=True)
    (OUT / "sensitivity_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", OUT / "sensitivity_results.json")


if __name__ == "__main__":
    main()
