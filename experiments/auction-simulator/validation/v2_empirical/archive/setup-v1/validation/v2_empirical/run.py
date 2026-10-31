"""Checkpointed independent policy evaluation. Old code/data are read only."""
import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from time import perf_counter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/v2_choice'))
from evaluate import C,W,digest_world,json_safe,guard_submissions,to_tables,signatures,instrumented_run
from metrics import exact_invariants
from checks import engine_state,digest
from audit.simulator import Market as AuditMarket
from v2_policy_empirical.activity import (Market,captured_world,coupled_calendar,master_proposals,
    old_weekly,week_origin,expected_visits)
from v2_policy_empirical.policy import schedules,POLICIES
from v2_policy.policy import schedules as old_schedules
sys.path.insert(0,str(ROOT/'validation/v2_policy'))
from measures import auction_rows,summary
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import jobs,PROFILES

NEW=ROOT/'validation/v2_empirical'
DEST=ROOT/'data/experiments/v2c-retailrocket-20261031'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():
    files=list((ROOT/'src/v2_policy_empirical').glob('*.py'))+list(NEW.glob('*.py'))+[NEW/'PREREGISTRATION.md',PROFILES]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
def save(path,value):
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(json_safe(value),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def checked(m,instrument=False):
    start=perf_counter()
    with guard_submissions() as counts:
        fp=instrumented_run(m) if instrument else None
        if not instrument:m.run()
    inv=exact_invariants(m)
    assert counts['checked_submissions']==len(m.bids)
    return dict(state=digest(engine_state(m)),seconds=perf_counter()-start,invariants=inv,
        fingerprint={k:v for k,v in (fp or {}).items() if k not in ('state','instrumented_seconds')})

def trace_checks(trace,auctions):
    byid={a['auction_id']:a for a in auctions};groups={}
    for r in trace:
        assert r['t0']==byid[r['auction_id']]['start_at']
        assert r['t0']+1440<=r['end']<=r['t0']+4320
        assert all(byid[i]['start_at']<=r['t0'] and i!=r['auction_id'] for i in r['competitor_ids'])
        groups.setdefault(r['auction_id'],[]).append(r)
    for rows in groups.values():
        assert len(rows)==3 and sum(r['selected'] for r in rows)==1
        assert all(abs(x['end']-y['end'])>=180-1e-8 for i,x in enumerate(rows) for y in rows[i+1:])

def frozen_regression(w,seed,scenario):
    ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
    m=AuditMarket(w,ends,seed);checked(m)
    ref=json.loads((ROOT/'validation/v2_choice/results/evaluation-1.json').read_text(encoding='utf-8'))
    expected=ref['datasets'][f'scenario_{scenario}/seed_{seed}']['legacy']['CSV_sha256']
    observed={k+'.csv':v for k,v in signatures(to_tables(w,m,w.cfg,'seller_default')).items()}
    assert len(expected)==11 and expected==observed,(scenario,seed,'legacy reference changed')
    return dict(scenario=scenario,seed=seed,all11_exact=True,CSV_sha256=observed)

def one(payload):
    scenario,seed,experiment,spec,smoke=payload
    assert sources()==spec,'Sources changed after registration'
    cfg=C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml')
    original,calls=captured_world(cfg,seed);oh=digest_world(original)
    assert oh==digest_world(W.build(cfg,seed)),'Capturing changed World RNG'
    regression=frozen_regression(original,seed,scenario) if seed<=3 else None
    cells=jobs(scenario,seed,original)
    if smoke:cells=[j for j in cells if j['name'] in ('lagged','old_control','input_error_+6','global_normalization')]
    master=master_proposals(original,[(np.array(j['actual']),j['normalization']) for j in cells],seed)
    # Proposal arrays only may differ; no buyer traits, items, starts or valuations.
    for a,b in zip(original.buyers,master.buyers):
        assert digest({k:v for k,v in a.items() if k not in ('cand_t','cand_u','cap_rate_per_min')})==digest(
            {k:v for k,v in b.items() if k not in ('cand_t','cand_u','cap_rate_per_min')})
    output=DEST/experiment/f'scenario_{scenario}/seed_{seed}'
    output.mkdir(parents=True,exist_ok=True)
    cache={};records=[];replays=0;actual_runs=0
    for j in cells:
        actual=np.array(j['actual']);prior=np.array(j['prior'])
        w=coupled_calendar(master,calls,actual,seed,j['decoupled'])
        if j['name']=='old_control':
            assert [a['default_end_at'] for a in w.auctions]==[a['default_end_at'] for a in original.auctions]
        wh=digest_world(w);items={i['item_id']:i for i in w.items}
        cellpath=output/j['name']
        # A completed cell is immutable and can be resumed only under the same sources.
        if (cellpath/'records.json').exists():
            data=json.loads((cellpath/'records.json').read_text(encoding='utf-8'))
            assert data['sources']==spec
            for rel,h in data['files'].items():assert sha(cellpath/rel)==h
            records+=data['records'];continue
        if cellpath.exists():raise FileExistsError('Incomplete cell preserved; use fresh experiment name')
        cellpath.mkdir()
        cellrecords=[]
        for policy in POLICIES:
            ends,trace,contexts=schedules(w.auctions,items,seed,prior,w.cfg['similarity'],policy,week_origin(w),j['adoption'])
            trace_checks(trace,w.auctions)
            key=digest((wh,j['normalization'],j['availability'],actual,ends))
            replay_required=j['name']=='lagged' or seed==1
            instrument=smoke and j['name']=='lagged' and policy=='combined'
            hit=key in cache
            if not hit:
                m=Market(w,ends,seed,actual,j['normalization'],j['availability'])
                record=checked(m,instrument);actual_runs+=1
                rows=auction_rows(m,w,ends,contexts)
                v=Counter(e['cause'] for e in m.events if e['event_type']=='visit')
                record.update(summary=summary(rows,m),rows=rows,visit_causes=dict(v),volume=expected_visits(m),replayed=False)
                # Old weekly curve must leave all business outputs identical on same pool.
                if j['name']=='old_control':
                    control=AuditMarket(w,ends,seed);checked(control);actual_runs+=1
                    assert signatures(to_tables(w,m,w.cfg,'seller_default'))==signatures(to_tables(w,control,w.cfg,'seller_default'))
                    record['old_weekly_business_equivalent']=True
                cache[key]=record
            r=cache[key]
            if replay_required and not r['replayed']:
                repeat=Market(w,ends,seed,actual,j['normalization'],j['availability'])
                repeated=checked(repeat,instrument);actual_runs+=1;replays+=1
                assert r['state']==repeated['state'],'Full state replay differs'
                if instrument:assert r['fingerprint']==repeated['fingerprint'],'RNG/heap replay differs'
                r['replayed']=True;r['repeat_seconds']=repeated['seconds']
            # Context/adoption differs across cache users; attach to identical outcomes here.
            ctx={c['auction_id']:c for c in contexts}
            rows=[dict(row,**ctx[row['auction_id']]) for row in r['rows']]
            origin=week_origin(w)
            for row in rows:
                row['end_hour']=int((origin+row['end'])//60)%24
                row['manual_hour']=int((origin+row['manual_end'])//60)%24
                row['end_shift_hours']=(row['end']-row['manual_end'])/60
            datafile=cellpath/f'{policy}.csv';pd.DataFrame(rows).to_csv(datafile,index=False)
            # Save compact TOP3 audit sufficient to reproduce all choices without hidden state.
            save(cellpath/f'{policy}_top3.json',trace)
            rec={k:v for k,v in r.items() if k not in ('rows',)}
            error=float(np.abs(prior/prior.mean()-actual/actual.mean()).sum()/336)
            rec.update(condition=j['name'],scenario=scenario,seed=seed,policy=policy,settings=j,
                world_sha256=wh,schedule_sha256=digest(ends),cache_key=key,cache_hit=hit,
                prior_actual_TV=error,repeat_required=replay_required,
                policy_information='declared prior + already registered public listings only',
                source_scope='ASSUMED overseas shape transfer, NOT empirical Korean auction activity')
            cellrecords.append(rec)
        assert digest_world(w)==wh,'Market mutated World'
        save(cellpath/'records.json',dict(sources=spec,records=cellrecords,
            files={p.name:sha(p) for p in cellpath.iterdir()}))
        records+=cellrecords
    # Old policy bridge isolates score/tie changes from source/profile changes.
    bridge=[]
    if seed<=3 and not smoke:
        items={i['item_id']:i for i in master.items};prior=master.buyer_hour_profile
        for kind in ('activity','conservative'):
            ends,trace,contexts=old_schedules(master.auctions,items,seed,prior,master.cfg['similarity'],kind,
                origin_minute=master.origin.hour*60+master.origin.minute)
            m=AuditMarket(master,ends,seed);r=checked(m);actual_runs+=1
            rows=auction_rows(m,master,ends,contexts)
            bridge.append(dict(policy=kind,scenario=scenario,seed=seed,summary=summary(rows,m),**r))
    assert digest_world(original)==oh
    result=dict(scenario=scenario,seed=seed,records=records,bridge=bridge,regression=regression,
        executed_simulations_this_invocation=actual_runs,replays_this_invocation=replays,
        master_candidate_count=sum(len(b['cand_t']) for b in master.buyers),original_world_sha256=oh)
    save(output/'completed.json',result)
    return dict(scenario=scenario,seed=seed,records=len(records),runs=actual_runs,replays=replays)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--workers',type=int,default=6)
    ap.add_argument('--smoke',action='store_true');ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    if Path(a.name).name!=a.name:raise ValueError('Single experiment name')
    spec=sources();plan=[(s,sd) for s in 'ABCDEF' for sd in range(1,6)] if not a.smoke else [('F',1)]
    registry=NEW/'results'/f'{a.name}_registry.json'
    value=dict(sources=spec,worlds=plan,smoke=a.smoke,preregistration='PREREGISTRATION.md')
    if registry.exists():
        assert a.resume and json.loads(registry.read_text(encoding='utf-8'))==json_safe(value)
    else:save(registry,value)
    results=[]
    with ProcessPoolExecutor(a.workers) as pool:
        fut=[]
        for s,sd in plan:
            completed=DEST/a.name/f'scenario_{s}/seed_{sd}/completed.json'
            if completed.exists():
                if not a.resume:raise FileExistsError(completed)
                v=json.loads(completed.read_text(encoding='utf-8'));results.append(dict(scenario=s,seed=sd,records=len(v['records']),resumed=True))
            else:fut.append(pool.submit(one,(s,sd,a.name,spec,a.smoke)))
        for f in as_completed(fut):
            r=f.result();results.append(r);print('PASS',len(results),'/',len(plan),r,flush=True)
    save(NEW/'results'/f'{a.name}_completion.json',dict(worlds=results,all_jobs_completed=True,sources=spec))

if __name__=='__main__':main()
