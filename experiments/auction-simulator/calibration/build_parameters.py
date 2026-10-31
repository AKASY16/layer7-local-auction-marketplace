"""Build calibration/parameters.yaml and parameter_sources.csv.

EMPIRICAL values are read from statistical_analysis/results/*.json (or recomputed
from raw data here), so every number traces back to a script. LITERATURE values
quote the paper. ASSUMED values are written by hand with the reason. Values
tuned by simulated moments (tune.py) are read from calibration/tuned.yaml and
stay ASSUMED: matching a target does not make a behavioural parameter observed.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "statistical_analysis"))
from common import DATA  # noqa: E402

R = HERE / "statistical_analysis" / "results"
VERSION = "1.0.0"


def j(name):
    return json.loads((R / f"{name}.json").read_text(encoding="utf-8"))


def rebid_mixture():
    """Fit a two-component lognormal split at 10 minutes to same-bidder re-bid gaps (Jank & Shmueli)."""
    from analyze_jank_shmueli import load_main
    df = load_main()
    df = df[~df["holdout"]].sort_values(["auctionid", "bidder", "bidtime"])
    gap = (df.groupby(["auctionid", "bidder"])["bidtime"].diff().dropna() * 1440).to_numpy()
    gap = gap[gap > 0]
    fast, slow = gap[gap <= 10], gap[gap > 10]
    return {"n": len(gap), "fast_share": len(fast) / len(gap),
            "fast_median": float(np.median(fast)), "fast_logsd": float(np.log(fast).std()),
            "slow_median": float(np.median(slow)), "slow_logsd": float(np.log(slow).std())}


def main():
    js, gw, ms, sw = j("jank_shmueli"), j("goodwill"), j("maxsold"), j("swoopo")
    rb = rebid_mixture()
    P = {}

    def add(name, value, unit, meaning, source, method, n, market, uncertainty, cls, transfer=""):
        P[name] = {"value": value, "unit": unit, "meaning": meaning, "source": source, "method": method,
                   "n": n, "market": market, "uncertainty": uncertainty, "class": cls, "transfer_to_layer7": transfer}

    # ---------------- EMPIRICAL -------------------------------------------------
    rg = gw["ebay_comps"]["retro_games_pooled_fit"]
    add("price_logsd_retro_game", round(rg["lognorm_sigma_log"], 3), "log KRW", "sd of log value, retro games",
        "ebay-sold-comps retro-video-games-cib/lots", "lognormal MLE (AIC best of 4)", rg["n"],
        "US eBay sold listings 2026-08/09", "n=120; CIB and lots mixed", "EMPIRICAL",
        "dispersion only; level is ASSUMED")
    lg = gw["goodwill_lego_single_items_fit"]
    add("price_logsd_figure", round(lg["lognorm_sigma_log"], 3), "log KRW", "sd of log value, figures/toys",
        "ShopGoodwill LEGO, non-lot titles", "lognormal MLE", lg["n"], "US Goodwill auctions 2026-06",
        f"hotwheels eBay gives {gw['ebay_comps']['hotwheels_pooled_fit']['lognorm_sigma_log']:.2f} (n=60)",
        "EMPIRICAL", "LEGO used as proxy for figures")
    sd_single = list(gw["goodwill_pooled"]["log_price_sd_single_items_by_file"].values())
    add("price_logsd_limited_goods", round(float(np.median(sd_single)), 3), "log KRW",
        "sd of log value, limited goods", "ShopGoodwill 12 files, non-lot titles",
        "median over files of sd(log price)", gw["goodwill_pooled"]["n"], "US Goodwill auctions 2026-06..09",
        f"file range {min(sd_single):.2f}-{max(sd_single):.2f}", "EMPIRICAL", "category proxy")
    lps = gw["goodwill_pooled"]["listings_per_seller_fit"]["negbin"]
    add("seller_listings_nb_size", round(lps["size"], 3), "-", "NB size (dispersion) of listings per seller",
        "ShopGoodwill", "zero-truncated NB MLE on listings per seller", gw["goodwill_pooled"]["sellers"],
        "US Goodwill stores (institutional sellers)", "sold-only listings; stores are not C2C sellers", "EMPIRICAL",
        "shape only, mean set by scale")
    add("rebid_fast_share", round(rb["fast_share"], 3), "share", "share of same-bidder re-bids within 10 min",
        "Jank & Shmueli 9 datasets, calibration split", "empirical share", rb["n"], "eBay 2003 hard close",
        "split point 10 min chosen by hand", "EMPIRICAL")
    add("rebid_fast_median_min", round(rb["fast_median"], 3), "min", "median delay, fast re-bid", "Jank & Shmueli",
        "median of gaps <= 10 min", rb["n"], "eBay 2003", "", "EMPIRICAL")
    add("rebid_fast_logsd", round(rb["fast_logsd"], 3), "log min", "log sd, fast re-bid", "Jank & Shmueli",
        "sd of log gap <= 10 min", rb["n"], "eBay 2003", "", "EMPIRICAL")
    add("rebid_slow_median_min", round(rb["slow_median"], 1), "min", "median delay, slow re-bid", "Jank & Shmueli",
        "median of gaps > 10 min", rb["n"], "eBay 2003", "", "EMPIRICAL")
    add("rebid_slow_logsd", round(rb["slow_logsd"], 3), "log min", "log sd, slow re-bid", "Jank & Shmueli",
        "sd of log gap > 10 min", rb["n"], "eBay 2003", "", "EMPIRICAL")

    # ---------------- LITERATURE ------------------------------------------------
    add("snipe_offset_max_sec", 120, "s", "snipes land uniformly in the last N seconds",
        "Shmueli, Russo & Jank 2007, Table 4 and 5.3", "last stage lasts ~2 min or less, alpha3 ~ 1 (uniform)",
        "9 eBay datasets", "eBay hard close", "d2 0.5-2 min across datasets", "LITERATURE")
    add("snipe_transmit_fail_prob", 0.045, "prob", "late bid fails to register", "Roth & Ockenfels 2002, sec. II",
        "esnipe statistic, Sept 2000", "~4,200 bids/day", "eBay 2000", "one service, one month", "LITERATURE")
    add("snipe_unavailable_prob", 0.10, "prob", "planned late bidder not available at the end",
        "Roth & Ockenfels 2002, survey", "median self-reported frequency", "survey responders", "eBay 2000",
        "self-report", "LITERATURE")
    add("wtp_idio_logsd", 0.25, "log", "idiosyncratic buyer-item valuation dispersion",
        "Bimpikis et al. 2020, Table 11", "idiosyncratic SD / mean valuation: MU 2978/18594=0.16, UD 4313/15459=0.28",
        "74 MU + 113 UD bidders", "B2B iPhone liquidation", "B2B resellers, not collectors", "LITERATURE")
    add("buyer_daily_retention", 0.97, "prob/day", "probability an active buyer stays another day",
        "Bimpikis et al. 2020, Table 11", "MU 0.968 (UD 0.843)", "187 bidders", "B2B", "B2B pool dynamics",
        "LITERATURE")
    add("supply_peak_ratio", 1.50, "ratio", "top-4-hour share of auction ends / of bids (crowded scenario)",
        "Simonsohn 2010, sec. 1 and Fig. 2", "37.6% of auctions vs 25.0% of bids end/placed 5-9 pm (Pacific)",
        "14,973 auctions, 44,735 bids", "eBay US DVDs 2008", "US eBay hours, applied as a ratio only", "LITERATURE")
    add("thickness_elasticity", 0.15, "-", "elasticity of visit rate in number of relevant auctions ending soon",
        "baseline value; scenario D uses 0.47 from Bimpikis et al. 2020 Fig. 13", "ASSUMED for baseline",
        "", "", "no C2C estimate exists", "ASSUMED")

    # ---------------- ASSUMED ---------------------------------------------------
    fx = 1350
    med_rg = float(np.exp(rg["lognorm_mu_log"]))
    med_lg = float(np.exp(lg["lognorm_mu_log"]))
    add("fx_krw_per_usd_anchor", fx, "KRW/USD", "only used to sanity-check KRW medians", "-", "-", "", "", "", "ASSUMED")
    add("price_median_krw_tcg", 40000, "KRW", "median base value, TCG (cards, boxes)", "-",
        "no TCG price data in inputs", "", "LAYER7 (hypothetical)", "unknown", "ASSUMED")
    add("price_median_krw_figure", 45000, "KRW", "median base value, figures/toys", "-",
        f"US LEGO median ${med_lg:.0f} x {fx} = {med_lg * fx:,.0f}; set higher for figures", "", "", "", "ASSUMED")
    add("price_median_krw_retro_game", 60000, "KRW", "median base value, retro games", "-",
        f"US eBay median ${med_rg:.0f} x {fx} = {med_rg * fx:,.0f}; set lower for Korean market", "", "", "", "ASSUMED")
    add("price_median_krw_limited_goods", 35000, "KRW", "median base value, limited goods", "-", "", "", "", "",
        "ASSUMED")
    add("price_logsd_tcg", 1.2, "log KRW", "sd of log value, TCG", "-",
        "no TCG data; inside observed 0.72-1.37 range of other collectibles", "", "", "", "ASSUMED")
    vq = ms["item"]["views_per_item"]
    add("item_appeal_logsd", 0.8, "log", "item-level browse appeal (popularity) dispersion", "-",
        f"below MaxSold views-per-item log spread (q10 {vq['q10']:.0f}, q90 {vq['q90']:.0f} -> sd ~"
        f"{np.log(vq['q90'] / vq['q10']) / 2.563:.2f}), which also mixes lot size and auction effects",
        "", "", "", "ASSUMED")
    add("appeal_wtp_elasticity", 0.0, "-", "WTP multiplier = appeal ** this (popular items valued higher)", "-",
        "tuned so the sold-only price ~ bids slope approaches Goodwill", "", "", "", "ASSUMED")
    add("series_zipf_exponent", 1.0, "-", "popularity of series within a category", "-", "", "", "", "", "ASSUMED")
    add("rarity_value_multiplier", [1.0, 1.6, 3.0, 8.0], "x", "value multiplier common/uncommon/rare/ultra",
        "-", "", "", "", "", "ASSUMED")
    add("condition_share", [0.25, 0.35, 0.40], "share", "new / like_new / used", "-", "", "", "", "", "ASSUMED")
    add("condition_value_multiplier", [1.2, 1.0, 0.75], "x", "value multiplier by condition", "-", "", "", "", "",
        "ASSUMED")
    add("seller_primary_category_share", 0.8, "share", "listings in the seller's main category", "-", "", "", "", "",
        "ASSUMED")
    sq = js["pooled"]["openbid_over_price_quantiles_calibration"]
    add("start_price_ratio_quantiles", [round(x, 5) for x in sq], "x value",
        "quantile function (21 points) of opening bid / closing price; start = ratio x estimated value",
        "Jank & Shmueli 9 datasets, calibration split", "empirical quantiles of openbid/price",
        js["pooled"]["bids_per_auction_fit_calibration"]["n"], "eBay 2003",
        f"median {sq[10]:.3f}; closing price, not value, in the denominator", "EMPIRICAL",
        "LAYER7 start-price rule unknown; eBay sellers' habit is used")
    add("start_price_min_krw", 1000.0, "KRW", "minimum starting price", "-", "", "", "", "", "ASSUMED")
    add("duration_share", [0.35, 0.35, 0.30], "share", "24 / 48 / 72 h", "-", "", "", "", "", "ASSUMED")
    add("visit_rate_median_per_day", 1.0, "visits/day", "median organic visit rate before scaling", "-", "",
        "", "", "", "ASSUMED")
    add("visit_rate_scale", 1.0, "x", "global visit-rate scale (tuned)", "-", "", "", "", "", "ASSUMED")
    add("visit_rate_logsd", 1.0, "log", "buyer activity heterogeneity", "-",
        f"checked against bids-per-bidder Gini: J&S {js['pooled']['gini_bids_per_bidder']:.2f}, "
        f"Swoopo {sw['traces']['gini_bids_per_user']:.2f}", "", "", "", "ASSUMED")
    add("buyer_hour_offset_sd", 1.5, "h", "individual shift of the activity profile", "-", "", "", "", "", "ASSUMED")
    add("weekend_activity_factor", 1.15, "x", "weekend visit multiplier", "-", "", "", "", "", "ASSUMED")
    add("buyer_secondary_category_prob", 0.3, "prob", "interest in each non-main category", "-", "", "", "", "",
        "ASSUMED")
    add("buyer_n_favorite_series", 2, "count", "favourite series per interest category", "-", "", "", "", "",
        "ASSUMED")
    add("favorite_series_wtp_multiplier", 1.3, "x", "WTP uplift for favourite series", "-", "", "", "", "", "ASSUMED")
    add("favorite_series_view_weight", 3.0, "x", "browse weight for favourite series", "-", "", "", "", "", "ASSUMED")
    add("buyer_price_level_logsd", 0.3, "log", "buyer-level WTP scale", "-", "", "", "", "", "ASSUMED")
    add("budget_items_median", 3.0, "items", "30-day budget in units of main-category median value", "-", "", "",
        "", "", "ASSUMED")
    add("budget_logsd", 0.7, "log", "budget dispersion", "-", "", "", "", "", "ASSUMED")
    add("buyer_initial_active_share", 0.7, "share", "buyers active from day 0; rest join uniformly", "-", "", "",
        "", "", "ASSUMED")
    add("style_share_early", 0.45, "share", "proxy-early bidders (tuned)", "-", "", "", "", "", "ASSUMED")
    add("style_share_incremental", 0.40, "share", "incremental re-bidders (tuned)", "-", "", "", "", "", "ASSUMED")
    add("style_share_sniper", 0.15, "share", "late bidders (tuned)", "-", "", "", "", "", "ASSUMED")
    add("rebid_propensity_mean", 0.6, "prob", "mean prob. of returning when outbid", "-", "", "", "", "", "ASSUMED")
    add("rebid_propensity_concentration", 4.0, "-", "Beta concentration", "-", "", "", "", "", "ASSUMED")
    add("incremental_mean_extra_steps", 1.0, "increments", "extra increments above minimum", "-", "", "", "", "",
        "ASSUMED")
    add("early_act_prob", 0.3, "prob", "non-sniper bids at once when the end is more than the window away (tuned)",
        "-", "otherwise watches and may return near the end", "", "", "", "ASSUMED")
    add("act_now_window_min", 60.0, "min", "inside this window before the end viewers act at once", "-", "", "",
        "", "", "ASSUMED")
    add("session_window_min", 10.0, "min", "re-bids this soon after being outbid skip the hour availability check",
        "-", "J&S: 70% of same-bidder re-bids come within 10 min", "", "", "", "ASSUMED")
    add("watch_return_prob", 0.25, "prob", "viewer comes back near the end (tuned)", "-", "", "", "", "", "ASSUMED")
    add("watch_return_mean_min_before_end", 45.0, "min", "how long before the end watchers return", "-", "", "",
        "", "", "ASSUMED")
    add("attention_mean_views", 3.0, "auctions", "mean auctions viewed per organic visit", "-", "", "", "", "",
        "ASSUMED")
    add("attention_thickness_elasticity", 0.0, "-", "elasticity of views per visit in the thickness signal",
        "-", "0 in baseline; scenario D sets 1 so that bidders per auction rise with thickness "
        "(Bimpikis et al. 2020 Fig. 13 reports bidders/auction, not visits)", "", "", "", "ASSUMED")
    add("ending_soon_boost", 2.0, "x", "extra browse weight for auctions about to end", "-",
        "mirrors 'ending soon' sort; drives attention competition", "", "", "", "ASSUMED")
    add("ending_soon_tau_hours", 6.0, "h", "decay of the ending-soon boost", "-", "", "", "", "", "ASSUMED")
    add("alert_follow_prob", 0.3, "prob", "buyer follows an interest category", "-", "", "", "", "", "ASSUMED")
    add("alert_open_prob", 0.4, "prob", "follower opens a new-listing alert", "-",
        "source of the early-bidding stage (BARISTA stage 1)", "", "", "", "ASSUMED")
    add("alert_delay_mean_min", 180.0, "min", "delay from listing to alert visit", "-", "", "", "", "", "ASSUMED")
    add("thickness_window_hours", 6.0, "h", "window for the thickness signal", "-", "", "", "", "", "ASSUMED")
    add("thickness_reference_count", 3.0, "auctions", "count at which multiplier = 1", "-", "", "", "", "",
        "ASSUMED")
    add("thickness_multiplier_min", 0.5, "x", "lower clamp", "-", "", "", "", "", "ASSUMED")
    add("thickness_multiplier_max", 2.5, "x", "upper clamp", "-", "", "", "", "", "ASSUMED")

    tuned_p = HERE / "tuned.yaml"
    if tuned_p.exists():
        tuned = yaml.safe_load(tuned_p.read_text(encoding="utf-8"))
        for k, v in tuned["values"].items():
            P[k]["value"] = v
            if k in tuned.get("fixed_from_previous_pass", []):
                P[k]["method"] = "simulated-moment grid search, earlier pass (kept fixed in the final pass)"
            elif k in tuned.get("fixed_by_hand", []):
                P[k]["method"] = "set by hand trials against the same targets before the grid search"
            else:
                P[k]["method"] = f"simulated-moment grid search, seed {tuned['seed']} ({tuned['objective']})"
            P[k]["class"] = "ASSUMED"

    # validation targets (not generator inputs)
    d3 = {k: v for k, v in js["by_dataset"].items() if k.endswith("_3d")}
    targets = {
        "js3_bids_per_auction_mean": float(np.mean([v["bids_per_auction"]["mean"] for v in d3.values()])),
        "js3_bidders_per_auction_mean": float(np.mean([v["bidders_per_auction"]["mean"] for v in d3.values()])),
        "js_bids_per_bidder_in_auction_mean": js["pooled"]["bids_per_bidder_in_auction"]["mean"],
        "js_share_repeat_bidder_pairs": js["pooled"]["share_bidder_auction_pairs_with_repeat_bid"],
        "js_cal_bids_per_bidder_in_auction_mean": js["pooled"]["calibration_pairs"]["bids_per_bidder_in_auction_mean"],
        "js_cal_share_repeat_bidder_pairs": js["pooled"]["calibration_pairs"]["share_repeat_pairs"],
        "js_hold_bids_per_bidder_in_auction_mean": js["pooled"]["holdout_pairs"]["bids_per_bidder_in_auction_mean"],
        "js_hold_share_repeat_bidder_pairs": js["pooled"]["holdout_pairs"]["share_repeat_pairs"],
        "js_hold_bids_per_auction_nb_size": js["pooled"]["bids_per_auction_fit_holdout"]["negbin"]["size"],
        "goodwill_hold_slope_log_price_log_bids": gw["goodwill_pooled"]["ols_log_price_on_log_bids_file_fe_holdout"]["slope_log_bids"],
        "js3_share_bids_last_5min": float(np.mean([v["timing"]["last_5min"] for v in d3.values()])),
        "js3_share_bids_last_60min": float(np.mean([v["timing"]["last_60min"] for v in d3.values()])),
        "js3_share_auctions_last_bid_5min": float(np.mean([v["share_auctions_last_bid_within_5min"] for v in d3.values()])),
        "js3_share_bids_first_10pct": float(np.mean([v["timing"]["first_10pct_time"] for v in d3.values()])),
        "js_bids_per_auction_nb_size": js["pooled"]["bids_per_auction_fit_calibration"]["negbin"]["size"],
        "js_gini_bids_per_bidder": js["pooled"]["gini_bids_per_bidder"],
        "swoopo_gini_bids_per_user": sw["traces"]["gini_bids_per_user"],
        "goodwill_slope_log_price_log_bids": gw["goodwill_pooled"]["ols_log_price_on_log_bids_file_fe_calibration"]["slope_log_bids"],
        "maxsold_slope_log1p_bids_log1p_views": ms["item"]["ols_log1p_bids_on_log1p_views"]["slope"],
        "maxsold_share_zero_bid_items": ms["item"]["share_zero_bid_items_full"],
    }
    doc = {"version": VERSION, "classes": {"EMPIRICAL": "estimated from the raw files by the scripts in statistical_analysis/",
                                           "LITERATURE": "taken from one of the four papers (quoted in method)",
                                           "ASSUMED": "no direct evidence; set for simulation (tuned ones say so)"},
           "params": P, "validation_targets": targets}
    (HERE / "parameters.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    rows = [{"name": k, **{c: (json.dumps(v[c]) if isinstance(v[c], list) else v[c]) for c in
                           ("value", "unit", "meaning", "source", "method", "n", "market", "uncertainty", "class",
                            "transfer_to_layer7")}} for k, v in P.items()]
    pd.DataFrame(rows).to_csv(HERE / "parameter_sources.csv", index=False, encoding="utf-8-sig")
    print("params:", len(P), pd.Series([v["class"] for v in P.values()]).value_counts().to_dict())
    print("targets:", json.dumps(targets, indent=0))


if __name__ == "__main__":
    main()
