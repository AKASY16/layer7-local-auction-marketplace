"""Prespecified diagnostic probes, not an end-time recommender benchmark.

Independent units: seeds 1101..1112. Full original market scales. B/C/D original
activity and B flat/12h-shifted activity, retaining the SAME external world per
seed across activity variants. Compare two schedules with both engines. End
hour, duration and exposure can change together: report a schedule total effect.
"""
import argparse
import copy
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C, W, digest_world, signature, simulate
from uncertainty import exploratory_cluster_ols, paired_seed_summary
sys.path.insert(0, str(ROOT / 'validation'))
import mechanism_check as MC
import generate as G

SEEDS = tuple(range(1101, 1113))
ENGINES = ('baseline-v4', 'audit-fix-v1')
POLICIES = ('concentrate_21', 'evening_spread')
METRICS = ('revenue_krw_per_auction', 'mean_revenue_value_ratio', 'total_revenue_value_ratio', 'sold_rate', 'bidders_per_auction')


def auction_arrays(m, w):
    ids = sorted(m.auc)
    values = {i['item_id']: i['estimated_value'] for i in w.items}
    price = np.array([m.auc[i]['price'] if m.auc[i]['leader'] is not None else 0. for i in ids])
    v = np.array([values[m.auc[i]['item_id']] for i in ids])
    bidders = np.array([len(m.auc[i]['bidders']) for i in ids])
    return ids, price, v, bidders


def summary(m, w):
    ids, price, values, bidders = auction_arrays(m, w)
    return {'revenue_krw_per_auction': float(price.mean()), 'mean_revenue_value_ratio': float((price/values).mean()),
            'total_revenue_value_ratio': float(price.sum()/values.sum()),
            'sold_rate': float(np.mean([m.auc[i]['leader'] is not None for i in ids])),
            'bidders_per_auction': float(bidders.mean()),
            'mean_duration_hours': float(np.mean([(a['scheduled_end_at']-a['start_at'])/60 for a in m.auc.values()]))}


def policy_job(job):
    scenario, seed, variant = job
    cfg = C.load(ROOT / f'config/scenarios/scenario_{scenario}.yaml')
    w = W.build(cfg, seed)
    external_hash = digest_world(w)
    w = copy.deepcopy(w)
    if variant == 'flat':
        w.buyer_hour_profile = np.ones(24)
    elif variant == 'shift12h':
        w.buyer_hour_profile = np.roll(w.buyer_hour_profile, 12)
    elif variant != 'original':
        raise ValueError(variant)
    # A changed profile must remain dominated by the original thinning envelope.
    upper = w.buyer_hour_profile.max() * max(1., w.cfg['params']['weekend_activity_factor']) * w.cfg['params']['thickness_multiplier_max']
    if any(b['visit_rate_per_day']/1440 * upper > b['cap_rate_per_min'] + 1e-12 for b in w.buyers):
        raise ValueError('Activity variant exceeds the preserved candidate-stream envelope')
    h0 = digest_world(w)
    ends = {'concentrate_21': MC.concentrate(w, 21), 'evening_spread': MC.spread_evening(w)}
    for e in ends.values():
        G.check_end_times(w, e)
    rows = []
    for engine in ENGINES:
        for policy in POLICIES:
            market = simulate(engine, w, ends[policy], seed)
            rows.append({'scenario': scenario, 'seed': seed, 'activity_variant': variant, 'engine': engine,
                         'policy': policy, 'external_world_sha256': external_hash, **summary(market, w)})
    assert h0 == digest_world(w)
    return rows


def conflicts(w, ends):
    groups = {}
    for item in w.items:
        groups[item['item_id']] = item['similarity_group']
    return {a['auction_id']: sum(a['auction_id'] != b['auction_id'] and
            groups[a['item_id']] == groups[b['item_id']] and abs(ends[a['auction_id']]-ends[b['auction_id']]) <= 180
            for b in w.auctions) for a in w.auctions}


def shift_job(seed):
    cfg = C.load(ROOT / 'config/scenarios/scenario_C.yaml')
    w = W.build(cfg, seed)
    h0 = digest_world(w)
    original = {a['auction_id']: a['default_end_at'] for a in w.auctions}
    original_conflict = conflicts(w, original)
    alternatives = []
    ids = sorted(original)
    for perturbation in range(2):
        rng = np.random.default_rng([seed, 9000+perturbation])
        moved = set(rng.choice(ids, size=max(1, int(.1*len(ids))), replace=False).tolist())
        ends = dict(original)
        for a in w.auctions:
            if a['auction_id'] in moved:
                ends[a['auction_id']] = a['start_at'] + 1440 + rng.random()*2880
        alternatives.append((perturbation, moved, ends, conflicts(w, ends)))
    rows, spillovers = [], []
    for engine in ENGINES:
        base = simulate(engine, w, original, seed)
        _, p0, values, b0 = auction_arrays(base, w)
        for perturbation, moved, ends, cf in alternatives:
            current = simulate(engine, w, ends, seed)
            _, p1, _, b1 = auction_arrays(current, w)
            unmoved = np.array([i not in moved for i in ids])
            diff = (p1-p0)/values
            for k, aid in enumerate(ids):
                if aid in moved:
                    rows.append({'seed': seed, 'perturbation': perturbation, 'auction_id': aid, 'engine': engine,
                        'delta_revenue_value_ratio': float(diff[k]), 'delta_bidders': float(b1[k]-b0[k]),
                        'delta_hour_weight': float(w.buyer_hour_profile[w.hour_of(ends[aid])] - w.buyer_hour_profile[w.hour_of(original[aid])]),
                        'delta_conflicts': cf[aid]-original_conflict[aid],
                        'delta_duration_hours': (ends[aid]-original[aid])/60})
            spillovers.append({'seed': seed, 'perturbation': perturbation, 'engine': engine,
                'share_unmoved_changed_outcomes': float(np.mean([signature(base, [i])['outcomes'] != signature(current, [i])['outcomes']
                                                               for i in ids if i not in moved])),
                'mean_abs_delta_ratio_unmoved': float(np.abs(diff[unmoved]).mean()),
                'total_revenue_delta_krw_all': float((p1-p0).sum()),
                'total_revenue_delta_krw_moved': float((p1-p0)[~unmoved].sum()),
                'total_revenue_delta_krw_unmoved': float((p1-p0)[unmoved].sum())})
    assert digest_world(w) == h0
    return rows, spillovers


def summarize(policy_rows, shift_rows, spillovers):
    frame = pd.DataFrame(policy_rows)
    comparisons, fix_changes = {}, {}
    for (scenario, variant, engine), group in frame.groupby(['scenario', 'activity_variant', 'engine']):
        if group.duplicated(['seed', 'policy']).any():
            raise ValueError('Duplicate policy/seed rows')
        key = f'{scenario}/{variant}/{engine}'
        comparisons[key] = {}
        for metric in METRICS:
            matrix = group.pivot(index='seed', columns='policy', values=metric).sort_index()
            assert list(matrix.index) == list(SEEDS)
            comparisons[key][metric] = paired_seed_summary(matrix['concentrate_21']-matrix['evening_spread'], matrix.index.tolist())
    for scenario, variant in frame[['scenario', 'activity_variant']].drop_duplicates().itertuples(index=False, name=None):
        key = f'{scenario}/{variant}'
        fix_changes[key] = {}
        for metric in METRICS:
            def differences(engine):
                group = frame[(frame.scenario == scenario) & (frame.activity_variant == variant) & (frame.engine == engine)]
                matrix = group.pivot(index='seed', columns='policy', values=metric).sort_index()
                return (matrix['concentrate_21']-matrix['evening_spread']).to_numpy()
            fix_changes[key][metric] = paired_seed_summary(differences('audit-fix-v1')-differences('baseline-v4'), SEEDS)
    regressions, spill = {}, {}
    shift = pd.DataFrame(shift_rows)
    sp = pd.DataFrame(spillovers)
    for engine, group in shift.groupby('engine'):
        x = group[['delta_hour_weight', 'delta_conflicts', 'delta_duration_hours']].to_numpy()
        regressions[engine] = {target: exploratory_cluster_ols(group[target], x, group['seed'])
                              for target in ('delta_revenue_value_ratio', 'delta_bidders')}
        sg = sp[sp.engine == engine].groupby('seed').mean(numeric_only=True)
        spill[engine] = {metric: paired_seed_summary(sg[metric], sg.index.tolist()) for metric in
                        ('share_unmoved_changed_outcomes', 'mean_abs_delta_ratio_unmoved',
                         'total_revenue_delta_krw_all', 'total_revenue_delta_krw_moved', 'total_revenue_delta_krw_unmoved')}
    return {'seeds': list(SEEDS), 'contrast': 'concentrate_21 MINUS evening_spread; mixed schedule total effect',
            'policy_contrasts': comparisons, 'fix_change_in_policy_contrast': fix_changes,
            'exploratory_repeated_shift_ols': regressions,
            'ols_columns': ['intercept', 'delta_hour_weight', 'delta_conflicts', 'delta_duration_hours'],
            'spillover': spill, 'n_policy_rows': len(frame), 'n_shift_rows': len(shift)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    dest = args.out.resolve()
    allowed = (ROOT / 'data/experiments').resolve()
    if dest == allowed or not dest.is_relative_to(allowed) or dest.exists():
        raise ValueError('Use a NEW directory below data/experiments/')
    dest.mkdir(parents=True)
    jobs = [(s, seed, 'original') for s in 'BCD' for seed in SEEDS]
    jobs += [('B', seed, variant) for variant in ('flat', 'shift12h') for seed in SEEDS]
    rows, shifts, spillovers = [], [], []
    with ProcessPoolExecutor(args.workers) as pool:
        futures = {pool.submit(policy_job, job): job for job in jobs}
        for n, future in enumerate(as_completed(futures), 1):
            result = future.result()
            rows.extend(result)
            print('schedule probes', n, '/', len(jobs), futures[future], flush=True)
        futures = {pool.submit(shift_job, seed): seed for seed in SEEDS}
        for n, future in enumerate(as_completed(futures), 1):
            rr, ss = future.result()
            shifts.extend(rr)
            spillovers.extend(ss)
            print('repeated shift worlds', n, '/', len(SEEDS), flush=True)
    pd.DataFrame(rows).sort_values(['scenario', 'activity_variant', 'engine', 'seed', 'policy']).to_csv(dest / 'policy_seed_metrics.csv', index=False)
    pd.DataFrame(shifts).sort_values(['engine', 'seed', 'perturbation', 'auction_id']).to_csv(dest / 'repeated_shift_rows.csv', index=False)
    pd.DataFrame(spillovers).sort_values(['engine', 'seed', 'perturbation']).to_csv(dest / 'spillover_seed_metrics.csv', index=False)
    # Prove activity variants kept external worlds fixed, even though observations differ.
    f = pd.DataFrame(rows)
    assert all(g.external_world_sha256.nunique() == 1 for _, g in f[f.scenario == 'B'].groupby('seed'))
    result = summarize(rows, shifts, spillovers)
    result['B_activity_variants_share_external_world'] = True
    (ROOT / 'validation/audit/experiment_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Wrote independent-seed results; no required direction or winner.', flush=True)


if __name__ == '__main__':
    main()
