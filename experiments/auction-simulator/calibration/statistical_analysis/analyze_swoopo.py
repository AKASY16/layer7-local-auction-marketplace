"""Swoopo pay-per-bid auctions (Byers, Mitzenmacher & Zervas): bidder heterogeneity.

Every bid costs a fee and pushes the clock back, so levels (bids per auction,
prices) do not transfer to a hard-close auction. Used only for the shape of
bidder heterogeneity and re-bid timing.
"""
import sys

import numpy as np
import pandas as pd

from common import describe, fit_counts, gini, save

EXTRACT = sys.argv[1] if len(sys.argv) > 1 else None  # folder holding swoopo-dataset/


def main():
    if EXTRACT is None:
        raise SystemExit("usage: analyze_swoopo.py <dir containing swoopo-dataset/>")
    tr = pd.read_csv(f"{EXTRACT}/swoopo-dataset/traces.tsv", sep="\t")
    oc = pd.read_csv(f"{EXTRACT}/swoopo-dataset/outcomes.tsv", sep="\t")
    tr["bid_time"] = pd.to_datetime(tr["bid_time"], errors="coerce")
    out = {"source": "Swoopo traces 2009-2010 and outcomes 2008-2009 (README: Byers, Mitzenmacher, Zervas)",
           "closing_rule": "pay-per-bid; each bid adds seconds to a countdown (soft close by design)"}
    chk = {"traces_rows": len(tr), "traces_auctions": tr["auction_id"].nunique(),
           "outcomes_rows": len(oc), "outcomes_unique_auctions": oc["auction_id"].nunique(),
           "traces_auctions_in_outcomes": int(tr["auction_id"].drop_duplicates().isin(oc["auction_id"]).sum()),
           "unparsed_bid_time": int(tr["bid_time"].isna().sum()),
           "duplicate_rows": int(tr.duplicated().sum()),
           "bid_time_range": [str(tr["bid_time"].min()), str(tr["bid_time"].max())],
           "bid_butler_values": tr["bid_butler"].value_counts().to_dict(),
           "share_inferred_within_group": float(tr["bid_infered"].mean())}
    out["checks"] = chk

    per_auc = tr.groupby("auction_id").agg(n_bids=("bid_number", "size"), n_users=("bid_user", "nunique"))
    ua = tr.groupby(["auction_id", "bid_user"]).size()
    users = tr.groupby("bid_user").agg(n_bids=("bid_number", "size"), n_auctions=("auction_id", "nunique"))
    # re-bid gap of the same user in the same auction, seconds (grouped bids share a timestamp)
    t = tr.sort_values(["auction_id", "bid_user", "bid_number"])
    gap = t.groupby(["auction_id", "bid_user"])["bid_time"].diff().dt.total_seconds().dropna()
    gap = gap[gap > 0]
    tiers = pd.cut(ua, [0, 1, 5, 20, 100, np.inf], labels=["1", "2-5", "6-20", "21-100", ">100"])
    top1 = users["n_bids"].sort_values(ascending=False)
    out["traces"] = {
        "bids_per_auction": describe(per_auc["n_bids"]),
        "users_per_auction": describe(per_auc["n_users"]),
        "bids_per_user_in_auction": describe(ua.values),
        "bids_per_user_in_auction_fit": fit_counts(ua.values, zero_truncated=True),
        "share_user_auction_pairs_single_bid": float((ua == 1).mean()),
        "user_auction_pair_tiers_share": tiers.value_counts(normalize=True).sort_index().to_dict(),
        "bid_share_by_tier": ua.groupby(tiers, observed=False).sum().div(ua.sum()).to_dict(),
        "auctions_per_user": describe(users["n_auctions"]),
        "share_users_single_auction": float((users["n_auctions"] == 1).mean()),
        "gini_bids_per_user": gini(users["n_bids"].values),
        "share_bids_top1pct_users": float(top1.head(max(1, len(top1) // 100)).sum() / top1.sum()),
        "share_bids_top10pct_users": float(top1.head(max(1, len(top1) // 10)).sum() / top1.sum()),
        "bidbutler_share_of_bids": float((tr["bid_butler"] > 0).mean()),
        "rebid_gap_same_user_sec": describe(gap.values),
        "share_rebid_within_60s": float((gap <= 60).mean()),
        "bid_hour_share_tz_unknown": tr["bid_time"].dt.hour.value_counts(normalize=True).sort_index().to_dict(),
    }
    # outcomes: price relative to retail, winner effort
    oc["price_over_retail"] = oc["price"] / oc["retail"].replace(0, np.nan)
    hh = oc["endtime_str"].str.extract(r"^(\d{1,2}):\d{2} (\w{3})")
    out["outcomes"] = {
        "price_over_retail": describe(oc["price_over_retail"]),
        "winner_placed_bids": describe(oc["placedbids"]),
        "bidfee_cents_values": oc["bidfee"].value_counts().to_dict(),
        "end_tz_labels": hh[1].value_counts().to_dict(),
        "end_hour_share_pacific": hh[0].astype(float).value_counts(normalize=True).sort_index().to_dict(),
        "flags_share": oc[["flg_click_only", "flg_beginnerauction", "flg_fixedprice", "flg_endprice"]].mean().to_dict(),
    }
    save("swoopo", out)


if __name__ == "__main__":
    main()
