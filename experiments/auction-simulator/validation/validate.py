"""Validate generated datasets: structure, statistics vs real data, BARISTA, reproducibility,
and the end-time re-simulation path.

  python validation/validate.py            # all data/synthetic/scenario_*/seed_*
  python validation/validate.py --root data/smoke

Writes validation/results.json and figures in validation/figures/.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import barista  # noqa: E402
import config as C  # noqa: E402
import generate as G  # noqa: E402
import market_simulator as MS  # noqa: E402
import world as W  # noqa: E402

RES = ROOT / "calibration" / "statistical_analysis" / "results"
FIG = ROOT / "validation" / "figures"


def mins(series, origin):
    return (pd.to_datetime(series, format="ISO8601") - origin).dt.total_seconds() / 60.0


def load(d):
    t = {n: pd.read_csv(d / f"{n}.csv") for n in ("sellers", "items", "buyers", "auctions", "visits", "bids", "outcomes")}
    t["latent"] = pd.read_csv(d / "hidden" / "buyers_latent.csv")
    t["meta"] = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    o = pd.Timestamp(datetime.fromisoformat(t["meta"]["origin"]))
    a = t["auctions"]
    a["start_m"], a["end_m"] = mins(a["start_at"], o), mins(a["scheduled_end_at"], o)
    a["actual_m"] = mins(a["actual_end_at"], o)
    b = t["bids"]
    if len(b):
        b["t"] = b["bid_time_min"]
    t["origin"] = o
    return t


# --------------------------------------------------------------------------- structure
def structural(t, cfg):
    a, b, o, it, by, lat = t["auctions"], t["bids"], t["outcomes"], t["items"], t["buyers"], t["latent"]
    inc_table = [(None if u is None else float(u), float(i)) for u, i in cfg["increment_table_krw"]]
    r = {}
    r["ids_unique"] = bool(a["auction_id"].is_unique and it["item_id"].is_unique and by["buyer_id"].is_unique
                           and (b["bid_id"].is_unique if len(b) else True))
    r["fk_auction_seller"] = bool(a["seller_id"].isin(t["sellers"]["seller_id"]).all())
    r["fk_auction_item"] = bool(a["item_id"].isin(it["item_id"]).all())
    r["fk_bid_auction"] = bool(b["auction_id"].isin(a["auction_id"]).all())
    r["fk_bid_buyer"] = bool(b["buyer_id"].isin(by["buyer_id"]).all())
    v = t["visits"]
    r["fk_visit_buyer"] = bool(v["buyer_id"].isin(by["buyer_id"]).all())
    r["fk_visit_auction"] = bool(v["auction_id"].dropna().isin(a["auction_id"]).all())
    r["outcomes_1to1"] = bool(len(o) == len(a) and set(o["auction_id"]) == set(a["auction_id"]))
    dur = (a["end_m"] - a["start_m"]) / 60
    r["duration_24_72h"] = bool(((dur >= 24 - 1e-6) & (dur <= 72 + 1e-6)).all())
    m = b.merge(a[["auction_id", "start_m", "end_m"]], on="auction_id")
    tol = 1 / 60  # one second (timestamps are written to the second)
    r["bids_inside_window"] = int(((m["t"] < m["start_m"] - tol) | (m["t"] > m["end_m"] + tol)).sum()) == 0
    r["hard_close_actual_eq_scheduled"] = bool((abs(a["actual_m"] - a["end_m"]) < tol).all()) \
        if cfg.get("close_rule", "hard") == "hard" else None

    # replay every auction with the proxy rule and every buyer's budget in time order
    start_price = a.set_index("auction_id")["starting_price"].to_dict()
    end_t = a.set_index("auction_id")["end_m"].to_dict()
    budget = lat.set_index("buyer_id")["budget_krw"].to_dict()
    st = {k: {"price": None, "leader": None, "max": 0.0} for k in start_price}
    spent, committed = {k: 0.0 for k in budget}, {k: 0.0 for k in budget}
    viol = {"min_increment": 0, "price_path": 0, "leader_path": 0, "budget_at_bid": 0}
    evs = [(row.t, 0, row) for row in b.itertuples()] + [(end_t[k], 1, k) for k in end_t]
    evs.sort(key=lambda e: (e[0], e[1]))
    for _, kind, x in evs:
        if kind == 1:
            s = st[x]
            if s["leader"] is not None:
                committed[s["leader"]] -= s["max"]
                spent[s["leader"]] += s["price"]
            continue
        s, bid, amt = st[x.auction_id], x.buyer_id, x.bid_amount
        need = start_price[x.auction_id] if s["price"] is None else s["price"] + MS.increment(s["price"], inc_table)
        if s["leader"] != bid and amt + 1e-6 < need:
            viol["min_increment"] += 1
        own = s["max"] if s["leader"] == bid else 0.0
        if amt > budget[bid] - spent[bid] - (committed[bid] - own) + 1e-6:
            viol["budget_at_bid"] += 1
        if s["price"] is None:
            s["price"], s["leader"], s["max"] = start_price[x.auction_id], bid, amt
            committed[bid] += amt
        elif amt > s["max"]:
            s["price"] = min(amt, s["max"] + MS.increment(s["max"], inc_table))
            if s["leader"] == bid:
                committed[bid] += amt - s["max"]
            else:
                committed[s["leader"]] -= s["max"]
                committed[bid] += amt
            s["leader"], s["max"] = bid, amt
        else:
            s["price"] = min(s["max"], amt + MS.increment(amt, inc_table))
        if abs(s["price"] - x.price_after) > 1e-6:
            viol["price_path"] += 1
        if (s["leader"] == bid) != bool(x.leader_after_is_bidder):
            viol["leader_path"] += 1
    r.update({f"violations_{k}": v for k, v in viol.items()})
    oo = o.set_index("auction_id")
    win_ok = price_ok = 0
    for k, s in st.items():
        row = oo.loc[k]
        if s["leader"] is None:
            win_ok += int(pd.isna(row["winner_id"]) and not bool(row["sold"]) and row["bid_count"] == 0)
            price_ok += int(pd.isna(row["winning_price"]))
        else:
            win_ok += int(row["winner_id"] == s["leader"] and bool(row["sold"]))
            price_ok += int(abs(row["winning_price"] - s["price"]) < 1e-6)
    r["winner_matches_replay"] = win_ok == len(st)
    r["price_matches_replay"] = price_ok == len(st)
    r["n_zero_bid_auctions"] = int((o["bid_count"] == 0).sum())
    r["zero_bid_handled"] = bool(((o["bid_count"] == 0) == o["winner_id"].isna()).all())
    pay = o.dropna(subset=["winner_id"]).groupby("winner_id")["winning_price"].sum()
    r["budget_total_respected"] = bool((pay <= lat.set_index("buyer_id").loc[pay.index, "budget_krw"] + 1e-6).all())
    r["bid_count_matches"] = bool((b.groupby("auction_id").size().reindex(o["auction_id"], fill_value=0).values
                                   == o["bid_count"].values).all())
    flags = [v for k, v in r.items() if isinstance(v, bool)]
    counts = [v for k, v in r.items() if k.startswith("violations_")]
    r["all_pass"] = all(flags) and all(c == 0 for c in counts)
    return r


# --------------------------------------------------------------------------- statistics
def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())) if n and x.sum() else float("nan")


def moments(t):
    a, b, o, it, v = t["auctions"], t["bids"], t["outcomes"], t["items"], t["visits"]
    m = b.merge(a[["auction_id", "start_m", "end_m", "category"]], on="auction_id")
    m["tte"] = m["end_m"] - m["t"]
    m["u"] = (m["t"] - m["start_m"]) / (m["end_m"] - m["start_m"])
    pos = o[o["bid_count"] > 0]
    pair = m.groupby(["auction_id", "buyer_id"]).size()
    last = m.groupby("auction_id")["tte"].min()
    sold = o[o["sold"]].merge(a[["auction_id", "item_id", "category"]], on="auction_id").merge(
        it[["item_id", "estimated_value"]], on="item_id")
    sold["lp"] = np.log(sold["winning_price"])
    X = np.column_stack([np.ones(len(sold)), np.log(sold["bid_count"]),
                         pd.get_dummies(sold["category"], drop_first=True).values.astype(float)])
    slope_pb = float(np.linalg.lstsq(X, sold["lp"].values, rcond=None)[0][1])
    views = v[v["event_type"] == "view"].groupby("auction_id").size().reindex(a["auction_id"], fill_value=0)
    nb = o.set_index("auction_id")["bid_count"].reindex(a["auction_id"])
    slope_vb = float(np.polyfit(np.log1p(views.values), np.log1p(nb.values), 1)[0])
    mu, var = pos["bid_count"].mean(), pos["bid_count"].var()
    visits = v[v["event_type"] == "visit"].copy()
    hours = pd.to_datetime(visits["event_time"], format="ISO8601").dt.hour
    return {
        "share_zero_bid": float((o["bid_count"] == 0).mean()),
        "bids_per_auction_mean_pos": float(mu), "bidders_per_auction_mean_pos": float(pos["unique_bidder_count"].mean()),
        "bids_per_auction_nb_size_mom": float(mu ** 2 / (var - mu)) if var > mu else float("inf"),
        "bids_per_bidder_in_auction_mean": float(pair.mean()), "share_repeat_bidder_pairs": float((pair >= 2).mean()),
        "share_bids_last_5min": float((m["tte"] <= 5).mean()), "share_bids_last_60min": float((m["tte"] <= 60).mean()),
        "share_bids_first_10pct": float((m["u"] <= 0.1).mean()),
        "share_auctions_last_bid_5min": float((last <= 5).mean()),
        "gini_bids_per_bidder": gini(m.groupby("buyer_id").size().values),
        "slope_log_price_log_bids_sold": slope_pb, "slope_log1p_bids_log1p_views": slope_vb,
        "winning_over_estimated_median": float((sold["winning_price"] / sold["estimated_value"]).median()),
        "log_price_sd_by_category": sold.groupby("category")["lp"].std().to_dict(),
        "visit_hour_share": hours.value_counts(normalize=True).sort_index().to_dict(),
        "u_hist20": np.histogram(m["u"].clip(0, 1), bins=20, range=(0, 1))[0].tolist(),
        "u_values_sample": m["u"].clip(0, 1).sample(min(len(m), 4000), random_state=0).tolist(),
    }


def dilution(t, window_h=3):
    """Bidders vs number of same-series auctions ending within +-window (observed data only)."""
    a = t["auctions"].merge(t["items"][["item_id", "series"]], on="item_id").merge(
        t["outcomes"][["auction_id", "unique_bidder_count"]], on="auction_id")
    a = a.sort_values("end_m")
    conc = []
    for r in a.itertuples():
        g = a[(a["series"] == r.series) & (a["auction_id"] != r.auction_id)]
        conc.append(int((abs(g["end_m"] - r.end_m) <= window_h * 60).sum()))
    a["n_concurrent_same_series"] = conc
    x, y = np.log1p(a["n_concurrent_same_series"]), np.log1p(a["unique_bidder_count"])
    slope = float(np.polyfit(x, y, 1)[0]) if x.std() > 0 else float("nan")
    rho = float(stats.spearmanr(a["n_concurrent_same_series"], a["unique_bidder_count"]).statistic)
    return {"slope_log1p_bidders_on_log1p_concurrent": slope, "spearman": rho,
            "mean_concurrent": float(a["n_concurrent_same_series"].mean())}


def file_hashes(d):
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*.csv"))}


# --------------------------------------------------------------------------- counterfactual plumbing
def counterfactual_check(scen_path, seed):
    """Same world, two end-time assignments. Checks the coupling, not which policy is better."""
    cfg = C.load(scen_path)
    w = W.build(cfg, seed)
    base = {a["auction_id"]: a["default_end_at"] for a in w.auctions}
    m0 = MS.simulate(w, base, seed)
    m0b = MS.simulate(w, base, seed)
    same = [x["bid_time"] for x in m0.bids] == [x["bid_time"] for x in m0b.bids]
    alt = dict(base)
    moved = []
    for a in w.auctions:
        e = base[a["auction_id"]]
        if w.hour_of(e) in (19, 20, 21, 22):
            new = e - 6 * 60
            if new >= a["start_at"] + 24 * 60:
                alt[a["auction_id"]] = new
                moved.append(a["auction_id"])
    w2 = W.build(cfg, seed)  # rebuild to show the world is a pure function of (config, seed)
    world_same = all(np.array_equal(x["cand_t"], y["cand_t"]) and np.array_equal(x["cand_u"], y["cand_u"])
                     for x, y in zip(w.buyers, w2.buyers))
    m1 = MS.simulate(w2, alt, seed)

    def summary(m, ids):
        pr = [m.auc[i]["price"] for i in ids if m.auc[i]["leader"] is not None]
        return {"n": len(ids), "sold": float(np.mean([m.auc[i]["leader"] is not None for i in ids])),
                "mean_bidders": float(np.mean([len(m.auc[i]["bidders"]) for i in ids])),
                "mean_price": float(np.mean(pr)) if pr else None}
    unmoved = [i for i in base if i not in set(moved)]
    ident = float(np.mean([(m0.auc[i]["price"], m0.auc[i]["leader"]) == (m1.auc[i]["price"], m1.auc[i]["leader"])
                           for i in unmoved]))
    wtp_same = all(m0.wtp_log[k] == v for k, v in m1.wtp_log.items() if k in m0.wtp_log)
    return {"scenario": cfg["scenario"]["id"], "seed": seed,
            "rerun_same_ends_identical_bids": same, "world_rebuild_identical_visit_stream": world_same,
            "valuations_identical_for_shared_pairs": wtp_same,
            "policy": "auctions ending 19-22h KST moved 6 h earlier when still >= 24 h after start",
            "n_moved": len(moved), "moved_before": summary(m0, moved), "moved_after": summary(m1, moved),
            "unmoved_before": summary(m0, unmoved), "unmoved_after": summary(m1, unmoved),
            "share_unmoved_with_identical_outcome": ident,
            "visits_before": m0.visit_counter, "visits_after": m1.visit_counter,
            "note": "plumbing test of the re-simulation path; not an evaluation of any end-time policy"}


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "data" / "synthetic"))
    ap.add_argument("--repro", default="all", help="'all', 'first' (seed 1 per scenario) or 'none'")
    a = ap.parse_args()
    root = Path(a.root)
    FIG.mkdir(parents=True, exist_ok=True)
    ptab = yaml.safe_load((ROOT / "calibration" / "parameters.yaml").read_text(encoding="utf-8"))
    targets = ptab["validation_targets"]
    js = json.loads((RES / "jank_shmueli.json").read_text(encoding="utf-8"))
    out = {"datasets": {}, "targets": targets}
    dirs = sorted(root.glob("scenario_*/seed_*"))
    for d in dirs:
        t = load(d)
        meta = t["meta"]
        cfg = C.load(ROOT / meta["scenario_file"]) if meta.get("scenario_file") else C.load(None)
        rec = {"structure": structural(t, cfg), "moments": moments(t), "dilution": dilution(t),
               "rows": meta["row_counts"]}
        if a.repro == "all" or (a.repro == "first" and d.name == "seed_1"):
            tmp = ROOT / "data" / "_repro_tmp"
            G.run(ROOT / meta["scenario_file"], meta["seed"], tmp,
                  overrides={"scale": meta["scale"]} if "smoke" in str(root) else None)
            h0, h1 = file_hashes(d), file_hashes(tmp)
            rec["reproducible_identical_csv"] = h0 == h1
            for p in sorted(tmp.rglob("*"), reverse=True):
                p.unlink() if p.is_file() else p.rmdir()
            tmp.rmdir()
        out["datasets"][f"{d.parent.name}/{d.name}"] = rec
        print(d, "structure", rec["structure"]["all_pass"], "repro", rec.get("reproducible_identical_csv"), flush=True)

    # aggregate per scenario
    agg = {}
    keys = ["share_zero_bid", "bids_per_auction_mean_pos", "bidders_per_auction_mean_pos", "bids_per_auction_nb_size_mom",
            "bids_per_bidder_in_auction_mean", "share_repeat_bidder_pairs", "share_bids_last_5min",
            "share_bids_last_60min", "share_bids_first_10pct", "share_auctions_last_bid_5min", "gini_bids_per_bidder",
            "slope_log_price_log_bids_sold", "slope_log1p_bids_log1p_views", "winning_over_estimated_median"]
    for k, rec in out["datasets"].items():
        s = k.split("/")[0]
        agg.setdefault(s, {kk: [] for kk in keys + ["dilution_slope", "dilution_spearman"]})
        for kk in keys:
            agg[s][kk].append(rec["moments"][kk])
        agg[s]["dilution_slope"].append(rec["dilution"]["slope_log1p_bidders_on_log1p_concurrent"])
        agg[s]["dilution_spearman"].append(rec["dilution"]["spearman"])
    out["by_scenario"] = {s: {kk: {"mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0}
                              for kk, v in d.items()} for s, d in agg.items()}

    # BARISTA: fit synthetic normalised bid times and compare with the real 3-day fit
    b3 = js["pooled"]["barista_3day_pooled"]["params"]
    real = barista.Barista(b3["a1"], b3["a2"], b3["a3"], b3["d1"] / 3, b3["d2"] / 3, 1.0)
    out["barista"] = {"real_3day_normalised": real.to_dict()}
    for s in agg:
        u = np.concatenate([np.array(out["datasets"][k]["moments"]["u_values_sample"]) for k in out["datasets"]
                            if k.startswith(s)])
        u = np.clip(u, 0, 1 - 1e-9)
        fr = barista.fit(u, 1.0, d2_grid=np.array([0.5, 1, 2, 5, 10]) / (1440 * 2))
        ks = stats.kstest(u, real.cdf)
        out["barista"][s] = {"lrt_choice": fr["lrt_choice"], "params": fr["chosen"].to_dict(),
                             "ks_vs_real_3day": {"D": float(ks.statistic), "p": float(ks.pvalue)}, "n": len(u)}

    # independent checks against the real-data holdout split (not used in tuning)
    p = js["pooled"]
    out["holdout_reference"] = {"js_bidders_per_auction_holdout_mean": p["bidders_per_auction_holdout"]["mean"],
                                "js_bids_per_auction_holdout_mean": p["bids_per_auction_holdout"]["mean"],
                                "js_timing_holdout": p["timing_holdout"]}

    scen_dir = ROOT / "config" / "scenarios"
    if (scen_dir / "scenario_B.yaml").exists() and "smoke" not in str(root):
        out["counterfactual_check"] = counterfactual_check(scen_dir / "scenario_B.yaml", 1)
    figures(out, js)
    (ROOT / "validation" / "results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("wrote validation/results.json")


def figures(out, js):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    real = np.array(js["pooled"]["u_histogram_3day"], float)
    real /= real.sum()
    fig, ax = plt.subplots(2, 3, figsize=(12, 6), sharex=True, sharey=True)
    for i, s in enumerate(sorted(out["by_scenario"])):
        h = np.sum([out["datasets"][k]["moments"]["u_hist20"] for k in out["datasets"] if k.startswith(s)], axis=0)
        h = np.array(h, float) / max(1, np.sum(h))
        x = np.arange(20) / 20 + 0.025
        axx = ax.flat[i]
        axx.bar(x, h, width=0.045, color="#4C78A8", label="synthetic")
        axx.step(np.arange(21) / 20, np.append(real, real[-1]), where="post", color="#E45756", label="eBay 3-day (J&S)")
        axx.set_title(s)
        axx.set_xlabel("elapsed share of auction")
    ax.flat[0].set_ylabel("share of bids")
    ax.flat[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "bid_time_distribution.png", dpi=120)
    plt.close(fig)

    ks = ["bidders_per_auction_mean_pos", "bids_per_bidder_in_auction_mean", "share_bids_last_5min",
          "share_auctions_last_bid_5min", "share_bids_first_10pct", "share_bids_last_60min"]
    tk = ["js3_bidders_per_auction_mean", "js_bids_per_bidder_in_auction_mean", "js3_share_bids_last_5min",
          "js3_share_auctions_last_bid_5min", "js3_share_bids_first_10pct", "js3_share_bids_last_60min"]
    fig, ax = plt.subplots(1, len(ks), figsize=(16, 3.2))
    sc = sorted(out["by_scenario"])
    for i, (k, t) in enumerate(zip(ks, tk)):
        m = [out["by_scenario"][s][k]["mean"] for s in sc]
        e = [out["by_scenario"][s][k]["sd"] for s in sc]
        ax[i].bar(sc, m, yerr=e, color="#4C78A8")
        ax[i].axhline(out["targets"][t], color="#E45756", ls="--")
        ax[i].set_title(k.replace("_", " "), fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "moments_vs_ebay.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3))
    prof = W.profile("korea_evening")
    ax.plot(range(24), prof / prof.sum(), color="#E45756", label="ASSUMED profile (input)")
    for s in ("A", "B"):
        k = f"scenario_{s}/seed_1"
        if k in out["datasets"]:
            hs = out["datasets"][k]["moments"]["visit_hour_share"]
            ax.plot([int(h) for h in hs], list(hs.values()), label=f"visits {s}")
    ax.set_xlabel("hour (KST)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "visit_hours.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
