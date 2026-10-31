"""ShopGoodwill closed auctions and eBay sold comps from the ebay-sold-comps repo.

Both sources contain only sold rows. Unsold auctions are not observed, so no
sell-through rate and no unconditional bid-count distribution is estimated.
Goodwill rows: price, bid count, end time (no time zone), seller id, no start time.
eBay rows: price, end date, condition; no bids and no auction/fixed-price flag.
"""
import re

import numpy as np
import pandas as pd

from common import DATA, describe, fit_counts, fit_positive, gini, is_holdout, save

G = DATA / "ShopGoodwill_ebay-sold-comps-main" / "data"


def icc_oneway(y, g):
    """Share of variance between groups (one-way random effects, ANOVA estimator)."""
    df = pd.DataFrame({"y": y, "g": g})
    grp = df.groupby("g")["y"]
    k = grp.size()
    k = k[k >= 2]
    df = df[df["g"].isin(k.index)]
    if len(k) < 3:
        return None
    grp = df.groupby("g")["y"]
    n = len(df)
    a = len(k)
    msb = (grp.size() * (grp.mean() - df["y"].mean()) ** 2).sum() / (a - 1)
    msw = ((df["y"] - grp.transform("mean")) ** 2).sum() / (n - a)
    k0 = (n - (k ** 2).sum() / n) / (a - 1)
    s2b = max((msb - msw) / k0, 0.0)
    return {"icc": s2b / (s2b + msw), "sd_between_log": s2b ** 0.5, "sd_within_log": msw ** 0.5,
            "groups": a, "n": n}


def _slope(d):
    X = np.column_stack([np.ones(len(d)), np.log(d["bids"]), pd.get_dummies(d["file"], drop_first=True).values])
    beta, *_ = np.linalg.lstsq(X.astype(float), np.log(d["sold_price_usd"]).values, rcond=None)
    return {"slope_log_bids": float(beta[1]), "n": len(d)}


def load_goodwill():
    frames = []
    for p in sorted(G.glob("goodwill-*.csv")):
        df = pd.read_csv(p)
        df["file"] = p.stem
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["ended_at"] = pd.to_datetime(df["ended_at"], errors="coerce")
    df["is_lot"] = df["title"].str.contains(r"\blot\b|\bbundle\b|grab ?bag|assort", flags=re.I, regex=True)
    return df


def main():
    gw = load_goodwill()
    chk = {"rows": len(gw), "files": gw["file"].nunique(), "null": gw.isna().sum().to_dict(),
           "item_id_dup_rows": int(gw["item_id"].dropna().duplicated().sum()),
           "full_dup_rows": int(gw.duplicated(subset=["title", "sold_price_usd", "bids", "ended_at", "seller_id"]).sum()),
           "min_bids": int(gw["bids"].min()), "ended_range": [str(gw["ended_at"].min()), str(gw["ended_at"].max())]}
    gw = gw.drop_duplicates(subset=["title", "sold_price_usd", "bids", "ended_at", "seller_id"]).copy()
    chk["rows_after_dedup"] = len(gw)
    gw["holdout"] = gw["seller_id"].map(is_holdout)
    out = {"source": "ebay-sold-comps repo (silentdirectivellc-hub), Goodwill files from the public "
                     "ShopGoodwill buyer API per README; licence CC0 (uploader); ShopGoodwill ToS not checked",
           "observation": "sold-only, conditional statistics", "checks": chk, "goodwill_by_file": {}}

    for f, s in gw.groupby("file"):
        out["goodwill_by_file"][f] = {
            "n": len(s), "sellers": s["seller_id"].nunique(), "lot_share": s["is_lot"].mean(),
            "price": describe(s["sold_price_usd"]), "bids": describe(s["bids"]),
            "spearman_price_bids": float(s[["sold_price_usd", "bids"]].corr("spearman").iloc[0, 1]),
            "price_fit": fit_positive(s["sold_price_usd"].values),
        }

    cal = gw[~gw["holdout"]]
    lp = np.log(cal["sold_price_usd"])
    X = np.column_stack([np.ones(len(cal)), np.log(cal["bids"]), pd.get_dummies(cal["file"], drop_first=True).values])
    beta, *_ = np.linalg.lstsq(X.astype(float), lp.values, rcond=None)
    per_seller = gw.groupby("seller_id").size()
    single = gw[~gw["is_lot"]]
    out["goodwill_pooled"] = {
        "n": len(gw), "sellers": int(gw["seller_id"].nunique()),
        "bids_conditional_on_sold_fit_calibration": fit_counts(cal["bids"].values, zero_truncated=True),
        "bids_conditional_on_sold": describe(cal["bids"]),
        "bids_holdout": describe(gw.loc[gw["holdout"], "bids"]),
        "share_single_bid": float((gw["bids"] == 1).mean()),
        "listings_per_seller": describe(per_seller.values),
        "listings_per_seller_fit": fit_counts(per_seller.values, zero_truncated=True),
        "gini_listings_per_seller": gini(per_seller.values),
        "top_seller_share": float(per_seller.max() / per_seller.sum()),
        "top10pct_seller_share": float(per_seller.sort_values(ascending=False).head(max(1, len(per_seller) // 10)).sum()
                                       / per_seller.sum()),
        "seller_icc_log_price_within_file": {f: icc_oneway(np.log(s["sold_price_usd"]), s["seller_id"])
                                             for f, s in gw.groupby("file")},
        "ols_log_price_on_log_bids_file_fe_calibration": {"slope_log_bids": float(beta[1]), "n": len(cal)},
        "ols_log_price_on_log_bids_file_fe_holdout": _slope(gw[gw["holdout"]]),
        "log_price_sd_single_items_by_file": single.groupby("file")["sold_price_usd"].apply(lambda v: float(np.log(v).std())).to_dict(),
        "log_price_sd_lots_by_file": gw[gw["is_lot"]].groupby("file")["sold_price_usd"].apply(lambda v: float(np.log(v).std())).to_dict(),
        "end_hour_share_tz_unknown": gw["ended_at"].dt.hour.value_counts(normalize=True).sort_index().to_dict(),
        "end_dow_share_tz_unknown_(0=Mon)": gw["ended_at"].dt.day_of_week.value_counts(normalize=True).sort_index().to_dict(),
        "share_end_18_to_20_tz_unknown": float(gw["ended_at"].dt.hour.between(18, 20).mean()),
        "pokemon_rows": int(gw["title"].str.contains("pokemon|pokémon", case=False).sum()),
    }

    # eBay sold comps (no bids, auction vs fixed price not recorded)
    eb = []
    for p in sorted(G.glob("*.csv")):
        if p.stem.startswith("goodwill-"):
            continue
        d = pd.read_csv(p)
        d["file"] = p.stem
        eb.append(d)
    eb = pd.concat(eb, ignore_index=True)
    out["ebay_comps"] = {"rows": len(eb), "dup_item_id": int(eb["item_id"].duplicated().sum()),
                         "condition_values": eb["condition"].value_counts().to_dict(), "by_file": {}}
    for f, s in eb.groupby("file"):
        out["ebay_comps"]["by_file"][f] = {"n": len(s), "price": describe(s["sold_price_usd"]),
                                           "log_price_sd": float(np.log(s["sold_price_usd"]).std()),
                                           "price_fit": fit_positive(s["sold_price_usd"].values)}
    rg = eb[eb["file"].str.startswith("retro-video-games")]
    hw = eb[eb["file"].str.startswith("hotwheels")]
    out["ebay_comps"]["retro_games_pooled_fit"] = fit_positive(rg["sold_price_usd"].values)
    out["ebay_comps"]["hotwheels_pooled_fit"] = fit_positive(hw["sold_price_usd"].values)
    out["ebay_comps"]["pokemon_rows"] = int(eb["title"].str.contains("pokemon|pokémon", case=False).sum())
    lego = gw[gw["file"].str.contains("lego")]
    out["goodwill_lego_single_items_fit"] = fit_positive(lego.loc[~lego["is_lot"], "sold_price_usd"].values)
    save("goodwill", out)


if __name__ == "__main__":
    main()
