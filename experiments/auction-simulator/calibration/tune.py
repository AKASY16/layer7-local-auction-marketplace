"""Coarse simulated-moment grid search for four ASSUMED behaviour parameters.

Targets are Jank & Shmueli eBay moments (3-day auctions where the paper splits by
duration). Tuning uses seed 101, which is not one of the output seeds, and the
baseline config (seller ends follow demand). The result is written to
calibration/tuned.yaml; run build_parameters.py afterwards. Matching eBay 2003
moments does not make these LAYER7 facts; they stay ASSUMED.
"""
import itertools
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
import config as C  # noqa: E402
import market_simulator as MS  # noqa: E402
import sim_stats  # noqa: E402
import world as W  # noqa: E402

TARGETS = {  # moment -> (target key in parameters.yaml, weight); all from calibration splits
    "bidders_per_auction_mean_pos": ("js3_bidders_per_auction_mean", 1.0),
    "bids_per_bidder_in_auction_mean": ("js_cal_bids_per_bidder_in_auction_mean", 1.0),
    "share_repeat_bidder_pairs": ("js_cal_share_repeat_bidder_pairs", 1.0),
    "share_bids_last_5min": ("js3_share_bids_last_5min", 1.0),
    "share_auctions_last_bid_5min": ("js3_share_auctions_last_bid_5min", 1.0),
    "share_bids_first_10pct": ("js3_share_bids_first_10pct", 0.5),
    "share_bids_last_60min": ("js3_share_bids_last_60min", 0.5),
    "bids_per_auction_nb_size_mom": ("js_bids_per_auction_nb_size", 0.5),
    "slope_log_price_log_bids_sold": ("goodwill_slope_log_price_log_bids", 1.0),
}
# browsing / alert settings fixed by hand trials before the first pass
FIXED = {"ending_soon_boost": 10.0, "ending_soon_tau_hours": 4.0, "alert_open_prob": 0.15}
# kept at the values chosen in pass 3 (see tuning_log_pass3.txt)
FROM_PASS3 = {"early_act_prob": 0.1, "watch_return_mean_min_before_end": 360.0, "rebid_propensity_mean": 0.97}
GRID = {  # pass 4: after the empirical start-price rule, session re-bids and appeal -> WTP were added
    "visit_rate_scale": [0.25, 0.35],
    "item_appeal_logsd": [1.0, 1.4],
    "appeal_wtp_elasticity": [1.0, 1.5],
    "incremental_share_of_non_snipers": [0.47, 0.62],
    "style_share_sniper": [0.2, 0.3],
    "watch_return_prob": [0.6, 0.8],
}
SEED = 101


def main():
    tab = yaml.safe_load((HERE / "parameters.yaml").read_text(encoding="utf-8"))
    tg = tab["validation_targets"]
    rows = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        ov = {**FIXED, **FROM_PASS3, **dict(zip(keys, combo))}
        sn, fi = ov["style_share_sniper"], ov.pop("incremental_share_of_non_snipers")
        ov["style_share_early"] = (1 - sn) * (1 - fi)
        ov["style_share_incremental"] = (1 - sn) * fi
        cfg = C.load(None, overrides={"param_overrides": ov, "scenario": {"id": "tune", "name": "tune"}})
        w = W.build(cfg, SEED)
        m = MS.simulate(w, {a["auction_id"]: a["default_end_at"] for a in w.auctions}, SEED)
        mm = sim_stats.market_moments(m)
        loss = sum(wt * ((mm[k] - tg[t]) / tg[t]) ** 2 for k, (t, wt) in TARGETS.items())
        rows.append({"params": ov, "loss": loss, **{k: mm[k] for k in TARGETS}})
        print(round(loss, 4), {k: round(v, 3) for k, v in ov.items()}, {k: round(mm[k], 3) for k in TARGETS}, flush=True)
    rows.sort(key=lambda r: r["loss"])
    best = rows[0]
    (HERE / "statistical_analysis" / "results" / "tuning_grid.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    out = {"objective": "weighted squared relative error over " + ", ".join(TARGETS), "seed": SEED,
           "loss": best["loss"], "moments_at_best": {k: best[k] for k in TARGETS},
           "targets": {k: tg[t] for k, (t, _) in TARGETS.items()},
           "values": {k: round(float(v), 4) for k, v in best["params"].items()},
           "fixed_by_hand": sorted(FIXED), "fixed_from_previous_pass": sorted(FROM_PASS3), "grid": GRID}
    (HERE / "tuned.yaml").write_text(yaml.safe_dump(out, sort_keys=False), encoding="utf-8")
    print("best", json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
