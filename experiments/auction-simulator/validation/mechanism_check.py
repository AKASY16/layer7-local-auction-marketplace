"""Do the scenarios produce different effects of end-time concentration?

Same world (config, seed), three end-time assignments:
  concentrate:    every auction ends at 21:00 KST, the one closest to its seller default
  spread_evening: same day, end spread uniformly over 18:00-24:00 KST
  spread:         every auction ends at start + U(24, 72) h (any hour)
  batch_days:     21:00 KST but only on even day indexes where the window allows
batch_days - concentrate: day-level batching; concentrate - spread_evening: same-minute
concentration within the evening; spread_evening - spread: the hour of day.
Reports mean bidders, sell rate and price / estimated value per policy. This checks
that the thickness (scenario D) and substitution (scenario C) mechanisms can push in
opposite directions; it is not an evaluation of a recommendation policy.

  python validation/mechanism_check.py
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import config as C  # noqa: E402
import market_simulator as MS  # noqa: E402
import world as W  # noqa: E402


def concentrate(w, hour=21):
    ends = {}
    for a in w.auctions:
        lo, hi = a["start_at"] + 1440, a["start_at"] + 4320
        t0 = lo - ((w.origin.hour * 60 + w.origin.minute + lo) % 1440)
        cands = [t0 + d * 1440 + hour * 60 for d in range(5)]
        cands = [t for t in cands if lo <= t <= hi]
        ends[a["auction_id"]] = min(cands, key=lambda t: abs(t - a["default_end_at"]))
    return ends


def batch_days(w, hour=21):
    """21:00 KST on even day indexes where the 24-72 h window allows (day-level batching)."""
    ends = concentrate(w, hour)
    for a in w.auctions:
        lo, hi = a["start_at"] + 1440, a["start_at"] + 4320
        t0 = lo - ((w.origin.hour * 60 + w.origin.minute + lo) % 1440)
        cands = [t0 + d * 1440 + hour * 60 for d in range(5)]
        cands = [t for t in cands if lo <= t <= hi and int((t + w.origin.hour * 60) // 1440) % 2 == 0]
        if cands:
            ends[a["auction_id"]] = min(cands, key=lambda t: abs(t - a["default_end_at"]))
    return ends


def spread_evening(w):
    """Same day as concentrate, end minute uniform over 18:00-23:59 KST."""
    base = concentrate(w)
    out = {}
    for a in w.auctions:
        off = (zlib.crc32(str(a["auction_id"]).encode()) % 10000) / 10000 * 360 - 180  # -3h..+3h around 21:00
        e = base[a["auction_id"]] + off
        out[a["auction_id"]] = min(max(e, a["start_at"] + 1440), a["start_at"] + 4320)
    return out


def spread(w):
    return {a["auction_id"]: a["start_at"] + 1440 + (zlib.crc32(str(a["auction_id"]).encode()) % 10000) / 10000 * 2880
            for a in w.auctions}


def summary(m, w):
    val = {it["item_id"]: it["estimated_value"] for it in w.items}
    a = list(m.auc.values())
    sold = [x for x in a if x["leader"] is not None]
    return {"mean_bidders": float(np.mean([len(x["bidders"]) for x in a])),
            "sold": len(sold) / len(a),
            "price_over_value_mean_sold": float(np.mean([x["price"] / val[x["item_id"]] for x in sold])),
            "revenue_over_value_all": float(sum(x["price"] for x in sold) / sum(val[x["item_id"]] for x in a)),
            "visits": m.visit_counter}


def main():
    out = {}
    for s in ("A", "B", "C", "D", "E"):
        rows = []
        for seed in (1, 2, 3):
            cfg = C.load(ROOT / "config" / "scenarios" / f"scenario_{s}.yaml")
            w = W.build(cfg, seed)
            r = {"seed": seed}
            for name, fn in (("batch_days", batch_days), ("concentrate", concentrate), ("spread_evening", spread_evening),
                             ("spread", spread)):
                r[name] = summary(MS.simulate(w, fn(w), seed), w)
            rows.append(r)
            print(s, seed, {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in r.items() if k != "seed"}, flush=True)
        def contrast(x, y):
            d = {k: [r[x][k] - r[y][k] for r in rows] for k in rows[0][y]}
            return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1))} for k, v in d.items()}
        out[s] = {"runs": rows,
                  "day_batching_effect (batch_days - concentrate)": contrast("batch_days", "concentrate"),
                  "concentration_effect (concentrate - spread_evening)": contrast("concentrate", "spread_evening"),
                  "hour_effect (spread_evening - spread)": contrast("spread_evening", "spread")}
    (ROOT / "validation" / "mechanism_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for s, v in out.items():
        for c in ("day_batching_effect (batch_days - concentrate)", "concentration_effect (concentrate - spread_evening)",
                  "hour_effect (spread_evening - spread)"):
            print(s, c.split()[0], {k: f"{x['mean']:+.3f} ({x['sd']:.3f})" for k, x in v[c].items()})


if __name__ == "__main__":
    main()
