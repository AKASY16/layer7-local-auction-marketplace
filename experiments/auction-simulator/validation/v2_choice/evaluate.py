"""Fixed18 worlds, one model and two quote-age sensitivities; no tuning/policy search."""
import argparse
import gc
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor,as_completed
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/audit'))
from common import C,W,MS,digest_world,json_safe
from v2_choice import MODEL
from v2_choice.simulator import make_market
from v2_choice.export import write_dataset
from audit.export import to_tables
sys.path.insert(0,str(ROOT/'validation/v2_observe'))
from checks import instrumented_run,assert_equivalent
sys.path.insert(0,str(ROOT/'validation'))
import validate as original
from validate_dataset import structural
sys.path.insert(0,str(Path(__file__).resolve().parent))
from metrics import summaries,exact_invariants


@contextmanager
def guard_submissions():
    parent=MS.Market.place_bid
    counts={'checked_submissions':0}
    def guard(m,t,b,a,maximum,kind,visit):
        assert b['join_at']<=t<b['leave_at']
        assert a['start_at']<=t<=a['end'] and not a['closed']
        assert m.min_acceptable(a)<=maximum+1e-8
        assert maximum<=m.headroom(b,a)+1e-8
        assert maximum<=m.wtp_log[(b['buyer_id'],a['auction_id'])]+1e-8
        counts['checked_submissions']+=1
        return parent(m,t,b,a,maximum,kind,visit)
    with patch.object(MS.Market,'place_bid',guard):yield counts


def signatures(tables):
    return {k:hashlib.sha256(v.to_csv(index=False).encode('utf-8')).hexdigest() for k,v in tables.items()}


def one(job):
    scenario,seed,dest=job
    cfg=C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml')
    w=W.build(cfg,seed);wh=digest_world(w)
    ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
    result={}
    for mode,age in [('legacy',None),('primary',None),('age60',60.),('age360',360.)]:
        m=make_market(w,ends,seed,model='legacy' if mode=='legacy' else MODEL,max_quote_age_min=age)
        start=perf_counter()
        with guard_submissions() as guarded:
            fingerprint=instrumented_run(m) if mode=='primary' else None
            if fingerprint is None:m.run()
        seconds=perf_counter()-start
        invariants=exact_invariants(m)
        assert guarded['checked_submissions']==len(m.bids)
        assert wh==digest_world(w)
        out=Path(dest)/f'scenario_{scenario}/seed_{seed}/{mode}'
        tables=write_dataset(w,m,out,seed,ROOT/f'config/scenarios/scenario_{scenario}.yaml')
        validation=structural(original.load(out),cfg)
        assert validation['all_pass']
        record={'metrics':summaries(m),'invariants':invariants,'structure':validation,
                'choice_counters':dict(getattr(m,'_choice_counts',{})),
                'world_unchanged':True,'max_quote_age_min':age,'runtime_with_validation_not_benchmark':seconds,
                'CSV_sha256':{p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.csv')},
                'known_pairs':sum(len(v) for v in getattr(m,'_knowledge',{}).values())}
        if mode=='legacy':
            manifest=json.loads((ROOT/'AUDIT_FIX_v1.json').read_text(encoding='utf-8'))
            prefix=f'data/experiments/audit-20261030/regression/scenario_{scenario}/seed_{seed}/audit-fix-v1/'
            expected={k[len(prefix):]:v for k,v in manifest['corrected_csv_sha256'].items() if k.startswith(prefix)}
            assert len(expected)==11 and expected==record['CSV_sha256']
            record['frozen11_exact']=True
        if mode=='primary':
            expected_tables=signatures(tables)
            # Compare new model to itself, never to legacy event streams.
            replay=make_market(w,ends,seed,model=MODEL)
            with guard_submissions():
                repeated=instrumented_run(replay)
            assert_equivalent(fingerprint,repeated)
            assert signatures(to_tables(w,replay,cfg,'seller_default'))==expected_tables
            exact_invariants(replay)
            assert wh==digest_world(w)
            record.update(reproducible=True,RNG_sha256=fingerprint['rng_sha256'],
                          heap_sha256=fingerprint['queue_sha256'],RNG_calls=fingerprint['counts'])
            del replay
        result[mode]=record
        del m,tables
        gc.collect()
    return f'scenario_{scenario}/seed_{seed}',result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--workers',type=int,default=2)
    a=ap.parse_args()
    dest=a.out.resolve();report=a.report.resolve()
    allowed=(ROOT/'data/experiments/v2b-20261031').resolve()
    if dest.exists() or dest==allowed or not dest.is_relative_to(allowed):raise ValueError('Use a new V2B experiment directory')
    if report.exists() or not report.is_relative_to((ROOT/'validation/v2_choice').resolve()):raise ValueError('Use a new V2B report path')
    dest.mkdir(parents=True)
    results={}
    with ProcessPoolExecutor(a.workers) as pool:
        jobs=[(s,sd,str(dest)) for s in 'ABCDEF' for sd in (1,2,3)]
        for f in as_completed([pool.submit(one,j) for j in jobs]):
            key,value=f.result();results[key]=value
            print(key,'PASS', 'legacy',value['legacy']['metrics']['n_bids'],
                  'primary',value['primary']['metrics']['n_bids'],flush=True)
    output={'all_mandatory_pass':len(results)==18,'n_worlds':len(results),'n_independent_seed_labels':3,
            'scenarios_are_not18_independent_samples':True,'no_parameter_tuning':True,
            'policy':'seller_default only; no V2-C optimization','variants':['legacy','primary','age60','age360'],
            'datasets':dict(sorted(results.items()))}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(json_safe(output),indent=2,allow_nan=False),encoding='utf-8')
    print('MANDATORY CHECKS',output['all_mandatory_pass'],flush=True)


if __name__=='__main__':main()
