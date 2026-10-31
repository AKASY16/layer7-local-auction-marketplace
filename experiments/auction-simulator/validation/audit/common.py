"""Small, explicit controls; these fixtures are not a fitted market."""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import config as C
import market_simulator as MS
import world as W


def json_safe(value):
    """Undefined descriptive moments are missing, not zero and not JSON NaN."""
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def fixture(similarity=0.0, disconnected=False, style='early'):
    cfg = C.load(ROOT / 'config/scenarios/scenario_B.yaml')
    cfg = copy.deepcopy(cfg)
    cfg['similarity'] = dict.fromkeys(('same_series', 'same_subcategory', 'same_category'), similarity)
    cfg['params'].update(thickness_elasticity=0.0, attention_thickness_elasticity=0.0,
                         ending_soon_boost=0.0, alert_open_prob=0.0, watch_return_prob=0.0,
                         early_act_prob=1.0, wtp_idio_logsd=0.0, appeal_wtp_elasticity=0.0,
                         snipe_unavailable_prob=0.0, snipe_transmit_fail_prob=0.0,
                         weekend_activity_factor=1.0, thickness_window_hours=48.0)
    w = W.World(cfg, __import__('datetime').datetime.fromisoformat(cfg['start_date']), 4320., ['tcg', 'figure'])
    w.buyer_hour_profile = np.ones(24)
    w.seller_end_profile = np.ones(24) / 24
    for i in (1, 2):
        category = 'figure' if disconnected and i == 2 else 'tcg'
        w.items.append(dict(item_id=i, seller_id=i, category=category, subcategory='single', series='series',
                            condition='new', rarity='common', estimated_value=10000.,
                            similarity_group=category + '|series', appeal=1.0))
        w.auctions.append(dict(auction_id=i, seller_id=i, item_id=i, category=category,
                               start_at=0., default_end_at=1500., starting_price=1000.))
        w.sellers.append(dict(seller_id=i, primary_category=category, n_listings=1,
                              preferred_end_hour=1, listing_rate_per_day=1/3))
    for i in range(1, 3 if disconnected else 2):
        category = 'figure' if disconnected and i == 2 else 'tcg'
        w.buyers.append(dict(buyer_id=i, main_category=category, interest={category: 1.0},
                             favorite_series=[], visit_rate_per_day=10., hour_offset=0., style=style,
                             rebid_propensity=0., price_level=1., budget=1000000., join_at=0., leave_at=4320.,
                             alert_follows=[], cap_rate_per_min=1., cand_t=np.array([]), cand_u=np.array([])))
    return w


def market_class(engine):
    if engine == 'baseline-v4':
        return MS.Market
    from audit.simulator import Market
    return Market


def simulate(engine, w, ends, seed):
    return market_class(engine)(w, ends, seed).run()


def signature(m, aids=None):
    """Ignore global row/visit counters, which are output identifiers, not behaviour."""
    aids = set(m.auc) if aids is None else set(aids)
    bids = [{k: v for k, v in b.items() if k != 'visit_id'} for b in m.bids if b['auction_id'] in aids]
    outcomes = {i: (a['price'], a['leader'], a['leader_max'], a['n_bids'], sorted(a['bidders']))
                for i, a in sorted(m.auc.items()) if i in aids}
    return {'bids': bids, 'outcomes': outcomes}


def activity_violations(m):
    return [dict(buyer_id=b['buyer_id'], auction_id=b['auction_id'], time=b['bid_time'],
                 leave_at=m.buyers[b['buyer_id']]['leave_at'], bid_type=b['bid_type'])
            for b in m.bids if not (m.buyers[b['buyer_id']]['join_at'] <= b['bid_time'] <
                                    m.buyers[b['buyer_id']]['leave_at'])]


def digest_world(w):
    def default(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if hasattr(x, 'isoformat'):
            return x.isoformat()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    return hashlib.sha256(json.dumps(w.__dict__, sort_keys=True, default=default).encode()).hexdigest()
