"""Independent equivalence instruments; none are used by the production observer."""
import hashlib
import json
from contextlib import ExitStack
from time import perf_counter
from unittest.mock import patch

import numpy as np
import keyrng
import market_simulator


def update(h, value):
    if isinstance(value, np.ndarray):
        h.update(b'array'+value.dtype.str.encode()+str(value.shape).encode()+value.tobytes())
    elif isinstance(value, np.generic):
        update(h, value.item())
    elif isinstance(value, dict):
        h.update(b'dict[')
        for k, v in value.items():
            update(h, k)
            update(h, v)
        h.update(b']')
    elif isinstance(value, (list, tuple)):
        h.update(type(value).__name__.encode()+b'[')
        for x in value:
            update(h, x)
        h.update(b']')
    elif isinstance(value, (set, frozenset)):
        update(h, ('set', sorted(value)))
    elif isinstance(value, float):
        h.update(b'float'+value.hex().encode()+b';')
    else:
        h.update(type(value).__name__.encode()+repr(value).encode()+b';')


def digest(value):
    h = hashlib.sha256()
    update(h, value)
    return h.hexdigest()


def engine_state(market):
    # Compare EVERY parent-engine attribute, including full queue/log identifiers,
    # cache insertion order, budgets, watch/snipes, rejected events, and counters.
    return {k: digest(v) for k, v in market.__dict__.items() if k not in ('observer', 'w')}


def instrumented_run(market):
    rng, queue = hashlib.sha256(), hashlib.sha256()
    counts = dict(u=0, normal=0, push=0, pop=0)
    original_u, original_normal = keyrng.u, keyrng.normal
    original_push, original_pop = market_simulator.heapq.heappush, market_simulator.heapq.heappop

    def u(*args, **kwargs):
        value = original_u(*args, **kwargs)
        counts['u'] += 1
        update(rng, ('u', args, kwargs, value))
        return value

    def normal(*args, **kwargs):
        value = original_normal(*args, **kwargs)
        counts['normal'] += 1
        update(rng, ('normal', args, kwargs, value))
        return value

    def push(heap, event):
        counts['push'] += 1
        update(queue, ('push', event))
        return original_push(heap, event)

    def pop(heap):
        event = original_pop(heap)
        counts['pop'] += 1
        update(queue, ('pop', event))
        return event

    with ExitStack() as stack:
        stack.enter_context(patch.object(keyrng, 'u', u))
        stack.enter_context(patch.object(keyrng, 'normal', normal))
        stack.enter_context(patch.object(market_simulator.heapq, 'heappush', push))
        stack.enter_context(patch.object(market_simulator.heapq, 'heappop', pop))
        start = perf_counter()
        market.run()
        elapsed = perf_counter()-start
    return {'rng_sha256': rng.hexdigest(), 'queue_sha256': queue.hexdigest(),
            'counts': counts, 'state': engine_state(market), 'instrumented_seconds': elapsed}


def assert_equivalent(left, right):
    for key in ('rng_sha256', 'queue_sha256', 'counts', 'state'):
        if left[key] != right[key]:
            raise AssertionError('Behavioral difference: '+key)


def diagnostic_invariants(market):
    if market.observer is None:
        return {'all_pass': True, 'enabled': False}
    o = market.observer
    contexts = o.records['market_context']
    for r in contexts:
        for clock in ('live','scheduled'):
            previous = 0.
            previous_proxy = 0
            for h in (1, 3, 6, 12, 24):
                v = r[f'T_{clock}_{h}h_weighted']
                assert previous-1e-10 <= v <= r['M_similarity_weighted']+1e-10
                previous = v
                proxy = r[f'T_{clock}_{h}h_catalog_proxy_count']
                if proxy is not None and r['M_catalog_proxy_count'] is not None:
                    assert previous_proxy <= proxy <= r['M_catalog_proxy_count']
                    previous_proxy = proxy
    organic = [e for e in market.events if e['event_type']=='visit' and e['cause']=='organic']
    accepted = [r for r in o.records['participation'] if r['stage']=='visit_candidate' and r['accepted']]
    assert len(organic)==len(accepted)
    for e,r in zip(organic,accepted):
        assert (e['event_time'],e['buyer_id'],e['thickness_signal']) == (r['time_min'],r['buyer_id'],round(r['N_near_end_count'],3))
    views = [e for e in market.events if e['event_type']=='view']
    aware = o.records['awareness_events']
    assert len(views)==len(aware)==len(o.records['decision_context'])
    known = {}
    for e, r in zip(views, aware):
        assert (e['buyer_id'],e['auction_id'],e['event_time'],e['visit_id']) == (
            r['buyer_id'],r['auction_id'],r['time_min'],r['visit_id'])
        seen = known.setdefault(r['buyer_id'], set())
        assert r['known_before_current_view'] == (r['auction_id'] in seen)
        assert r['known_count_before']==len(seen)
        seen.add(r['auction_id'])
        assert r['known_count_after']==len(seen)
    for r in o.records['purchase_state']:
        assert abs(r['uncommitted_budget']-(r['budget']-r['spent']-r['committed']))<1e-8
    assert all(r['cached_wtp_after'] is None or r['cached_wtp_after']==market.wtp_log[(r['buyer_id'],r['auction_id'])]
               for r in o.records['decision_context'])
    return {'enabled': True, 'all_pass': True, 'actual_views':len(views),
            'market_contexts':len(contexts),'awareness_rows':len(aware),
            'purchase_state_rows':len(o.records['purchase_state'])}
