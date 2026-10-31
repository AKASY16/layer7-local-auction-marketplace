"""Summary statistics of a simulated market, defined like the real-data ones.

Real eBay bid histories only contain auctions with bids, so auction-level
moments are computed on auctions with >= 1 bid when compared with them.
"""
import math

import numpy as np
import pandas as pd


def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def market_moments(m):
    """m: market_simulator.Market after run()."""
    bids = pd.DataFrame(m.bids)
    auc = pd.DataFrame([{"auction_id": a["auction_id"], "start": a["start_at"], "end": a["scheduled_end_at"],
                         "n_bids": a["n_bids"], "n_bidders": len(a["bidders"]), "category": a["category"]}
                        for a in m.auc.values()])
    out = {"n_auctions": len(auc), "share_zero_bid": float((auc["n_bids"] == 0).mean()), "n_bids": len(bids)}
    if bids.empty:
        return out
    b = bids.merge(auc[["auction_id", "start", "end"]], on="auction_id")
    b["tte"] = b["end"] - b["bid_time"]
    b["u"] = (b["bid_time"] - b["start"]) / (b["end"] - b["start"])
    pos = auc[auc["n_bids"] > 0]
    pair = b.groupby(["auction_id", "buyer_id"]).size()
    last = b.groupby("auction_id")["tte"].min()
    out.update({
        "bids_per_auction_mean_pos": float(pos["n_bids"].mean()),
        "bids_per_auction_var_pos": float(pos["n_bids"].var()),
        "bidders_per_auction_mean_pos": float(pos["n_bidders"].mean()),
        "bids_per_bidder_in_auction_mean": float(pair.mean()),
        "share_repeat_bidder_pairs": float((pair >= 2).mean()),
        "share_bids_last_5min": float((b["tte"] <= 5).mean()),
        "share_bids_last_60min": float((b["tte"] <= 60).mean()),
        "share_bids_first_10pct": float((b["u"] <= 0.1).mean()),
        "share_auctions_last_bid_5min": float((last <= 5).mean()),
        "gini_bids_per_bidder": gini(b.groupby("buyer_id").size().values),
        "bid_type_share": b["bid_type"].value_counts(normalize=True).to_dict(),
    })
    val = {it["item_id"]: it["estimated_value"] for it in m.w.items}
    sold = pd.DataFrame([{"lp": math.log(a["price"]), "lb": math.log(a["n_bids"]), "category": a["category"]}
                         for a in m.auc.values() if a["leader"] is not None])
    X = np.column_stack([np.ones(len(sold)), sold["lb"], pd.get_dummies(sold["category"], drop_first=True).values.astype(float)])
    out["slope_log_price_log_bids_sold"] = float(np.linalg.lstsq(X, sold["lp"].values, rcond=None)[0][1])
    for c, g in sold.groupby("category"):
        out[f"log_price_sd_sold_{c}"] = float(g["lp"].std())
    out["winning_over_estimated_median"] = float(np.median([a["price"] / val[a["item_id"]] for a in m.auc.values()
                                                            if a["leader"] is not None]))
    mu, var = out["bids_per_auction_mean_pos"], out["bids_per_auction_var_pos"]
    out["bids_per_auction_nb_size_mom"] = float(mu ** 2 / (var - mu)) if var > mu else float("inf")
    return out
