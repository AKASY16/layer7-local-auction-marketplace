"""Discrete-event auction market on top of an exogenous World.

`simulate(world, end_times, seed)` runs one policy: end_times maps auction_id to
scheduled end (minutes). Everything that depends on end times (which visits are
accepted, which auctions a buyer sees, bids, outcomes) is recomputed here.

Behaviour per buyer visit (all choices keyed by ids, see keyrng):
 1. Visit candidates come from the World stream; a candidate is kept with
    probability rate * hour weight * weekday factor * thickness / cap, where
    thickness = number of open auctions in the buyer's categories that end in the
    next W hours (demand-side participation effect, Bimpikis et al. 2020).
 2. The buyer looks at up to K open auctions, sampled by interest x favourite
    series x "ending soon" boost. Auctions that end together compete for these
    slots (attention dilution).
 3. For each viewed auction: skip if already leading or won a substitute
    (probability = similarity), skip if WTP or budget is below the minimum
    acceptable bid, otherwise act by style:
      early       -> proxy bid at min(WTP, budget headroom)
      incremental -> bid a small step above the minimum, re-bid when outbid
      sniper      -> schedule one bid in the last seconds (Roth & Ockenfels 2002)
 4. Outbid buyers may return (rebid propensity, delay from Jank & Shmueli gaps).
    Every planned return (outbid notice, watch return, snipe, alert) happens only
    if the buyer is around at that hour: probability = own hourly activity weight
    / profile peak. This is what ties an auction's end hour to its late demand.
    A re-bid within session_window_min of being outbid skips this check: the
    bidder is still on the site.
 5. Hard close: no bid after the scheduled end. Optional soft close extends the
    end when a bid lands inside the threshold (used only for sensitivity runs).
Price formation is eBay-style proxy bidding: the leader pays one increment
above the second-highest maximum, capped at the leader's maximum.
"""
import heapq
import math
from bisect import bisect_right
from collections import defaultdict

import numpy as np

import keyrng as K

VISIT, ALERT, RETURN, SNIPE, CLOSE, LIST = range(6)
CAUSE = {VISIT: "organic", ALERT: "listing_alert", RETURN: "return", SNIPE: "snipe"}


def increment(price, table):
    for upper, inc in table:
        if upper is None or price < upper:
            return inc
    return table[-1][1]


class Market:
    def __init__(self, world, end_times, seed, close_rule="hard"):
        self.w = world
        self.cfg = world.cfg
        self.p = world.cfg["params"]
        self.seed = seed
        self.close_rule = close_rule
        self.inc_table = [(None if u is None else float(u), float(i)) for u, i in self.cfg["increment_table_krw"]]
        self.items = {it["item_id"]: it for it in world.items}
        self.auc = {}
        for a in world.auctions:
            end = float(end_times[a["auction_id"]])
            self.auc[a["auction_id"]] = {
                **a, "scheduled_end_at": end, "end": end, "price": None, "leader": None, "leader_max": 0.0,
                "n_bids": 0, "bidders": set(), "closed": False, "close_version": 0}
        self.buyers = {b["buyer_id"]: b for b in world.buyers}
        self.state = {bid: {"spent": 0.0, "committed": 0.0, "leading": set(), "won": [],
                            "snipes": set(), "returns": 0} for bid in self.buyers}
        self.heap = []
        self.seq = 0
        self.bids, self.events, self.decisions, self.wtp_log = [], [], [], {}
        self.visit_counter = 0
        self.watching = set()
        self.avail_norm = float(np.max(world.buyer_hour_profile))
        # per category sorted scheduled end times (for the thickness signal)
        self.cat_ends = defaultdict(list)
        for a in self.auc.values():
            self.cat_ends[a["category"]].append(a["end"])
        for c in self.cat_ends:
            self.cat_ends[c].sort()
        self.cat_open = defaultdict(set)
        sim = self.cfg["similarity"]
        self.sim_series, self.sim_sub, self.sim_cat = sim["same_series"], sim["same_subcategory"], sim["same_category"]

    # --- helpers --------------------------------------------------------------
    def push(self, t, kind, payload):
        self.seq += 1
        heapq.heappush(self.heap, (t, self.seq, kind, payload))

    def similarity(self, i, j):
        a, b = self.items[i], self.items[j]
        if a["category"] != b["category"]:
            return 0.0
        if a["series"] == b["series"]:
            return self.sim_series
        if a["subcategory"] == b["subcategory"]:
            return self.sim_sub
        return self.sim_cat

    def wtp(self, b, a):
        key = (b["buyer_id"], a["auction_id"])
        v = self.wtp_log.get(key)
        if v is None:
            it = self.items[a["item_id"]]
            fav = self.p["favorite_series_wtp_multiplier"] if it["series"] in b["favorite_series"] else 1.0
            interest = b["interest"].get(it["category"], 0.0)
            z = K.normal(self.seed, "wtp", b["buyer_id"], a["item_id"])
            # popular items (high appeal) are also valued higher: demand-driven price dispersion
            pop = it["appeal"] ** self.p["appeal_wtp_elasticity"]
            v = (it["estimated_value"] * pop * b["price_level"] * fav * (0.75 + 0.25 * interest)
                 * math.exp(self.p["wtp_idio_logsd"] * z - 0.5 * self.p["wtp_idio_logsd"] ** 2))
            v = float(round(v, -2))
            self.wtp_log[key] = v
        return v

    def hour_weight(self, b, t):
        h = (self.w.hour_of(t) - int(round(b["hour_offset"]))) % 24
        f = self.p["weekend_activity_factor"] if self.w.dow_of(t) >= 5 else 1.0
        return self.w.buyer_hour_profile[h] * f

    def thickness(self, b, t):
        win = self.p["thickness_window_hours"] * 60
        n = 0.0
        for c, wgt in b["interest"].items():
            ends = self.cat_ends[c]
            n += wgt * (bisect_right(ends, t + win) - bisect_right(ends, t))
        ref, th = self.p["thickness_reference_count"], self.p["thickness_elasticity"]
        m = ((n + 1.0) / (ref + 1.0)) ** th
        return min(max(m, self.p["thickness_multiplier_min"]), self.p["thickness_multiplier_max"]), n

    def log(self, t, b, kind, auction=None, cause=None, visit=None, extra=None):
        self.events.append({"event_time": t, "buyer_id": b, "auction_id": auction, "event_type": kind,
                            "cause": cause, "visit_id": visit, **(extra or {})})

    def decide(self, t, b, a, reason, visit):
        self.decisions.append({"time": t, "buyer_id": b, "auction_id": a, "decision": reason, "visit_id": visit})

    # --- bidding ----------------------------------------------------------------
    def min_acceptable(self, a):
        if a["price"] is None:
            return a["starting_price"]
        return a["price"] + increment(a["price"], self.inc_table)

    def headroom(self, b, a):
        st = self.state[b["buyer_id"]]
        own = a["leader_max"] if a["leader"] == b["buyer_id"] else 0.0
        return b["budget"] - st["spent"] - (st["committed"] - own)

    def place_bid(self, t, b, a, max_amount, bid_type, visit):
        bid = b["buyer_id"]
        st = self.state[bid]
        prev_leader, prev_max = a["leader"], a["leader_max"]
        if a["price"] is None:
            a["price"], a["leader"], a["leader_max"] = a["starting_price"], bid, max_amount
        elif max_amount > a["leader_max"]:
            a["price"] = min(max_amount, a["leader_max"] + increment(a["leader_max"], self.inc_table))
            a["leader"], a["leader_max"] = bid, max_amount
        else:
            a["price"] = min(a["leader_max"], max_amount + increment(max_amount, self.inc_table))
        a["n_bids"] += 1
        a["bidders"].add(bid)
        self.bids.append({"auction_id": a["auction_id"], "buyer_id": bid, "bid_time": t, "bid_amount": max_amount,
                          "bid_type": bid_type, "price_after": a["price"], "leader_after": a["leader"],
                          "visit_id": visit})
        self.log(t, bid, "bid", a["auction_id"], bid_type, visit)
        if a["leader"] == bid:
            if prev_leader == bid:
                st["committed"] += max_amount - prev_max
            else:
                st["committed"] += max_amount
                st["leading"].add(a["auction_id"])
                if prev_leader is not None:
                    self.outbid(t, prev_leader, a, prev_max)
        else:
            self.outbid(t, bid, a, None)  # immediately beaten by the standing proxy
        if self.close_rule == "soft":
            thr = self.cfg["soft_close"]["threshold_min"]
            if a["end"] - t <= thr:
                a["end"] = t + self.cfg["soft_close"]["extend_min"]
                a["close_version"] += 1
                self.push(a["end"], CLOSE, (a["auction_id"], a["close_version"]))

    def outbid(self, t, buyer_id, a, old_max):
        st = self.state[buyer_id]
        if old_max is not None:
            st["committed"] -= old_max
            st["leading"].discard(a["auction_id"])
        b = self.buyers[buyer_id]
        if b["style"] == "sniper":
            return
        n = self.state[buyer_id]["returns"]
        if K.u(self.seed, "rebid", buyer_id, a["auction_id"], a["n_bids"]) < b["rebid_propensity"]:
            if K.u(self.seed, "rebid_delay_mix", buyer_id, a["auction_id"], a["n_bids"]) < self.p["rebid_fast_share"]:
                med, sd = self.p["rebid_fast_median_min"], self.p["rebid_fast_logsd"]
            else:
                med, sd = self.p["rebid_slow_median_min"], self.p["rebid_slow_logsd"]
            d = med * math.exp(sd * K.normal(self.seed, "rebid_delay", buyer_id, a["auction_id"], a["n_bids"]))
            if t + d < a["end"] and t + d < b["leave_at"]:
                self.state[buyer_id]["returns"] = n + 1
                self.push(t + d, RETURN, (buyer_id, a["auction_id"], "outbid_notice", t))

    def consider(self, t, b, a, mode, visit):
        """One buyer looks at one open auction."""
        bid = b["buyer_id"]
        aid = a["auction_id"]
        self.log(t, bid, "view", aid, mode, visit)
        if a["leader"] == bid:
            self.decide(t, bid, aid, "already_leading", visit)
            return
        st = self.state[bid]
        best_sim = 0.0
        for other in list(st["leading"]) + st["won"]:
            if other != aid:
                best_sim = max(best_sim, self.similarity(self.auc[other]["item_id"], a["item_id"]))
        if best_sim > 0 and K.u(self.seed, "substitute_skip", bid, aid, len(st["won"]), len(st["leading"])) < best_sim:
            self.decide(t, bid, aid, "has_substitute", visit)
            return
        v = self.wtp(b, a)
        need = self.min_acceptable(a)
        room = self.headroom(b, a)
        if v < need:
            self.decide(t, bid, aid, "price_above_wtp", visit)
            return
        if room < need:
            self.decide(t, bid, aid, "budget", visit)
            return
        cap = min(v, room)
        style = b["style"]
        if mode == "snipe":
            if K.u(self.seed, "snipe_transmit", bid, aid) < self.p["snipe_transmit_fail_prob"]:
                self.log(t, bid, "snipe_failed", aid, "transmission", visit)
                self.decide(t, bid, aid, "snipe_failed", visit)
                return
            self.place_bid(t, b, a, cap, "snipe", visit)
            return
        if style == "sniper":
            if aid not in st["snipes"]:
                st["snipes"].add(aid)
                if K.u(self.seed, "snipe_unavailable", bid, aid) < self.p["snipe_unavailable_prob"]:
                    self.decide(t, bid, aid, "snipe_planned_unavailable", visit)
                else:
                    off = K.u(self.seed, "snipe_offset", bid, aid) * self.p["snipe_offset_max_sec"] / 60.0
                    ts = a["scheduled_end_at"] - off
                    if ts > t:
                        self.push(ts, SNIPE, (bid, aid))
                        self.decide(t, bid, aid, "snipe_scheduled", visit)
                    else:
                        self.place_bid(t, b, a, cap, "manual", visit)
            return
        # non-snipers far from the end often only watch and come back later
        # (bid intensity rises toward the end: BARISTA alpha2 < 1, Roth & Ockenfels)
        if a["end"] - t > self.p["act_now_window_min"] and mode in ("organic", "listing_alert"):
            if K.u(self.seed, "defer", bid, aid, int(t * 60)) > self.p["early_act_prob"]:
                self.decide(t, bid, aid, "deferred", visit)
                self.schedule_watch(t, b, a)
                return
        if style == "early":
            self.place_bid(t, b, a, cap, "proxy", visit)
        else:  # incremental: a few increments above the minimum
            steps = 1 + int(-math.log(1 - K.u(self.seed, "jump", bid, aid, a["n_bids"])) * self.p["incremental_mean_extra_steps"])
            amt = need + (steps - 1) * increment(need, self.inc_table)
            self.place_bid(t, b, a, min(cap, amt), "incremental", visit)
        self.schedule_watch(t, b, a)

    def schedule_watch(self, t, b, a):
        """Some viewers come back to look again shortly before the end."""
        bid, aid = b["buyer_id"], a["auction_id"]
        if (bid, aid) in self.watching or a["end"] - t <= 30:
            return
        if K.u(self.seed, "watch", bid, aid) < self.p["watch_return_prob"]:
            self.watching.add((bid, aid))
            d = -math.log(1 - K.u(self.seed, "watch_delay", bid, aid)) * self.p["watch_return_mean_min_before_end"]
            tr = a["scheduled_end_at"] - d
            if t < tr < b["leave_at"]:
                self.push(tr, RETURN, (bid, aid, "watch_return"))

    # --- visits -----------------------------------------------------------------
    def visit(self, t, b, cand_index):
        bid = b["buyer_id"]
        thick, n_rel = self.thickness(b, t)
        rate = b["visit_rate_per_day"] / 1440.0 * self.hour_weight(b, t) * thick
        if b["cand_u"][cand_index] * b["cap_rate_per_min"] > rate:
            return
        self.visit_counter += 1
        vid = self.visit_counter
        self.log(t, bid, "visit", None, "organic", vid, {"thickness_signal": round(n_rel, 3)})
        opens = []
        for c, wgt in b["interest"].items():
            for aid in self.cat_open[c]:
                a = self.auc[aid]
                it = self.items[a["item_id"]]
                tte_h = (a["end"] - t) / 60.0
                fav = self.p["favorite_series_view_weight"] if it["series"] in b["favorite_series"] else 1.0
                s = wgt * fav * it["appeal"] * (1.0 + self.p["ending_soon_boost"] * math.exp(-tte_h / self.p["ending_soon_tau_hours"]))
                opens.append((s, aid))
        if not opens:
            return
        # views per visit; with attention_thickness_elasticity > 0 a buyer looks at more
        # auctions when more relevant ones end soon (one-stop shopping on thick days)
        att = ((n_rel + 1.0) / (self.p["thickness_reference_count"] + 1.0)) ** self.p["attention_thickness_elasticity"]
        att = min(max(att, 0.5), 4.0)
        k = 1 + int(-math.log(1 - K.u(self.seed, "visit_k", bid, cand_index)) * (self.p["attention_mean_views"] - 1) * att)
        keyed = sorted(((K.u(self.seed, "view_key", bid, cand_index, aid) ** (1.0 / s), aid) for s, aid in opens),
                       reverse=True)
        for _, aid in keyed[:k]:
            a = self.auc[aid]
            if not a["closed"]:
                self.consider(t, b, a, "organic", vid)

    # --- main loop --------------------------------------------------------------
    def run(self):
        for a in self.auc.values():
            self.push(a["start_at"], LIST, a["auction_id"])
            self.push(a["end"], CLOSE, (a["auction_id"], 0))
        for b in self.buyers.values():
            if len(b["cand_t"]):
                self.push(float(b["cand_t"][0]), VISIT, (b["buyer_id"], 0))
        while self.heap:
            t, _, kind, pay = heapq.heappop(self.heap)
            if kind == LIST:
                a = self.auc[pay]
                self.cat_open[a["category"]].add(pay)
                self.schedule_alerts(t, a)
            elif kind == CLOSE:
                aid, ver = pay
                a = self.auc[aid]
                if ver == a["close_version"] and not a["closed"]:
                    self.close(t, a)
            elif kind == VISIT:
                bid, i = pay
                b = self.buyers[bid]
                self.visit(t, b, i)
                if i + 1 < len(b["cand_t"]):
                    self.push(float(b["cand_t"][i + 1]), VISIT, (bid, i + 1))
            elif kind in (RETURN, ALERT, SNIPE):
                bid, aid = pay[0], pay[1]
                a = self.auc[aid]
                if a["closed"] or t > a["end"] or t < a["start_at"]:
                    continue
                b = self.buyers[bid]
                cause = pay[2] if kind == RETURN else CAUSE[kind]
                # a planned return only happens if the buyer is around at that hour:
                # availability = own activity weight relative to the profile peak
                avail = min(1.0, self.hour_weight(b, t) / self.avail_norm)
                in_session = kind == RETURN and len(pay) > 3 and t - pay[3] <= self.p["session_window_min"]
                if not in_session and K.u(self.seed, "available", bid, aid, int(t * 60)) > avail:
                    self.decide(t, bid, aid, f"unavailable_{cause}", None)
                    continue
                self.visit_counter += 1
                vid = self.visit_counter
                self.log(t, bid, "visit", aid, cause, vid)
                self.consider(t, b, a, "snipe" if kind == SNIPE else cause, vid)
        return self

    def schedule_alerts(self, t, a):
        for b in self.buyers.values():
            if a["category"] not in b["alert_follows"] or not (b["join_at"] <= t < b["leave_at"]):
                continue
            if K.u(self.seed, "alert", b["buyer_id"], a["auction_id"]) < self.p["alert_open_prob"]:
                d = -math.log(1 - K.u(self.seed, "alert_delay", b["buyer_id"], a["auction_id"])) * self.p["alert_delay_mean_min"]
                if t + d < min(a["end"], b["leave_at"]):
                    self.push(t + d, ALERT, (b["buyer_id"], a["auction_id"]))

    def close(self, t, a):
        a["closed"] = True
        a["actual_end_at"] = t
        self.cat_open[a["category"]].discard(a["auction_id"])
        if a["leader"] is not None:
            st = self.state[a["leader"]]
            st["committed"] -= a["leader_max"]
            st["leading"].discard(a["auction_id"])
            st["spent"] += a["price"]
            st["won"].append(a["auction_id"])


def simulate(world, end_times, seed, close_rule="hard"):
    return Market(world, end_times, seed, close_rule).run()
