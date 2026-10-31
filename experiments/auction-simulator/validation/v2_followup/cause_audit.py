"""Passive deferral audit. Oracle truth is diagnostics ONLY, never buyer input."""
import bisect
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'validation/v2_choice'))
from evaluate import C, W, digest_world, guard_submissions, instrumented_run, signatures, to_tables, json_safe
from v2_choice.simulator import AlternativeMarket
from v2_choice.policy import compare
from metrics import exact_invariants
import pandas as pd


class AuditedMarket(AlternativeMarket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, trace=True, **kwargs)
        self.audit_deferrals = []

    def _choose_focal(self, t, b, a, visit=None):
        allowed = super()._choose_focal(t, b, a, visit)
        if not self._choice_trace:
            return allowed
        row = self._choice_trace.pop()
        if row['reason'] != 'choice_better_known_alternative':
            return allowed
        bid, aid, target = b['buyer_id'], a['auction_id'], row['best_id']
        book = self._knowledge[bid]
        q = book[target]
        actual = self.auc[target]
        # Current-state diagnostics: no WTP/RNG/cache/event operations.
        refreshed = {}
        for j, quote in book.items():
            live = self.auc[j]
            refreshed[j] = dict(quote, seen_at=t, ask=self.min_acceptable(live),
                                seen_end=t if live['closed'] else live['end'])
        st = self.state[bid]
        oracle = compare(t, aid, refreshed, row['free_budget'], st['leading'], st['won'],
                         lambda i, j: self.similarity(book[i]['item_id'], book[j]['item_id']))
        fresh_target = refreshed[target]
        score = self.similarity(book[aid]['item_id'], q['item_id'])*(q['wtp']-fresh_target['ask'])
        self.audit_deferrals.append(dict(time=t, event_ordinal=len(self.events), buyer_id=bid,
            focal_id=aid, target_id=target, visit_id=visit, known_end=q['seen_end'],
            quote_age_min=t-q['seen_at'], known_ask=q['ask'], actual_ask=fresh_target['ask'],
            target_price_changed=q['ask'] != fresh_target['ask'],
            target_actual_unaffordable=fresh_target['ask'] > row['free_budget'],
            target_actual_nonpositive=q['wtp'] <= fresh_target['ask'],
            target_actual_closed=actual['closed'], target_actual_score=score,
            own_surplus=row['own_surplus'], all_known_refreshed_allow=oracle['allow']))
        return allowed


def followthrough(m, records):
    """First deferral per buyer/target; do not treat repeated holds as independent."""
    grouped = {}
    for r in records:
        key = (r['buyer_id'], r['target_id'])
        if key not in grouped:
            grouped[key] = dict(r, repeat_deferrals=0)
        grouped[key]['repeat_deferrals'] += 1
    bybuyer = defaultdict(list)
    for ordinal, e in enumerate(m.events):
        bybuyer[e['buyer_id']].append((ordinal, e))
    result = []
    for (bid, target), r in grouped.items():
        limit = min(r['known_end'], m.buyers[bid]['leave_at'])
        rows = bybuyer[bid]
        begin = bisect.bisect_left([x[0] for x in rows], r['event_ordinal'])
        future = [e for _, e in rows[begin:] if e['event_time'] < limit]
        targetviews = [e for e in future if e['event_type']=='view' and e['auction_id']==target]
        targetbids = [e for e in future if e['event_type']=='bid' and e['auction_id']==target]
        anybids = [e for e in future if e['event_type']=='bid']
        anyview = any(e['event_type']=='view' for e in future)
        anyvisit = any(e['event_type']=='visit' for e in future)
        purchased = bool(targetbids) and m.auc[target]['leader']==bid
        category = ('target_purchased' if purchased else 'target_bid_not_won' if targetbids else
                    'target_view_no_bid' if targetviews else 'other_view_no_target' if anyview else
                    'accepted_visit_no_view' if anyvisit else 'no_later_accepted_opportunity')
        result.append(dict(r, window_end=limit, target_revisited=bool(targetviews),
            target_bid=bool(targetbids), target_purchased=purchased, later_any_bid=bool(anybids),
            later_accepted_visit=anyvisit, later_any_view=anyview, category=category,
            first_revisit_lag_min=targetviews[0]['event_time']-r['time'] if targetviews else None,
            first_revisit_cause=targetviews[0]['cause'] if targetviews else None))
    counts=Counter(r['category'] for r in result)
    summary={'deferral_events':len(records),'unique_buyer_targets':len(result),'categories':dict(counts)}
    for key in ('target_revisited','target_bid','target_purchased','later_any_bid','later_accepted_visit',
                'later_any_view','target_price_changed','target_actual_unaffordable',
                'target_actual_nonpositive','target_actual_closed','all_known_refreshed_allow'):
        summary[key]=sum(bool(r[key]) for r in result)
    summary['event_level_oracle_allow']=sum(r['all_known_refreshed_allow'] for r in records)
    summary['quote_age_median_min']=float(pd.Series([r['quote_age_min'] for r in records]).median()) if records else None
    return result, summary


def one(job):
    scenario, seed, dest = job
    cfg=C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml')
    w=W.build(cfg,seed); before=digest_world(w)
    ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
    m=AuditedMarket(w,ends,seed)
    with guard_submissions(): fp=instrumented_run(m)
    exact_invariants(m)
    old=json.loads((ROOT/'validation/v2_choice/results/evaluation-1.json').read_text(encoding='utf-8'))
    ref=old['datasets'][f'scenario_{scenario}/seed_{seed}']['primary']
    tables=to_tables(w,m,cfg,'seller_default')
    assert {k+'.csv':v for k,v in signatures(tables).items()}==ref['CSV_sha256']
    assert fp['rng_sha256']==ref['RNG_sha256'] and fp['queue_sha256']==ref['heap_sha256']
    assert digest_world(w)==before
    pairs, summary=followthrough(m,m.audit_deferrals)
    summary.update(behavior_csv_exact=True,RNG_exact=True,heap_exact=True,
                   decision_counts=dict(Counter(r['decision'] for r in m.decisions)))
    dest=Path(dest)/f'scenario_{scenario}/seed_{seed}';dest.mkdir(parents=True,exist_ok=False)
    pd.DataFrame(m.audit_deferrals).to_csv(dest/'deferrals.csv',index=False)
    pd.DataFrame(pairs).to_csv(dest/'first_target_followthrough.csv',index=False)
    return f'scenario_{scenario}/seed_{seed}',summary


def main():
    dest=ROOT/'validation/v2_followup/results/cause-audit'
    if dest.exists():raise FileExistsError(dest)
    results={}
    with ProcessPoolExecutor(2) as pool:
        futures=[pool.submit(one,(s,seed,str(dest))) for s in 'ABCDEF' for seed in (1,2,3)]
        for f in as_completed(futures):
            key,row=f.result();results[key]=row
            print(key,row['unique_buyer_targets'],row['target_revisited'],row['target_bid'],flush=True)
    (dest/'summary.json').write_text(json.dumps(json_safe(dict(sorted(results.items()))),indent=2),encoding='utf-8')

if __name__=='__main__':main()
