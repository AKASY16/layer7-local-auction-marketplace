"""Full 18-dataset baseline replay and opt-in fixes; never writes frozen data."""
import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C, MS, activity_violations, digest_world, signature, json_safe
from baseline_audit import protection
sys.path.insert(0, str(ROOT / 'validation'))
import validate as V
import generate as G
from audit import export as E
from audit.simulator import Market


class ActiveOnly(Market):
    thickness = MS.Market.thickness


class ThicknessOnly(Market):
    push = MS.Market.push


def hashes(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*.csv'))}


def compact_moments(tables):
    m = V.moments(tables)
    return {k: v for k, v in m.items() if k not in ('u_values_sample', 'visit_hour_share')}


def one(job):
    scenario, seed, destination = job
    dest = Path(destination) / f'scenario_{scenario}/seed_{seed}'
    scen = ROOT / f'config/scenarios/scenario_{scenario}.yaml'
    base_dest = dest / 'baseline-v4'
    if dest.exists():
        raise FileExistsError(dest)
    base_dest.mkdir(parents=True)
    w, before, _ = G.run(scen, seed, base_dest)
    h0 = digest_world(w)
    cfg = w.cfg
    ends = {a['auction_id']: a['default_end_at'] for a in w.auctions}
    fixed = Market(w, ends, seed).run()
    tables = E.to_tables(w, fixed, cfg, 'seller_default')
    fixed_dest = dest / 'audit-fix-v1'
    E.write_tables(tables, fixed_dest, cfg, seed, scen, 'seller_default')
    replay = Market(w, ends, seed).run()
    replica = dest / 'audit-fix-v1-replay'
    E.write_tables(E.to_tables(w, replay, cfg, 'seller_default'), replica, cfg, seed, scen, 'seller_default')
    bt, ft = V.load(base_dest), V.load(fixed_dest)
    bm, fm = compact_moments(bt), compact_moments(ft)
    metric_delta = {k: fm[k]-bm[k] for k in bm if isinstance(bm[k], (int, float))}
    active_only = ActiveOnly(w, ends, seed).run()
    thickness_only = ThicknessOnly(w, ends, seed).run()
    result = {
        'baseline_reproduces_original_11_csv': hashes(base_dest) == hashes(ROOT / f'data/synthetic/scenario_{scenario}/seed_{seed}'),
        'baseline_structure': V.structural(bt, cfg), 'corrected_structure': V.structural(ft, cfg),
        'corrected_reproducible_11_csv': hashes(fixed_dest) == hashes(replica),
        'corrected_full_bids_identical': fixed.bids == replay.bids,
        'world_not_mutated': h0 == digest_world(w),
        'baseline_activity_bad_bids_exact': len(activity_violations(before)),
        'corrected_activity_bad_bids_exact': len(activity_violations(fixed)),
        'corrected_activity_bad_events_exact': sum(not fixed.buyers[e['buyer_id']]['join_at'] <= e['event_time'] <
                                                  fixed.buyers[e['buyer_id']]['leave_at'] for e in fixed.events),
        'n_rejected_inactive_events': len(fixed.rejected_inactive_events),
        'baseline_moments': bm, 'corrected_moments': fm, 'moment_delta': metric_delta,
        'baseline_bid_count': len(before.bids), 'corrected_bid_count': len(fixed.bids),
        'active_only_bid_count': len(active_only.bids), 'thickness_only_bid_count': len(thickness_only.bids),
        'active_only_bad_bids': len(activity_violations(active_only)),
        'thickness_only_bad_bids': len(activity_violations(thickness_only)),
        'changed_auction_outcomes': sum(signature(before, [i])['outcomes'] != signature(fixed, [i])['outcomes'] for i in ends),
    }
    return f'scenario_{scenario}/seed_{seed}', result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    allowed = (ROOT / 'data/experiments').resolve()
    dest = args.out.resolve()
    if dest == allowed or not dest.is_relative_to(allowed) or dest.exists():
        raise ValueError('Use a NEW directory below data/experiments/')
    jobs = [(s, seed, str(dest)) for s in 'ABCDEF' for seed in (1, 2, 3)]
    result = {}
    with ProcessPoolExecutor(args.workers) as pool:
        for future in as_completed([pool.submit(one, job) for job in jobs]):
            key, value = future.result()
            result[key] = value
            print(key, 'baseline_repro', value['baseline_reproduces_original_11_csv'],
                  'fixed_structure', value['corrected_structure']['all_pass'],
                  'fixed_active_bad', value['corrected_activity_bad_bids_exact'], flush=True)
    checks = ['baseline_reproduces_original_11_csv', 'corrected_reproducible_11_csv',
              'corrected_full_bids_identical', 'world_not_mutated']
    ok = protection()['ok'] and len(result) == 18 and all(all(v[k] for k in checks) and
        v['baseline_structure']['all_pass'] and v['corrected_structure']['all_pass'] and
        v['corrected_activity_bad_bids_exact'] == 0 and v['corrected_activity_bad_events_exact'] == 0
        for v in result.values())
    output = {'protection': protection(), 'n_datasets': len(result), 'all_pass': ok, 'datasets': dict(sorted(result.items()))}
    (ROOT / 'validation/audit/regression_results.json').write_text(json.dumps(json_safe(output), indent=2, allow_nan=False), encoding='utf-8')
    print('REGRESSION ALL PASS:', ok, flush=True)
    if not ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
