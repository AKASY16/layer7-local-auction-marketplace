"""MaxSold auction / item / bid parquet files (DuckDB, full scan).

Structure found in the files (not assumed):
- train-00000-of-00001.parquet: one row per auction event (an estate sale with many lots).
- item_data.parquet: one row per lot, item_end_time is the lot's actual close.
- bid_data.parquet: one row per price step. bid_is_proxy=True rows are steps the
  system placed for a standing maximum, so they are not separate visits or
  decisions. There is no bidder identifier in any file.
Timestamps carry a UTC offset (-0400/-0500, i.e. North American Eastern), so the
wall-clock hour is read from the string itself.
"""
import duckdb
import numpy as np

from common import DATA, describe, fit_counts, fit_positive, is_holdout, save
import barista  # noqa: E402

M = (DATA / "Maxsold").as_posix()
A = f"read_parquet('{M}/train-00000-of-00001.parquet')"
I = f"read_parquet('{M}/item_data.parquet')"
B = f"read_parquet('{M}/bid_data.parquet')"
TS = "%Y-%m-%dT%H:%M:%S%z"


def main():
    con = duckdb.connect()
    con.execute("SET threads TO 8")
    q = lambda s: con.execute(s).fetchdf()
    one = lambda s: con.execute(s).fetchone()
    out = {"source": "MaxSold (Hugging Face jpearce610); estate-sale online auctions, Canada/US",
           "closing_rule": "soft close: auction_extended_bidding flag with threshold/interval columns; "
                           "lots close in a staggered sequence after auction_ends"}

    con.execute(f"""CREATE TEMP TABLE auc AS SELECT auction_id, auction_item_count, auction_total_viewed,
        auction_total_bid_count, auction_total_winning_price, auction_extended_bidding,
        auction_extended_bidding_interval, auction_extended_bidding_threshold,
        epoch(strptime(auction_starts, '{TS}')) AS t_start, epoch(strptime(auction_ends, '{TS}')) AS t_end,
        epoch(strptime(auction_last_item_closes, '{TS}')) AS t_last,
        CAST(substr(auction_ends, 12, 2) AS INT) AS end_hour_local,
        dayofweek(CAST(substr(auction_ends, 1, 10) AS DATE)) AS end_dow,
        substr(auction_starts, 1, 10) AS start_date
        FROM {A}""")
    con.execute(f"""CREATE TEMP TABLE itm AS SELECT i.item_id, i.auction_id, i.item_viewed, i.item_current_bid,
        i.item_bid_count, i.item_bidding_extended, i.item_number_of_images, i.item_starting_bid,
        epoch(strptime(i.item_start_time, '{TS}')) AS t_start, epoch(strptime(i.item_end_time, '{TS}')) AS t_close,
        a.t_end AS t_sched
        FROM {I} i JOIN auc a USING (auction_id)""")

    # --- integrity --------------------------------------------------------
    chk = {}
    chk["auctions"] = one("SELECT count(*) FROM auc")[0]
    chk["items"] = one("SELECT count(*) FROM itm")[0]
    chk["bids_rows"] = one(f"SELECT count(*) FROM {B}")[0]
    chk["items_without_auction"] = one(f"SELECT count(*) FROM {I} i ANTI JOIN auc a USING (auction_id)")[0]
    chk["bids_without_item"] = one(f"SELECT count(*) FROM {B} b ANTI JOIN {I} i USING (item_id)")[0]
    chk["dup_item_id"] = one(f"SELECT count(*) FROM (SELECT item_id FROM {I} GROUP BY 1 HAVING count(*) > 1)")[0]
    chk["dup_bid_rows"] = one(f"SELECT count(*) - count(DISTINCT (item_id, bid_id)) FROM {B}")[0]
    chk["auction_start_range_p0_p1_p99_p100"] = q(
        "SELECT quantile_disc(start_date, [0, 0.01, 0.99, 1]) AS q FROM auc")["q"][0].tolist()
    chk["auctions_end_before_start"] = one("SELECT count(*) FROM auc WHERE t_end <= t_start")[0]
    chk["item_bid_count_vs_rows_mismatch"] = one(f"""SELECT count(*) FROM itm i LEFT JOIN
        (SELECT item_id, count(*) n FROM {B} GROUP BY 1) b USING (item_id)
        WHERE coalesce(b.n, 0) <> i.item_bid_count""")[0]
    chk["final_price_ne_max_bid"] = one(f"""SELECT count(*) FROM itm i JOIN
        (SELECT item_id, max(bid_amount) m FROM {B} GROUP BY 1) b USING (item_id)
        WHERE abs(b.m - i.item_current_bid) > 1e-6""")[0]
    chk["extended_bidding_params"] = q("""SELECT auction_extended_bidding, auction_extended_bidding_interval,
        auction_extended_bidding_threshold, count(*) n FROM auc GROUP BY ALL""").to_dict("records")
    chk["starting_bid_values"] = q("SELECT item_starting_bid, count(*) n FROM itm GROUP BY 1").to_dict("records")
    out["checks"] = chk

    # --- auction level ----------------------------------------------------
    ad = q("""SELECT auction_item_count, (t_end - t_start) / 86400 AS dur_days, (t_last - t_end) / 60 AS tail_min,
              end_hour_local, end_dow, auction_total_viewed FROM auc""")
    ad = ad[(ad["dur_days"] > 0) & (ad["dur_days"] < 60)]
    out["auction"] = {
        "items_per_auction": describe(ad["auction_item_count"]),
        "duration_days": describe(ad["dur_days"]),
        "last_lot_close_minus_scheduled_end_min": describe(ad["tail_min"]),
        "end_hour_local_share": ad["end_hour_local"].value_counts(normalize=True).sort_index().to_dict(),
        "end_dow_share_(0=Sun)": ad["end_dow"].value_counts(normalize=True).sort_index().to_dict(),
        "share_end_19_to_21_local": float(ad["end_hour_local"].between(19, 21).mean()),
        "total_viewed": describe(ad["auction_total_viewed"]),
    }

    # --- item level -------------------------------------------------------
    s = q("""SELECT item_bid_count, item_viewed, item_current_bid, item_bidding_extended, item_number_of_images,
             (t_close - t_sched) / 60 AS close_minus_sched_min, auction_id
             FROM itm USING SAMPLE 400000 ROWS (reservoir, 42)""")
    s["holdout"] = s["auction_id"].map(is_holdout)
    cal = s[~s["holdout"]]
    zero_share = one("SELECT avg(CASE WHEN item_bid_count = 0 THEN 1 ELSE 0 END) FROM itm")[0]
    lv, lb = np.log1p(cal["item_viewed"]), np.log1p(cal["item_bid_count"])
    slope, icpt = np.polyfit(lv, lb, 1)
    sold = cal[cal["item_bid_count"] > 0]
    out["item"] = {
        "sample_rows": len(s), "sample_note": "reservoir sample of 400k lots, 70/30 split by auction_id",
        "share_zero_bid_items_full": zero_share,
        "bid_steps_per_item_full": q("""SELECT avg(item_bid_count) mean, quantile_cont(item_bid_count, [0.25, 0.5, 0.75, 0.9, 0.99]) q
                                       FROM itm""").to_dict("records")[0],
        "bid_steps_per_item_fit_calibration": fit_counts(cal["item_bid_count"].values),
        "bid_steps_per_item_holdout": describe(s.loc[s["holdout"], "item_bid_count"]),
        "views_per_item": describe(cal["item_viewed"]),
        "corr_log1p_views_log1p_bids": float(np.corrcoef(lv, lb)[0, 1]),
        "ols_log1p_bids_on_log1p_views": {"slope": slope, "intercept": icpt},
        "spearman_views_bids": float(cal[["item_viewed", "item_bid_count"]].corr("spearman").iloc[0, 1]),
        "final_price_sold_items": describe(sold["item_current_bid"]),
        "final_price_fit_sold": fit_positive(sold["item_current_bid"].values),
        "share_items_extended_full": one("SELECT avg(CASE WHEN item_bidding_extended THEN 1 ELSE 0 END) FROM itm")[0],
        "close_minus_scheduled_auction_end_min": describe(cal["close_minus_sched_min"]),
        "extended_vs_not_close_offset_min": cal.groupby("item_bidding_extended")["close_minus_sched_min"].median().to_dict(),
    }

    # --- bid level (full scan) --------------------------------------------
    con.execute(f"""CREATE TEMP TABLE bid AS SELECT b.item_id, b.bid_id, b.bid_amount, b.bid_is_proxy,
        epoch(strptime(b.bid_time, '{TS}')) AS t, CAST(substr(b.bid_time, 12, 2) AS INT) AS hour_local,
        i.t_start, i.t_close, i.t_sched, i.auction_id
        FROM {B} b JOIN itm i USING (item_id)""")
    bl = {}
    bl["proxy_share"] = one("SELECT avg(CASE WHEN bid_is_proxy THEN 1 ELSE 0 END) FROM bid")[0]
    bl["manual_bids"] = one("SELECT count(*) FROM bid WHERE NOT bid_is_proxy")[0]
    bl["manual_bids_per_item_with_bids"] = q("""SELECT avg(n) mean, quantile_cont(n, [0.25, 0.5, 0.75, 0.9, 0.99]) q FROM
        (SELECT item_id, count(*) n FROM bid WHERE NOT bid_is_proxy GROUP BY 1)""").to_dict("records")[0]
    bl["bids_outside_item_window"] = one("SELECT count(*) FROM bid WHERE t < t_start OR t > t_close + 1")[0]
    bl["manual_timing_share"] = q("""SELECT
        avg(CASE WHEN t_close - t <= 60 THEN 1 ELSE 0 END) last_1min_before_actual_close,
        avg(CASE WHEN t_close - t <= 300 THEN 1 ELSE 0 END) last_5min_before_actual_close,
        avg(CASE WHEN t_close - t <= 3600 THEN 1 ELSE 0 END) last_60min_before_actual_close,
        avg(CASE WHEN t > t_sched THEN 1 ELSE 0 END) after_scheduled_auction_end,
        avg(CASE WHEN (t - t_start) / nullif(t_sched - t_start, 0) <= 0.1 THEN 1 ELSE 0 END) first_10pct_of_scheduled
        FROM bid WHERE NOT bid_is_proxy""").to_dict("records")[0]
    bl["manual_bid_hour_local_share"] = q("""SELECT hour_local, count(*) * 1.0 / sum(count(*)) OVER () s
        FROM bid WHERE NOT bid_is_proxy GROUP BY 1 ORDER BY 1""").set_index("hour_local")["s"].to_dict()
    gaps = q("""SELECT (t - lag(t) OVER (PARTITION BY item_id ORDER BY t, bid_id)) / 60 AS gap_min
        FROM (SELECT * FROM bid WHERE NOT bid_is_proxy AND item_id IN
              (SELECT item_id FROM itm USING SAMPLE 100000 ROWS (reservoir, 7)))""")["gap_min"].dropna()
    bl["manual_interbid_gap_min_sample"] = describe(gaps.values)
    # jump size between consecutive price steps relative to price (increment behaviour)
    inc = q("""SELECT bid_amount - lag(bid_amount) OVER (PARTITION BY item_id ORDER BY bid_id) AS d, bid_amount
        FROM bid WHERE item_id IN (SELECT item_id FROM itm USING SAMPLE 50000 ROWS (reservoir, 11))""").dropna()
    bl["price_step_abs"] = describe(inc["d"].values)
    bl["price_step_rel"] = describe((inc["d"] / inc["bid_amount"].clip(lower=1)).values)
    out["bid"] = bl

    # BARISTA on manual bids, time normalised to [0, 1] by the scheduled end; bids in the
    # extension (after the scheduled end) are excluded, so stage 3 is truncated.
    sm = q("""SELECT (t - t_start) / (t_sched - t_start) AS u, (t_sched - t_start) / 86400 AS dur_days, auction_id
        FROM bid WHERE NOT bid_is_proxy AND t <= t_sched AND t_sched > t_start
        USING SAMPLE 200000 ROWS (reservoir, 3)""")
    sm = sm[(sm["u"] >= 0) & (sm["u"] <= 1)]
    sm["holdout"] = sm["auction_id"].map(is_holdout)
    med_dur = float(sm["dur_days"].median())
    d2_grid = np.array([0.5, 1, 2, 5, 10, 30, 60]) / (1440 * med_dur)
    fr = barista.fit(sm.loc[~sm["holdout"], "u"].values, 1.0, d2_grid=d2_grid)
    from scipy import stats
    ks = stats.kstest(sm.loc[sm["holdout"], "u"].values, fr["chosen"].cdf)
    out["barista_normalised_manual_bids"] = {
        "note": "soft-close market, bids after scheduled end excluded; descriptive comparison only",
        "median_duration_days": med_dur, "lrt_choice": fr["lrt_choice"], "params": fr["chosen"].to_dict(),
        "ks_holdout": {"D": ks.statistic, "p": ks.pvalue}, "models": fr["models"],
        "u_histogram_20bins": np.histogram(sm["u"], bins=20, range=(0, 1))[0].tolist(),
    }
    save("maxsold", out)


if __name__ == "__main__":
    main()
