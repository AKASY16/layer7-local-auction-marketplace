"""Jank & Shmueli eBay bid histories: bid timing, counts, repeat bidding, BARISTA fits.

bidtime in the main files is days since auction start (relative time); only the
Palm "Visualization" file carries absolute timestamps, with no time zone stated.
Auctions appear only through their bids, so zero-bid auctions are unobserved and
count fits are zero-truncated.
"""
import numpy as np
import pandas as pd
from scipy import stats

from common import DATA, describe, fit_counts, gini, is_holdout, save
import barista  # noqa: E402  (src/ is put on the path by common)

JS = DATA / "Jank & Shmueli"
MAIN = {
    ("Cartier", 3): "Cartier wristwatched on eBay/Cartier+3-day+auctions.csv",
    ("Cartier", 5): "Cartier wristwatched on eBay/Cartier+5-day+auctions.csv",
    ("Cartier", 7): "Cartier wristwatched on eBay/Cartier+7-day+auctions.csv",
    ("Palm", 3): "Palm Pilot M515 PDAs on eBay/Palm+3-day+auctions.csv",
    ("Palm", 5): "Palm Pilot M515 PDAs on eBay/Palm+5-day+auctions.csv",
    ("Palm", 7): "Palm Pilot M515 PDAs on eBay/Palm+7-day+auctions.csv",
    ("Xbox", 3): "Xbox game consoles on eBay/Xbox 3-day auctions.csv",
    ("Xbox", 5): "Xbox game consoles on eBay/Xbox 5-day auctions.csv",
    ("Xbox", 7): "Xbox game consoles on eBay/Xbox 7-day auctions.csv",
}
# BARISTA Table 4 of the paper, for comparison only
PAPER_T4 = {
    ("Xbox", 7): (3, 10, 0.24, 1.19, 1.2, 2), ("Xbox", 5): (2, None, 0.3, 7.7, None, 1),
    ("Xbox", 3): (3, 2.1, 0.3, 2.99, 1.3, 1.8), ("Palm", 7): (3, 4.9, 0.37, 1.13, 1.7, 2),
    ("Palm", 5): (3, 2.7, 0.32, 0.79, 1.8, 2), ("Palm", 3): (3, 1.8, 0.33, 1.01, 1.45, 1.4),
    ("Cartier", 7): (3, 2.6, 0.29, 2.95, 4, 0.5), ("Cartier", 5): (3, 3.1, 0.35, 1.08, 2.4, 0.51),
    ("Cartier", 3): (3, 1.5, 0.31, 0.88, 1.8, 1),
}
MIN = 1 / 1440


def load_main():
    frames = []
    for (item, dur), rel in MAIN.items():
        df = pd.read_csv(JS / rel)
        df["item"], df["duration_days"] = item, dur
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["u"] = df["bidtime"] / df["duration_days"]
    df["time_to_end_min"] = (df["duration_days"] - df["bidtime"]) * 1440
    df["holdout"] = df["auctionid"].map(is_holdout)
    return df


def auction_level(df):
    g = df.sort_values("bidtime").groupby("auctionid")
    a = pd.DataFrame({
        "item": g["item"].first(), "duration_days": g["duration_days"].first(),
        "n_bids": g.size(), "n_bidders": g["bidder"].nunique(),
        "openbid": g["openbid"].first(), "price": g["price"].first(),
        "last_bid_min_to_end": g["time_to_end_min"].min(),
        "first_bid_u": g["u"].min(), "holdout": g["holdout"].first(),
    })
    a["price_over_open"] = a["price"] / a["openbid"].clip(lower=0.01)
    return a


def _pair_stats(df):
    bpa = df.groupby(["auctionid", "bidder"]).size()
    return {"bids_per_bidder_in_auction_mean": float(bpa.mean()), "share_repeat_pairs": float((bpa >= 2).mean()),
            "n_pairs": int(len(bpa))}


def timing_shares(df):
    t = df["time_to_end_min"]
    return {"last_1min": (t <= 1).mean(), "last_5min": (t <= 5).mean(), "last_60min": (t <= 60).mean(),
            "last_10pct_time": (df["u"] >= 0.9).mean(), "first_10pct_time": (df["u"] <= 0.1).mean(),
            "n_bids": len(df)}


def main():
    raw_checks = {}
    # duplicate file check
    a = pd.read_csv(JS / MAIN[("Cartier", 7)])
    b = pd.read_csv(JS / "Cartier wristwatched on eBay/Cartier+for+WinnersCurse.csv")
    raw_checks["cartier_winnerscurse_identical_to_7day"] = bool(a.equals(b))
    c = pd.read_csv(JS / "Palm Pilot M515 PDAs on eBay/Palm+7-day+149auctions+Curve+Clustering.csv")
    p7 = pd.read_csv(JS / MAIN[("Palm", 7)])
    raw_checks["palm149_auctions"] = int(c["Auction ID"].nunique())
    raw_checks["palm149_ids_in_palm7"] = int(c["Auction ID"].drop_duplicates().isin(p7["auctionid"]).sum())
    alld = pd.read_csv(JS / "Palm Pilot M515 PDAs on eBay/Palm+All+DurationAuctions.csv")
    raw_checks["palm_alldur_auctions"] = int(alld["AuctId"].nunique())
    raw_checks["palm_alldur_lengths"] = alld.groupby("Length")["AuctId"].nunique().to_dict()

    df = load_main()
    raw_checks["main_rows"] = len(df)
    raw_checks["main_duplicate_rows"] = int(df.duplicated().sum())
    raw_checks["bidtime_outside_0_T"] = int(((df["bidtime"] < 0) | (df["bidtime"] > df["duration_days"])).sum())
    raw_checks["bidder_null"] = int(df["bidder"].isna().sum())
    raw_checks["bid_gt_price"] = float((df["bid"] > df["price"] + 1e-9).mean())
    auc = auction_level(df)

    out = {"source": "Jank & Shmueli, Modeling Online Auctions (eBay 2003-ish; Palm file dated Mar-Apr 2003)",
           "time_unit": "bidtime = days since start (relative). No absolute clock except Palm Visualization file.",
           "checks": raw_checks, "by_dataset": {}, "pooled": {}}

    for (item, dur), sub in df.groupby(["item", "duration_days"]):
        key = f"{item}_{dur}d"
        sa = auc[(auc["item"] == item) & (auc["duration_days"] == dur)]
        bpa = sub.groupby(["auctionid", "bidder"]).size()
        cal = sub[~sub["holdout"]]
        hold = sub[sub["holdout"]]
        fitres = barista.fit(cal["bidtime"].values, float(dur))
        m = fitres["chosen"]
        ks_cal = stats.kstest(cal["bidtime"].values, m.cdf)
        ks_hold = stats.kstest(hold["bidtime"].values, m.cdf) if len(hold) > 20 else None
        pt = PAPER_T4[(item, dur)]
        out["by_dataset"][key] = {
            "n_auctions": len(sa), "n_bids": len(sub), "n_bidders": sub["bidder"].nunique(),
            "bids_per_auction": describe(sa["n_bids"]),
            "bidders_per_auction": describe(sa["n_bidders"]),
            "bids_per_bidder_in_auction": describe(bpa.values),
            "share_bidder_auction_pairs_with_repeat_bid": float((bpa >= 2).mean()),
            "timing": timing_shares(sub),
            "share_auctions_last_bid_within_5min": float((sa["last_bid_min_to_end"] <= 5).mean()),
            "price_over_openbid": describe(sa["price_over_open"]),
            "barista_fit_calibration_split": {
                "lrt_choice": fitres["lrt_choice"],
                "models": fitres["models"],
                "n_cal_bids": len(cal), "n_holdout_bids": len(hold),
                "ks_calibration": {"D": ks_cal.statistic, "p": ks_cal.pvalue},
                "ks_holdout": None if ks_hold is None else {"D": ks_hold.statistic, "p": ks_hold.pvalue},
                "d2_minutes": m.d2 * 1440,
            },
            "paper_table4": {"stages": pt[0], "a1": pt[1], "a2": pt[2], "a3": pt[3], "d1_days": pt[4],
                             "d2_min": pt[5]},
        }
        print(key, fitres["lrt_choice"], m, "KS hold", ks_hold)

    # pooled over all nine datasets (different items and durations: descriptive only)
    cal_a = auc[~auc["holdout"]]
    hold_a = auc[auc["holdout"]]
    bpa_all = df.groupby(["auctionid", "bidder"]).size()
    # bidder participation across auctions within each item market
    part = df.groupby(["item", "bidder"])["auctionid"].nunique()
    gaps = (df.sort_values(["auctionid", "bidtime"]).groupby("auctionid")["bidtime"].diff().dropna() * 1440)
    rep = df.sort_values(["auctionid", "bidder", "bidtime"]).groupby(["auctionid", "bidder"])["bidtime"].diff().dropna() * 1440
    out["pooled"] = {
        "n_auctions": len(auc), "n_bids": len(df),
        "bids_per_auction_fit_calibration": fit_counts(cal_a["n_bids"].values, zero_truncated=True),
        "bids_per_auction_calibration": describe(cal_a["n_bids"]),
        "bids_per_auction_holdout": describe(hold_a["n_bids"]),
        "bidders_per_auction_fit_calibration": fit_counts(cal_a["n_bidders"].values, zero_truncated=True),
        "bidders_per_auction_calibration": describe(cal_a["n_bidders"]),
        "bidders_per_auction_holdout": describe(hold_a["n_bidders"]),
        "bids_per_bidder_in_auction": describe(bpa_all.values),
        "bids_per_bidder_in_auction_fit": fit_counts(bpa_all.values, zero_truncated=True),
        "share_bidder_auction_pairs_with_repeat_bid": float((bpa_all >= 2).mean()),
        "auctions_per_bidder_within_item": describe(part.values),
        "share_bidders_in_2plus_auctions_within_item": float((part >= 2).mean()),
        "interbid_gap_min": describe(gaps.values),
        "repeat_bid_gap_same_bidder_min": describe(rep.values),
        "share_repeat_gaps_under_10min": float((rep <= 10).mean()),
        "timing_calibration": timing_shares(df[~df["holdout"]]),
        "timing_holdout": timing_shares(df[df["holdout"]]),
        "share_auctions_last_bid_within_5min": float((auc["last_bid_min_to_end"] <= 5).mean()),
        "price_over_openbid": describe(auc["price_over_open"]),
        # opening bid relative to closing price, calibration split: used as the empirical
        # start-price rule (start / value) in the generator
        "openbid_over_price_quantiles_calibration": np.quantile(
            (cal_a["openbid"] / cal_a["price"]).clip(1e-4, 1.0), np.linspace(0, 1, 21)).tolist(),
        "openbid_over_price_quantiles_holdout": np.quantile(
            (hold_a["openbid"] / hold_a["price"]).clip(1e-4, 1.0), np.linspace(0, 1, 21)).tolist(),
        "holdout_pairs": _pair_stats(df[df["holdout"]]),
        "calibration_pairs": _pair_stats(df[~df["holdout"]]),
        "bids_per_auction_fit_holdout": fit_counts(hold_a["n_bids"].values, zero_truncated=True),
        "corr_log_price_vs_bidders_within_item": {
            it: float(np.corrcoef(np.log(s["price"]), s["n_bidders"])[0, 1]) for it, s in auc.groupby("item")},
        "bidderrate": describe(df.drop_duplicates("bidder")["bidderrate"]),
        "gini_bids_per_bidder": gini(df.groupby("bidder").size().values),
    }
    # bid-time density on normalised time for the 3-day auctions (closest to 24-72h)
    d3 = df[df["duration_days"] == 3]
    out["pooled"]["u_histogram_3day"] = np.histogram(d3["u"], bins=20, range=(0, 1))[0].tolist()
    f3 = barista.fit(d3.loc[~d3["holdout"], "bidtime"].values, 3.0)
    ks3 = stats.kstest(d3.loc[d3["holdout"], "bidtime"].values, f3["chosen"].cdf)
    out["pooled"]["barista_3day_pooled"] = {"lrt_choice": f3["lrt_choice"], "params": f3["chosen"].to_dict(),
                                            "ks_holdout": {"D": ks3.statistic, "p": ks3.pvalue},
                                            "models": f3["models"]}

    # Palm file with absolute timestamps (time zone not stated in the file)
    viz = pd.read_csv(JS / "Palm Pilot M515 PDAs on eBay/Palm 7-day 158auctions Visualization.csv")
    viz = viz.iloc[:, :6]
    viz.columns = ["auction", "amount", "bid_ts", "start_ts", "bidder", "rating"]
    viz = viz[viz["bidder"] != "*"]
    viz["bid_ts"] = pd.to_datetime(viz["bid_ts"], format="%b-%d-%y %H:%M:%S", errors="coerce")
    viz["start_ts"] = pd.to_datetime(viz["start_ts"], format="%b-%d-%y %H:%M:%S", errors="coerce")
    end = viz.groupby("auction")["start_ts"].first() + pd.Timedelta(days=7)
    out["palm_absolute_time_file"] = {
        "rows_excluding_start_marker": len(viz), "auctions": viz["auction"].nunique(),
        "unparsed_bid_ts": int(viz["bid_ts"].isna().sum()),
        "bid_ts_range": [str(viz["bid_ts"].min()), str(viz["bid_ts"].max())],
        "time_zone": "not stated in file (eBay displayed Pacific time at the time; unverified)",
        "bid_hour_share": (viz["bid_ts"].dt.hour.value_counts(normalize=True).sort_index()).to_dict(),
        "end_hour_share": (end.dt.hour.value_counts(normalize=True).sort_index()).to_dict(),
    }
    # seller-bidder network file
    net = pd.read_csv(JS / "Swarowski beads on eBay/eBayNetwork.csv")
    out["swarovski_network"] = {"edges": len(net), "sellers": net["Seller"].nunique(),
                                "bidders": net["Bidder"].nunique(), "weight": describe(net["Weight"]),
                                "note": "seller-bidder edge counts only; no times or prices"}
    save("jank_shmueli", out)


if __name__ == "__main__":
    main()
