"""Fixed18 worlds; three modes, no fitting or end-time policy optimization."""
import argparse
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor,as_completed
import gc
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/v2_choice'))
from evaluate import C,W,MS,digest_world,json_safe,guard_submissions,signatures,instrumented_run,assert_equivalent,to_tables
from metrics import summaries,exact_invariants
from audit.export import write_tables
from validate_dataset import structural
import validate as original
from v2_choice import MODEL as V1
from v2_followup import MODEL,ENGINE_VERSION
from v2_followup.simulator import FollowupMarket,make_market
from cause_audit import AuditedMarket,followthrough
from window_metrics import model_windows,empirical
import pandas as pd


class AuditedFollowup(AuditedMarket,FollowupMarket):
    """Audit consumes the parent's temporary trace after intent has been set."""
    pass


@contextmanager
def slot_guard(m):
    original=m.consider
    calls={};actual={};base=[]
    def checked(instance,t,b,a,mode,visit):
        if mode=='organic':
            key=(b['buyer_id'],visit)
            calls[key]=calls.get(key,0)+1
            start=len(m.events)
            result=original(t,b,a,mode,visit)
            viewed=[e for e in m.events[start:] if e['event_type']=='view']
            assert len(viewed)<=1
            actual.setdefault(key,[]).extend(e['auction_id'] for e in viewed)
            assert len(actual[key])<=calls[key]
            assert len(set(actual[key]))==len(actual[key])
            return result
        return original(t,b,a,mode,visit)
    # Class patch leaves no function object in the instance-state fingerprint.
    with patch.object(type(m),'consider',checked):yield


def one(job):
    s,seed,dest=job;key=f'scenario_{s}/seed_{seed}'
    cfg=C.load(ROOT/f'config/scenarios/scenario_{s}.yaml')
    w=W.build(cfg,seed);wh=digest_world(w)
    ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
    previous=json.loads((ROOT/'validation/v2_choice/results/evaluation-1.json').read_text(encoding='utf-8'))['datasets'][key]
    results={}
    organic_baseline=None
    view_caps=None
    for label,model in [('legacy','legacy'),('v1',V1),('v2b1',MODEL)]:
        m=make_market(w,ends,seed,model=model)
        start=perf_counter()
        with guard_submissions() as guarded:
            if label=='v2b1':
                with slot_guard(m):fp=instrumented_run(m)
            else:m.run();fp=None
        duration=perf_counter()-start
        invariants=exact_invariants(m)
        assert guarded['checked_submissions']==len(m.bids)
        assert wh==digest_world(w)
        tables=to_tables(w,m,cfg,'seller_default')
        sigs={k+'.csv':v for k,v in signatures(tables).items()}
        out=Path(dest)/key/label
        write_tables(tables,out,cfg,seed,ROOT/f'config/scenarios/scenario_{s}.yaml','seller_default')
        metadata=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
        metadata.update(choice_model=model,engine=ENGINE_VERSION if label=='v2b1' else metadata['engine'],
                        extra_behavior_assumptions='ASSUMED, see validation/v2_followup/PRE_IMPLEMENTATION.md' if label=='v2b1' else None)
        (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        structure=structural(original.load(out),cfg);assert structure['all_pass']
        record=dict(metrics=summaries(m),windows=model_windows(m),invariants=invariants,structure=structure,
            world_unchanged=True,CSV_sha256=sigs,choice_counts=dict(getattr(m,'_choice_counts',{})),
            followup_counts=dict(getattr(m,'_followup_counts',{})),runtime_instrumented_not_benchmark=duration)
        visits=[(e['event_time'],e['buyer_id']) for e in m.events if e['event_type']=='visit' and e['cause']=='organic']
        from collections import Counter
        caps=Counter((e['event_time'],e['buyer_id']) for e in m.events if e['event_type']=='view' and e['cause']=='organic')
        if organic_baseline is None:organic_baseline,view_caps=visits,caps
        assert visits==organic_baseline
        assert all(n<=view_caps[k] for k,n in caps.items())
        record.update(organic_opportunities_exact=True,organic_view_budget_not_increased=True)
        if label!='v2b1':
            assert sigs==previous['legacy' if label=='legacy' else 'primary']['CSV_sha256']
            record['frozen11_exact']=True
        else:
            # Same production mode, full state and ordered RNG/queue reproducibility.
            replay=FollowupMarket(w,ends,seed)
            with guard_submissions(),slot_guard(replay):repeated=instrumented_run(replay)
            assert_equivalent(fp,repeated)
            assert signatures(to_tables(w,replay,cfg,'seller_default'))==signatures(tables)
            exact_invariants(replay);del replay
            # Passive diagnostic instrument must not change the actual behavior.
            audited=AuditedFollowup(w,ends,seed)
            with guard_submissions(),slot_guard(audited):audited.run()
            assert signatures(to_tables(w,audited,cfg,'seller_default'))==signatures(tables)
            exact_invariants(audited)
            pairs,flow=followthrough(audited,audited.audit_deferrals)
            pd.DataFrame(audited.audit_deferrals).to_csv(out/'deferrals.csv',index=False)
            pd.DataFrame(pairs).to_csv(out/'first_target_followthrough.csv',index=False)
            record.update(reproducible=True,default_vs_audited11_exact=True,followthrough=flow,
                RNG_sha256=fp['rng_sha256'],heap_sha256=fp['queue_sha256'],RNG_calls=fp['counts'],state=fp['state'])
            del audited
        results[label]=record
        del m,tables;gc.collect()
    assert wh==digest_world(w)
    return key,results


def main():
    dest=ROOT/'data/experiments/v2b1-20261031/evaluation-1'
    report=ROOT/'validation/v2_followup/results/evaluation-1.json'
    if dest.exists() or report.exists():raise FileExistsError('Fresh evaluation directory required')
    results={}
    with ProcessPoolExecutor(2) as pool:
        futures=[pool.submit(one,(s,seed,str(dest))) for s in 'ABCDEF' for seed in (1,2,3)]
        for f in as_completed(futures):
            key,row=f.result();results[key]=row
            print(key,'PASS',[(k,v['metrics']['n_bids']) for k,v in row.items()],flush=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(json_safe(dict(n_worlds=len(results),all_mandatory_pass=len(results)==18,
        policy='seller_default hard close; unchanged World',no_tuning=True,datasets=dict(sorted(results.items())),
        JS_window_reference=empirical(ROOT))),indent=2,allow_nan=False),encoding='utf-8')
    print('ALL MANDATORY PASS',len(results),flush=True)

if __name__=='__main__':main()
