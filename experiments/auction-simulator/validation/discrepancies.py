"""Table of remaining statistical discrepancies of the frozen baseline (baseline-v4).

Reads validation/results.json and the real-data results; writes
validation/known_discrepancies.csv. Rows: one per metric, synthetic range over
scenarios A-E (F reported separately because of its size), real value, gap.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    r = json.loads((ROOT / "validation" / "results.json").read_text(encoding="utf-8"))
    t = yaml.safe_load((ROOT / "calibration" / "parameters.yaml").read_text(encoding="utf-8"))
    tg, P = t["validation_targets"], t["params"]
    bs = r["by_scenario"]
    main_s = [f"scenario_{s}" for s in "ABCDE"]

    def rng(k):
        v = [bs[s][k]["mean"] for s in main_s]
        return min(v), max(v), bs["scenario_F"][k]["mean"]

    rows = []

    def add(metric, real, real_src, k, tuned, holdout=None):
        lo, hi, f = rng(k)
        gap = (lo - real) / real if lo > real else ((hi - real) / real if hi < real else 0.0)
        rows.append({"metric": metric, "real": real, "real_source": real_src, "real_holdout": holdout,
                     "synthetic_A_to_E_min": lo, "synthetic_A_to_E_max": hi, "synthetic_F": f,
                     "rel_gap_outside_range": gap, "tuning_target": tuned})

    add("repeat bidder-auction pairs (>=2 bids)", tg["js_cal_share_repeat_bidder_pairs"], "J&S calibration split",
        "share_repeat_bidder_pairs", True, tg["js_hold_share_repeat_bidder_pairs"])
    add("auctions with last bid in final 5 min", tg["js3_share_auctions_last_bid_5min"], "J&S 3-day",
        "share_auctions_last_bid_5min", True)
    add("slope log1p(bids) ~ log1p(views)", tg["maxsold_slope_log1p_bids_log1p_views"], "MaxSold lots",
        "slope_log1p_bids_log1p_views", False)
    add("share of auctions with zero bids", tg["maxsold_share_zero_bid_items"], "MaxSold lots (different start rule)",
        "share_zero_bid", False)
    add("share of bids in final 60 min", tg["js3_share_bids_last_60min"], "J&S 3-day", "share_bids_last_60min", True)
    add("share of bids in first 10% of time", tg["js3_share_bids_first_10pct"], "J&S 3-day",
        "share_bids_first_10pct", True)
    # sold-price dispersion by category (mean over seeds, scenarios A-E)
    for cat, pk, src in (("figure", "price_logsd_figure", "Goodwill LEGO single items"),
                         ("limited_goods", "price_logsd_limited_goods", "Goodwill single items, median of files"),
                         ("retro_game", "price_logsd_retro_game", "eBay sold retro games"),
                         ("tcg", "price_logsd_tcg", "ASSUMED (no TCG data)")):
        vals = {s: np.mean([d["moments"]["log_price_sd_by_category"][cat] for k, d in r["datasets"].items()
                            if k.startswith(s)]) for s in main_s + ["scenario_F"]}
        lo, hi = min(vals[s] for s in main_s), max(vals[s] for s in main_s)
        real = P[pk]["value"]
        rows.append({"metric": f"sd of log sold price, {cat}", "real": real, "real_source": src, "real_holdout": None,
                     "synthetic_A_to_E_min": lo, "synthetic_A_to_E_max": hi, "synthetic_F": vals["scenario_F"],
                     "rel_gap_outside_range": (lo - real) / real if lo > real else ((hi - real) / real if hi < real else 0.0),
                     "tuning_target": False})
    sold = [np.mean([1 - d["moments"]["share_zero_bid"] for k, d in r["datasets"].items() if k.startswith(s)])
            for s in main_s]
    rows.append({"metric": "sell-through rate", "real": None, "real_source": "no source observes unsold auctions",
                 "real_holdout": None, "synthetic_A_to_E_min": min(sold), "synthetic_A_to_E_max": max(sold),
                 "synthetic_F": None, "rel_gap_outside_range": None, "tuning_target": False})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "validation" / "known_discrepancies.csv", index=False, encoding="utf-8-sig")
    print(df.round(3).to_string())


if __name__ == "__main__":
    main()
