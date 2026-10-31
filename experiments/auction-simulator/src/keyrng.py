"""Keyed random numbers for common random numbers across policies.

A draw is a pure function of (seed, purpose, ids...). The same buyer meeting the
same auction for the same purpose gets the same uniform no matter what else
changed, so two runs that differ only in end times differ only where the
behaviour actually diverges (Glasserman & Yao 1992 style coupling).
"""
from statistics import NormalDist

MASK = (1 << 64) - 1
_ND = NormalDist()

# purpose ids, fixed forever so files stay reproducible
P = {name: i + 1 for i, name in enumerate([
    "wtp", "visit_k", "view_key", "substitute_skip", "rebid", "rebid_delay_mix", "rebid_delay",
    "snipe_offset", "snipe_unavailable", "snipe_transmit", "watch", "watch_delay", "alert",
    "alert_delay", "jump", "watch_back_wtp", "defer", "available",
])}


def _mix(z):
    z = (z + 0x9E3779B97F4A7C15) & MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return z ^ (z >> 31)


def u(seed, purpose, *ids):
    """Uniform in (0, 1) from the keys."""
    h = _mix(seed & MASK)
    h = _mix(h ^ P[purpose])
    for k in ids:
        h = _mix(h ^ (k & MASK))
    return ((h >> 11) + 0.5) * (1.0 / (1 << 53))


def normal(seed, purpose, *ids):
    return _ND.inv_cdf(u(seed, purpose, *ids))
