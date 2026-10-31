"""Frozen parent consider body with only its substitute-skip block replaced.
Validated by an AST comparison test against the preserved parent source.
"""
import math
from market_simulator import K, increment, SNIPE


def consider_experimental(self, t, b, a, mode, visit):
    """One buyer looks at one open auction."""
    bid = b["buyer_id"]
    aid = a["auction_id"]
    self.log(t, bid, "view", aid, mode, visit)
    if a["leader"] == bid:
        self.decide(t, bid, aid, "already_leading", visit)
        return
    st = self.state[bid]
    if not self._choose_focal(t, b, a, visit):
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
