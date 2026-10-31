"""Preregistered policy tests. Checkpoint each market; never overwrite an experiment."""
import argparse
import gc
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from time import perf_counter

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/v2_choice'))
from evaluate import C,W,digest_world,json_safe,guard_submissions,to_tables,signatures,instrumented_run,assert_equivalent
from metrics import exact_invariants
from checks import engine_state,digest
from v2_followup.simulator import make_market
from v2_policy.policy import schedules,ITEM_FIELDS
from design import jobs,varied_world
from measures import auction_rows,summary
import pandas as pd

CORE=['src/v2_policy/__init__.py','src/v2_policy/policy.py','validation/v2_policy/design.py',
      'validation/v2_policy/measures.py','validation/v2_policy/evaluate_policy.py','validation/v2_policy/PREREGISTRATION.md']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():return {k:sha(ROOT/k) for k in CORE}

def build_market(w,ends,seed,settings):
    m=make_market(w,ends,seed,model=settings.get('model','legacy'))
    sub=settings.get('substitution')
    if sub:
        values=(0.,0.,0.) if sub=='zero' else (.95,.6,.2)
        m.sim_series,m.sim_sub,m.sim_cat=values
    return m

def run_checked(m,instrument=False):
    with guard_submissions() as guard:
        if instrument:fp=instrumented_run(m)
        else:
            m.run();fp={'state':engine_state(m)}
    checks=exact_invariants(m)
    assert guard['checked_submissions']==len(m.bids)
    return fp,checks

def verify_trace(trace,auctions):
    starts={a['auction_id']:a['start_at'] for a in auctions}
    byaid={}
    for r in trace:
        assert starts[r['auction_id']]==r['t0']
        assert r['t0']+1440-1e-8<=r['end']<=r['t0']+4320+1e-8
        assert all(starts[j]<=r['t0'] and j!=r['auction_id'] for j in r['competitor_ids'])
        byaid.setdefault(r['auction_id'],[]).append(r)
    for rows in byaid.values():
        assert len(rows)<=3
        assert all(abs(x['end']-y['end'])>=180-1e-8 for i,x in enumerate(rows) for y in rows[i+1:])
        assert sum(x['selected'] for x in rows)==1

def old_reference(w,m,job,policy):
    if job.get('profile','base')!='base' or job.get('substitution') or policy!='manual' or job['seed']>3:return None
    key=f"scenario_{job['scenario']}/seed_{job['seed']}"
    model=job.get('model','legacy')
    path='validation/v2_followup/results/evaluation-1.json' if model=='known-surplus-followup-v1' else 'validation/v2_choice/results/evaluation-1.json'
    label='v2b1' if model=='known-surplus-followup-v1' else 'primary' if model=='known-surplus-v1' else 'legacy'
    ref=json.loads((ROOT/path).read_text(encoding='utf-8'))['datasets'][key][label]['CSV_sha256']
    actual={k+'.csv':v for k,v in signatures(to_tables(w,m,w.cfg,'seller_default')).items()}
    assert actual==ref,(key,model,'Frozen result differs')
    return {'all11_exact':True,'reference':path,'case':key,'mode':label}

def one(payload):
    job,root,expected_sources=payload
    assert sources()==expected_sources
    family,s,seed=job['family'],job['scenario'],job['seed']
    cfg=C.load(ROOT/f'config/scenarios/scenario_{s}.yaml')
    original=W.build(cfg,seed);oh=digest_world(original)
    w=varied_world(original,job.get('profile','base'));wh=digest_world(w)
    items={i['item_id']:i for i in w.items}
    prior=W.profile('korea_evening') if not job.get('aligned') else w.buyer_hour_profile.copy()
    weights=original.cfg['similarity']
    origin=w.origin.hour*60+w.origin.minute
    _,_,reference_context=schedules(w.auctions,items,seed,prior,weights,'manual',origin_minute=origin)
    reference={r['auction_id']:r for r in reference_context}
    result={}
    for policy in job['policies']:
        out=Path(root)/family/f'scenario_{s}/seed_{seed}'/policy
        if (out/'record.json').exists():
            record=json.loads((out/'record.json').read_text(encoding='utf-8'))
            assert record['sources']==expected_sources
            assert all(sha(out/n)==h for n,h in record['output_sha256'].items())
            result[policy]=record
            continue
        if out.exists():raise FileExistsError('Incomplete result preserved; use a fresh experiment: '+str(out))
        ends,trace,context=schedules(w.auctions,items,seed,prior,weights,policy,
            adoption=job.get('adoption',1.),choice=job.get('choice','closest'),origin_minute=origin)
        verify_trace(trace,w.auctions)
        replay_required=family=='nominal' or seed==1
        instrument=family=='nominal' and seed==1 and policy in ('conservative','activity')
        m=build_market(w,ends,seed,job)
        start=perf_counter();fp,invariants=run_checked(m,instrument)
        seconds=perf_counter()-start
        frozen=old_reference(w,m,job,policy)
        assert digest_world(w)==wh
        if replay_required:
            again=build_market(w,ends,seed,job)
            repeated,repeat_checks=run_checked(again,instrument)
            if instrument:assert_equivalent(fp,repeated)
            else:assert fp['state']==repeated['state']
            assert digest_world(w)==wh
            del again
        rows=auction_rows(m,w,ends,context)
        for r in rows:
            c=reference[r['auction_id']]
            r.update(reference_M=c['known_series_supply'],reference_T=c['known_series_near_manual'])
            group=[a for a in w.auctions if a['auction_id']!=r['auction_id'] and
                   items[a['item_id']]['category']==r['category'] and items[a['item_id']]['series']==r['series']]
            r['realized_series_near']=sum(abs(ends[a['auction_id']]-r['end'])<=60 for a in group)
            r['future_listed_series_near']=sum(abs(ends[a['auction_id']]-r['end'])<=60 and a['start_at']>r['start'] for a in group)
        record=dict(family=family,scenario=s,seed=seed,policy=policy,settings=job,
            engine=job.get('model','audit-fix-v1'),world_sha256=wh,original_world_sha256=oh,
            sources=expected_sources,summary=summary(rows,m),invariants=invariants,
            repeat_tested=replay_required,reproduced=replay_required,instrumented_RNG_heap=instrument,
            frozen_reference=frozen,public_prior=list(map(float,prior)),
            actual_ASSUMED_profile=list(map(float,w.buyer_hour_profile)),
            policy_information='prior+already registered public listings only; no outcome/buyer/actual profile access',
            schedule_sha256=digest(ends),behavior_state_sha256=digest(fp['state']),
            seconds_with_validation_not_benchmark=seconds)
        if instrument:record.update(RNG_sha256=fp['rng_sha256'],heap_sha256=fp['queue_sha256'])
        out.mkdir(parents=True,exist_ok=False)
        pd.DataFrame(rows).to_csv(out/'auctions.csv',index=False)
        (out/'recommendations.jsonl').write_text(''.join(json.dumps(json_safe(r),ensure_ascii=False,allow_nan=False)+'\n' for r in trace),encoding='utf-8')
        record['output_sha256']={p.name:sha(p) for p in out.iterdir()}
        (out/'record.json').write_text(json.dumps(json_safe(record),indent=2,allow_nan=False),encoding='utf-8')
        result[policy]=record
        del m;gc.collect()
    assert digest_world(original)==oh and digest_world(w)==wh
    return f'{family}/scenario_{s}/seed_{seed}',result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--name',default='evaluation-1');ap.add_argument('--resume',action='store_true')
    a=ap.parse_args()
    if Path(a.name).name!=a.name:raise ValueError('One experiment name')
    dest=ROOT/'data/experiments/v2c-20261031'/a.name
    report=ROOT/'validation/v2_policy/results'/f'{a.name}.json'
    if report.exists() or dest.exists() and not a.resume:raise FileExistsError('Existing results preserved')
    spec=sources();report.parent.mkdir(parents=True,exist_ok=True)
    registry=report.parent/f'{a.name}_design.json'
    design=dict(n_markets=729,n_repeats=343,jobs=jobs(),sources=spec)
    if registry.exists():assert json.loads(registry.read_text(encoding='utf-8'))==design
    else:registry.write_text(json.dumps(design,indent=2),encoding='utf-8')
    results={}
    with ProcessPoolExecutor(a.workers) as pool:
        futures=[pool.submit(one,(j,str(dest),spec)) for j in jobs()]
        for f in as_completed(futures):
            key,row=f.result();results[key]=row
            print('PASS',len(results),'/',len(jobs()),key,','.join(row),flush=True)
    flat=[r for v in results.values() for r in v.values()]
    assert len(flat)==729 and sum(r['repeat_tested'] for r in flat)==343
    output=dict(all_mandatory_pass=True,n_markets=len(flat),n_repeats=343,sources=spec,datasets=dict(sorted(results.items())),
        scope='ASSUMED simulated market policy comparisons; no Korean activity or real causal validation')
    report.write_text(json.dumps(json_safe(output),indent=2,allow_nan=False),encoding='utf-8')
    print('COMPLETE729, repeated343',flush=True)

if __name__=='__main__':main()
