"""Reproducers BEFORE fixes, and the same controls AFTER fixes. No tuning."""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C, MS, W, activity_violations, digest_world, fixture, market_class, signature, simulate
import keyrng as K


def controls(engine):
    cls = market_class(engine)
    out = {}
    # A discovered sniper leaves the market before the planned bid.
    w = fixture(style='sniper')
    w.items, w.auctions = w.items[:1], w.auctions[:1]
    w.buyers[0].update(leave_at=1000., cand_t=np.array([900.]), cand_u=np.array([0.]))
    m = simulate(engine, w, {1: 1500.}, 11)
    out['expired_sniper'] = {'violations': activity_violations(m), 'n_bids': len(m.bids),
                              'expected_n_bids': 0}
    # Explicitly present one open and one unlisted auction in the same window.
    w = fixture()
    w.auctions[1].update(start_at=100., default_end_at=1600.)
    m = cls(w, {1: 1500., 2: 1600.}, 11)
    m.cat_open['tcg'].add(1)
    out['future_listing'] = {'observed_relevant_count': m.thickness(w.buyers[0], 50.)[1],
                             'expected_relevant_count': 1.0}
    # Equal discovery/exposure and ample budgets: separate substitution from time collision.
    factorial = []
    for sub in (0., 1.):
        for gap in (0., 180.):
            w = fixture(similarity=sub)
            m = cls(w, {1: 1500., 2: 1500. + gap}, 11)
            for aid in (1, 2):
                m.push(1490., MS.RETURN, (1, aid, 'watch_return'))
            m.run()
            factorial.append({'similarity': sub, 'end_gap_minutes': gap, 'n_bids': len(m.bids),
                               'n_sold': sum(a['leader'] is not None for a in m.auc.values()),
                               'skip_substitute': sum(d['decision'] == 'has_substitute' for d in m.decisions)})
    out['substitution_x_collision'] = factorial
    # Disconnected demand and budgets: changing component 1 must not change component 2.
    w = fixture(disconnected=True, style='sniper')
    for b in w.buyers:
        b.update(cand_t=np.array([500., 1400., 1600.]), cand_u=np.array([0., 0., 0.]))
    h0 = digest_world(w)
    a = simulate(engine, w, {1: 1500., 2: 1500.}, 22)
    b = simulate(engine, w, {1: 1700., 2: 1500.}, 22)
    out['disconnected_components'] = {'component_2_identical': signature(a, [2]) == signature(b, [2]),
                                       'world_not_mutated': h0 == digest_world(w)}
    # Coupling and repeated calls: compare complete bids, not just bid timestamps.
    cfg = C.load(ROOT / 'config/scenarios/scenario_F.yaml', overrides={'scale':
                  {'n_buyers': 40, 'n_auctions': 12, 'n_sellers': 4, 'days': 10}})
    w = W.build(cfg, 901)
    h0 = digest_world(w)
    ends = {a['auction_id']: a['default_end_at'] for a in w.auctions}
    a = simulate(engine, w, ends, 901)
    alt = {i: t-60 if t-w.auctions[i-1]['start_at'] >= 1500 else t+60 for i, t in ends.items()}
    simulate(engine, w, alt, 901)
    b = simulate(engine, w, ends, 901)
    out['coupling'] = {'full_bids_repeat_identical': a.bids == b.bids,
                        'outcomes_repeat_identical': signature(a) == signature(b),
                        'world_not_mutated': h0 == digest_world(w),
                        'rebuilt_world_identical': h0 == digest_world(W.build(cfg, 901)),
                        'shared_wtp_identical': all(v == b.wtp_log[k] for k, v in a.wtp_log.items())}
    keys = [(s, p, i, j) for s in (1, 11) for p in K.P for i in range(10) for j in range(5)]
    vals = {key: K.u(*key) for key in keys}
    for key in reversed(keys):
        assert vals[key] == K.u(*key)
    out['key_rng'] = {'tested_keys': len(keys), 'order_independent': True,
                       'sample_values_strictly_inside_0_1': all(0 < x < 1 for x in vals.values()),
                       'scope': 'Key stability check; not a proof of statistical independence.'}
    # An entirely quiet market should still export readable, empty CSV schemas.
    w = fixture()
    m = simulate(engine, w, {1: 1500., 2: 1500.}, 11)
    try:
        if engine == 'baseline-v4':
            import generate as G
            tables = G.to_tables(w, m, w.cfg, 'control')
        else:
            from audit.export import to_tables
            tables = to_tables(w, m, w.cfg, 'control')
        out['empty_market_export'] = {'ok': True, 'bid_columns': list(tables['bids'].columns),
                                       'event_columns': list(tables['visits'].columns)}
    except (KeyError, ValueError) as e:
        out['empty_market_export'] = {'ok': False, 'exception': repr(e)}
    out['correction_checks_pass'] = (not out['expired_sniper']['violations'] and
        out['future_listing']['observed_relevant_count'] == 1 and out['empty_market_export']['ok'])
    assert out['disconnected_components']['component_2_identical']
    assert all(out['coupling'][k] for k in out['coupling'])
    assert [r['n_bids'] for r in factorial] == [2, 2, 1, 1]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['baseline-v4', 'audit-fix-v1'], default='baseline-v4')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'validation/audit').resolve()):
        raise ValueError('Use a NEW report path inside validation/audit/')
    result = {'engine': args.engine, 'controls': controls(args.engine)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.engine != 'baseline-v4':
        assert result['controls']['correction_checks_pass']


if __name__ == '__main__':
    main()
