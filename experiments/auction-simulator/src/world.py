"""Exogenous world: sellers, items, buyers, listing schedule and buyer visit candidates.

Everything here is fixed before any end time is chosen. A different end-time
policy reuses the same World object, so buyer traits, valuations and the
candidate visit stream are identical across policies (common random numbers).
Times are minutes from the simulation origin (config start_date, KST).
"""
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

HOUR_PROFILES = {
    # ASSUMED relative activity by KST hour (mean 1). Shape only: evening peak,
    # lunch bump, deep night trough. No Korean bidding data was available.
    "korea_evening": [0.30, 0.18, 0.10, 0.06, 0.05, 0.06, 0.15, 0.40, 0.60, 0.65, 0.70, 0.75,
                      1.00, 0.90, 0.75, 0.75, 0.80, 0.90, 1.05, 1.30, 1.60, 1.80, 1.65, 0.95],
    "flat": [1.0] * 24,
}


def profile(name, blend_flat=0.0):
    if isinstance(name, list):
        v = np.array(name, float)
    else:
        v = np.array(HOUR_PROFILES[name], float)
    v = v / v.mean()
    v = (1 - blend_flat) * v + blend_flat
    return v / v.mean()


@dataclass
class World:
    cfg: dict
    origin: datetime
    horizon_min: float
    categories: list
    sellers: list = field(default_factory=list)
    items: list = field(default_factory=list)
    auctions: list = field(default_factory=list)
    buyers: list = field(default_factory=list)
    buyer_hour_profile: np.ndarray = None
    seller_end_profile: np.ndarray = None

    def hour_of(self, t):
        return int((self.origin.hour * 60 + self.origin.minute + t) // 60) % 24

    def dow_of(self, t):  # 0 = Monday
        return int((self.origin.weekday() * 1440 + self.origin.hour * 60 + t) // 1440) % 7


def _supply_profile(demand, kind, ratio):
    """Seller end-hour distribution.

    uniform: flat over 24 h. follow: proportional to buyer activity.
    crowded: demand**g, with g chosen so the top-4-hour share of supply is
    `ratio` times the top-4-hour share of demand (Simonsohn 2010: 37.6% vs 25.0%).
    """
    if kind == "uniform":
        return np.ones(24) / 24
    d = demand / demand.sum()
    if kind == "follow":
        return d
    top = np.argsort(d)[-4:]
    target = min(ratio * d[top].sum(), 0.95)
    lo, hi = 1.0, 12.0
    for _ in range(60):
        g = (lo + hi) / 2
        s = d ** g
        s /= s.sum()
        if s[np.argsort(s)[-4:]].sum() < target:
            lo = g
        else:
            hi = g
    return s


def build(cfg, seed):
    p = cfg["params"]
    sc = cfg["scale"]
    rng = np.random.default_rng([seed, 101])
    origin = datetime.fromisoformat(cfg["start_date"])
    days = sc["days"]
    horizon = days * 1440.0
    cats = cfg["categories"]
    w = World(cfg=cfg, origin=origin, horizon_min=horizon, categories=[c["name"] for c in cats])
    w.buyer_hour_profile = profile(cfg["buyer_hour_profile"], cfg.get("buyer_hour_blend_flat", 0.0))
    w.seller_end_profile = _supply_profile(w.buyer_hour_profile, cfg["seller_end_hour_mode"],
                                           p["supply_peak_ratio"])
    cat_idx = {c["name"]: i for i, c in enumerate(cats)}
    supply_share = np.array([c["supply_share"] for c in cats], float)
    supply_share /= supply_share.sum()
    demand_share = np.array([c["demand_share"] for c in cats], float)
    demand_share /= demand_share.sum()

    # --- series popularity per category (Zipf-like, ASSUMED) ----------------
    series = {}
    for c in cats:
        n = int(c["n_series"])
        pop = 1.0 / np.arange(1, n + 1) ** p["series_zipf_exponent"]
        series[c["name"]] = (np.array([f"{c['name']}_s{j + 1:02d}" for j in range(n)]), pop / pop.sum())

    # --- sellers: listing counts are Poisson-Gamma (NB) shaped ---------------
    n_s, n_a = sc["n_sellers"], sc["n_auctions"]
    wgt = rng.gamma(p["seller_listings_nb_size"], 1.0, n_s)
    counts = rng.multinomial(n_a, wgt / wgt.sum())
    for s in range(n_s):
        prim = rng.choice(len(cats), p=supply_share)
        pref_hour = int(rng.choice(24, p=w.seller_end_profile))
        w.sellers.append({"seller_id": s + 1, "primary_category": cats[prim]["name"],
                          "n_listings": int(counts[s]), "preferred_end_hour": pref_hour,
                          "listing_rate_per_day": counts[s] / days})

    # --- items and auctions --------------------------------------------------
    rar_names = ["common", "uncommon", "rare", "ultra"]
    rar_share = np.array(cfg["rarity_share"], float)
    rar_mult = np.array(p["rarity_value_multiplier"], float)
    cond_names = ["new", "like_new", "used"]
    cond_share = np.array(p["condition_share"], float)
    cond_mult = np.array(p["condition_value_multiplier"], float)
    dur_choices = np.array(cfg["duration_hours_choices"], float)
    dur_share = np.array(p["duration_share"], float)
    aid = 0
    latest_start = horizon - 72 * 60
    for s in w.sellers:
        for _ in range(s["n_listings"]):
            aid += 1
            ci = cat_idx[s["primary_category"]]
            if rng.random() > p["seller_primary_category_share"]:
                ci = rng.choice(len(cats), p=supply_share)
            c = cats[ci]
            names, pop = series[c["name"]]
            si = rng.choice(len(names), p=pop)
            sub = c["subcategories"][rng.integers(len(c["subcategories"]))]
            r = rng.choice(4, p=rar_share / rar_share.sum())
            k = rng.choice(3, p=cond_share / cond_share.sum())
            value = (p[f"price_median_krw_{c['name']}"] * np.exp(p[f"price_logsd_{c['name']}"] * rng.standard_normal())
                     * rar_mult[r] * cond_mult[k])
            value = float(max(1000.0, round(value, -2)))
            # opening bid / closing price ratio of real eBay auctions (Jank & Shmueli), applied to value
            q = p["start_price_ratio_quantiles"]
            start_ratio = float(np.interp(rng.random(), np.linspace(0, 1, len(q)), q))
            start_price = float(max(p["start_price_min_krw"], round(value * start_ratio, -3)))
            appeal = float(np.exp(p["item_appeal_logsd"] * rng.standard_normal()))
            w.items.append({"item_id": aid, "seller_id": s["seller_id"], "category": c["name"],
                            "subcategory": sub, "series": names[si], "condition": cond_names[k],
                            "rarity": rar_names[r], "estimated_value": value,
                            "similarity_group": f"{c['name']}|{names[si]}", "appeal": round(appeal, 4)})
            start = float(rng.uniform(0, latest_start))
            start = round(start)  # whole minutes
            dur = float(rng.choice(dur_choices, p=dur_share / dur_share.sum())) * 60
            end = _default_end(w, start, dur, s["preferred_end_hour"], rng)
            w.auctions.append({"auction_id": aid, "seller_id": s["seller_id"], "item_id": aid,
                               "category": c["name"], "start_at": start, "default_end_at": end,
                               "starting_price": start_price})

    # --- buyers ---------------------------------------------------------------
    styles = ["early", "incremental", "sniper"]
    style_share = np.array([p["style_share_early"], p["style_share_incremental"], p["style_share_sniper"]])
    style_share /= style_share.sum()
    rp_m, rp_k = p["rebid_propensity_mean"], p["rebid_propensity_concentration"]
    hp = w.buyer_hour_profile
    cap_hour = hp.max()
    wk = p["weekend_activity_factor"]
    thick_max = p["thickness_multiplier_max"]
    for b in range(sc["n_buyers"]):
        main = rng.choice(len(cats), p=demand_share)
        interest = np.zeros(len(cats))
        interest[main] = 1.0
        for j in range(len(cats)):
            if j != main and rng.random() < p["buyer_secondary_category_prob"]:
                interest[j] = rng.uniform(0.2, 0.6)
        fav = []
        for j in np.nonzero(interest)[0]:
            names, pop = series[cats[j]["name"]]
            kf = min(len(names), int(p["buyer_n_favorite_series"]))
            fav += list(rng.choice(names, size=kf, replace=False, p=pop))
        rate = (p["visit_rate_median_per_day"] * p["visit_rate_scale"]
                * np.exp(p["visit_rate_logsd"] * rng.standard_normal()))
        price_level = float(np.exp(p["buyer_price_level_logsd"] * rng.standard_normal()))
        med_main = p[f"price_median_krw_{cats[main]['name']}"]
        budget = float(round(price_level * med_main * np.exp(np.log(p["budget_items_median"])
                                                              + p["budget_logsd"] * rng.standard_normal()), -3))
        # active window: some buyers join later, all leave at daily hazard (1 - retention)
        join = 0.0 if rng.random() < p["buyer_initial_active_share"] else float(rng.uniform(0, horizon))
        stay_days = rng.geometric(1 - p["buyer_daily_retention"])
        leave = min(horizon, join + stay_days * 1440.0)
        cap = rate / 1440.0 * cap_hour * max(1.0, wk) * thick_max  # per minute
        n_cand = rng.poisson(cap * (leave - join))
        cand_t = np.sort(rng.uniform(join, leave, n_cand))
        cand_u = rng.random(n_cand)
        follows = [cats[j]["name"] for j in np.nonzero(interest)[0] if rng.random() < p["alert_follow_prob"]]
        w.buyers.append({
            "buyer_id": b + 1, "main_category": cats[main]["name"],
            "interest": {cats[j]["name"]: float(interest[j]) for j in range(len(cats)) if interest[j] > 0},
            "favorite_series": [str(x) for x in fav], "visit_rate_per_day": float(rate),
            "hour_offset": float(np.clip(p["buyer_hour_offset_sd"] * rng.standard_normal(), -6, 6)),
            "style": styles[rng.choice(3, p=style_share)],
            "rebid_propensity": float(rng.beta(rp_m * rp_k, (1 - rp_m) * rp_k)),
            "price_level": price_level, "budget": max(budget, 5000.0),
            "join_at": join, "leave_at": leave, "alert_follows": follows,
            "cap_rate_per_min": cap, "cand_t": cand_t, "cand_u": cand_u,
        })
    return w


def _default_end(w, start, dur, pref_hour, rng):
    """Seller's habitual end time: the preferred clock hour closest to start + dur,
    kept inside the 24-72 h window. Minutes jittered within the hour."""
    lo, hi = start + 24 * 60, start + 72 * 60
    target = start + dur
    cands = []
    t0 = lo - ((w.origin.hour * 60 + w.origin.minute + lo) % 1440)  # midnight before lo
    for day in range(5):
        t = t0 + day * 1440 + pref_hour * 60 + float(rng.uniform(0, 59))
        if lo <= t <= hi:
            cands.append(t)
    if not cands:
        return float(min(max(target, lo), hi))
    return float(round(min(cands, key=lambda t: abs(t - target))))
