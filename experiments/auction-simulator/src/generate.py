"""Generate synthetic LAYER7 auction datasets.

  python src/generate.py --all                      # 6 scenarios x seeds in baseline.yaml
  python src/generate.py --scenario config/scenarios/scenario_B.yaml --seed 1
  python src/generate.py --scenario ... --seed 1 --end-times my_policy.csv --out data/experiments/x
  python src/generate.py --all --smoke              # tiny run for structural checks

--end-times takes a CSV (auction_id, scheduled_end_at ISO-8601) and re-simulates
the same world (same buyers, items, valuations, visit stream) under those ends.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import market_simulator as MS  # noqa: E402
import world as W  # noqa: E402

GENERATOR_VERSION = "1.0.0"
ROOT = C.ROOT


def iso(origin, t):
    return (origin + timedelta(minutes=float(t))).isoformat(timespec="seconds")


def parse_end_times(path, world):
    df = pd.read_csv(path)
    out = {}
    for r in df.itertuples():
        t = datetime.fromisoformat(r.scheduled_end_at)
        if t.tzinfo is None:
            raise ValueError("scheduled_end_at needs a UTC offset, e.g. 2026-11-03T21:00:00+09:00")
        out[int(r.auction_id)] = (t - world.origin).total_seconds() / 60.0
    return out


def check_end_times(world, ends):
    bad = []
    for a in world.auctions:
        e = ends[a["auction_id"]]
        if not (a["start_at"] + 24 * 60 - 1e-6 <= e <= a["start_at"] + 72 * 60 + 1e-6):
            bad.append(a["auction_id"])
    if bad:
        raise ValueError(f"{len(bad)} end times outside 24-72 h of start, e.g. auction {bad[:5]}")


def run(scenario, seed, out_dir, end_times_csv=None, overrides=None, write=True):
    cfg = C.load(scenario, overrides=overrides)
    world = W.build(cfg, seed)
    ends = {a["auction_id"]: a["default_end_at"] for a in world.auctions}
    source = "seller_default"
    if end_times_csv:
        ends.update(parse_end_times(end_times_csv, world))
        source = f"override:{Path(end_times_csv).name}"
    check_end_times(world, ends)
    m = MS.simulate(world, ends, seed, cfg.get("close_rule", "hard"))
    tables = to_tables(world, m, cfg, source)
    if write:
        write_tables(tables, out_dir, cfg, seed, scenario, source)
    return world, m, tables


def to_tables(world, m, cfg, source):
    o = world.origin
    sellers = pd.DataFrame([{k: s[k] for k in ("seller_id", "primary_category", "n_listings",
                                                "listing_rate_per_day", "preferred_end_hour")} for s in world.sellers])
    items = pd.DataFrame(world.items)
    # pairwise similarity for items in the same category (rule in metadata)
    pairs = []
    by_cat = items.groupby("category")
    for _, g in by_cat:
        ids = g["item_id"].to_numpy()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                s = m.similarity(int(ids[i]), int(ids[j]))
                if s > 0:
                    pairs.append((int(ids[i]), int(ids[j]), s))
    sim = pd.DataFrame(pairs, columns=["item_id_a", "item_id_b", "similarity"])

    buyers = pd.DataFrame([{"buyer_id": b["buyer_id"], "main_category": b["main_category"],
                            "followed_categories": "|".join(b["alert_follows"]),
                            "joined_at": iso(o, b["join_at"])} for b in world.buyers])
    latent = pd.DataFrame([{
        "buyer_id": b["buyer_id"], "interest_weights": json.dumps(b["interest"]),
        "favorite_series": "|".join(b["favorite_series"]), "visit_rate_per_day": b["visit_rate_per_day"],
        "hour_offset_h": b["hour_offset"], "bidding_style": b["style"], "rebid_propensity": b["rebid_propensity"],
        "price_level": b["price_level"], "budget_krw": b["budget"], "active_from": iso(o, b["join_at"]),
        "active_until": iso(o, b["leave_at"]), "spent_krw": m.state[b["buyer_id"]]["spent"],
        "n_won": len(m.state[b["buyer_id"]]["won"])} for b in world.buyers])

    rows, outs = [], []
    last_bid = {}
    for bd in m.bids:
        last_bid[bd["auction_id"]] = bd["bid_time"]
    for a in m.auc.values():
        sold = a["leader"] is not None
        rows.append({"auction_id": a["auction_id"], "seller_id": a["seller_id"], "item_id": a["item_id"],
                     "category": a["category"], "start_at": iso(o, a["start_at"]),
                     "scheduled_end_at": iso(o, a["scheduled_end_at"]), "seller_default_end_at": iso(o, a["default_end_at"]),
                     "end_time_source": source if a["scheduled_end_at"] != a["default_end_at"] else "seller_default",
                     "actual_end_at": iso(o, a["actual_end_at"]), "duration_hours": (a["scheduled_end_at"] - a["start_at"]) / 60,
                     "starting_price": a["starting_price"], "minimum_increment_rule": cfg["increment_rule_name"],
                     "minimum_increment_at_start": MS.increment(a["starting_price"], m.inc_table),
                     "close_rule": cfg.get("close_rule", "hard"),
                     "auction_status": "closed_sold" if sold else "closed_unsold"})
        outs.append({"auction_id": a["auction_id"], "winner_id": a["leader"], "winning_price": a["price"] if sold else None,
                     "bid_count": a["n_bids"], "unique_bidder_count": len(a["bidders"]), "sold": sold,
                     "last_bid_at": iso(o, last_bid[a["auction_id"]]) if a["auction_id"] in last_bid else None})
    auctions = pd.DataFrame(rows).sort_values("auction_id")
    outcomes = pd.DataFrame(outs).sort_values("auction_id")
    outcomes["winner_id"] = outcomes["winner_id"].astype("Int64")

    bids = pd.DataFrame(m.bids)
    if len(bids):
        bids = bids.sort_values("bid_time", kind="stable").reset_index(drop=True)  # keep event order for ties
        bids.insert(0, "bid_id", np.arange(1, len(bids) + 1))
        bids["bid_time_min"] = bids["bid_time"]
        bids["bid_time"] = [iso(o, t) for t in bids["bid_time"]]
        bids["leader_after_is_bidder"] = bids["leader_after"] == bids["buyer_id"]
        bids = bids.drop(columns=["leader_after"])
    ev = pd.DataFrame(m.events)
    ev = ev.sort_values("event_time", kind="stable").reset_index(drop=True)
    ev.insert(0, "event_id", np.arange(1, len(ev) + 1))
    ev["event_time"] = [iso(o, t) for t in ev["event_time"]]
    ev["auction_id"] = ev["auction_id"].astype("Int64")
    dec = pd.DataFrame(m.decisions)
    if len(dec):
        dec["time"] = [iso(o, t) for t in dec["time"]]
    val = pd.DataFrame([{"buyer_id": k[0], "auction_id": k[1], "wtp_krw": v} for k, v in m.wtp_log.items()])
    return {"sellers": sellers, "items": items, "item_similarity": sim, "buyers": buyers, "auctions": auctions,
            "visits": ev, "bids": bids, "outcomes": outcomes,
            "hidden/buyers_latent": latent, "hidden/valuations": val, "hidden/decisions": dec}


def write_tables(tables, out_dir, cfg, seed, scenario, source):
    out = Path(out_dir)
    (out / "hidden").mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, df in tables.items():
        p = out / f"{name}.csv"
        df.to_csv(p, index=False, encoding="utf-8")
        hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator_version": GENERATOR_VERSION, "parameters_version": cfg["parameters_version"],
        "scenario": cfg["scenario"]["id"], "scenario_name": cfg["scenario"]["name"], "seed": seed,
        "scenario_file": Path(scenario).resolve().relative_to(ROOT).as_posix() if scenario else None,
        "end_time_source": source, "close_rule": cfg.get("close_rule", "hard"),
        "time_zone": "Asia/Seoul (+09:00)", "origin": cfg["start_date"], "scale": cfg["scale"],
        "similarity_rule": cfg["similarity"], "increment_table_krw": cfg["increment_table_krw"],
        "param_overrides": cfg.get("param_overrides", {}),
        "row_counts": {k: int(len(v)) for k, v in tables.items()}, "file_sha256_16": hashes,
        "observed_files": ["sellers", "items", "item_similarity", "buyers", "auctions", "visits", "bids", "outcomes"],
        "hidden_files": ["hidden/buyers_latent", "hidden/valuations", "hidden/decisions"],
        "note": "hidden/ holds generator truths (budgets, WTP, styles, skip reasons). Do not feed them, or any "
                "row stamped after the decision time, to a recommender.",
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="small scale run into data/smoke")
    ap.add_argument("--end-times")
    ap.add_argument("--out")
    a = ap.parse_args()
    base = C.load_yaml(ROOT / "config" / "baseline.yaml")
    if a.all:
        jobs = [(ROOT / "config" / "scenarios" / f"scenario_{s}.yaml", sd) for s in base["scenarios"] for sd in base["seeds"]]
    else:
        jobs = [(Path(a.scenario), a.seed)]
    for scen, sd in jobs:
        cfg = C.load(scen)
        sid = cfg["scenario"]["id"]
        ov = None
        if a.smoke:
            ov = {"scale": base["smoke_scale"]}
            if sid == "F":
                ov = None
        out = a.out or ROOT / "data" / ("smoke" if a.smoke else "synthetic") / f"scenario_{sid}" / f"seed_{sd}"
        _, m, t = run(scen, sd, out, a.end_times, overrides=ov)
        o = t["outcomes"]
        print(f"{sid} seed {sd}: auctions {len(o)} bids {len(t['bids'])} visits "
              f"{(t['visits']['event_type'] == 'visit').sum()} sold {o['sold'].mean():.2f} "
              f"bids/auction {o['bid_count'].mean():.1f} bidders/auction {o['unique_bidder_count'].mean():.1f} -> {out}")


if __name__ == "__main__":
    main()
