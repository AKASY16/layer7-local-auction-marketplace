"""Physical UTC-offset hypotheses, kept distinct from modulo-day phase stress."""
import argparse
import copy
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'validation/v2_empirical'))
import run as R
from design import jobs as base_jobs
from v2_policy_empirical.activity import adjustments,shift
BASE_MASTER=R.master_proposals
NEGATIVE=(-12,-9,-6,-3)
ALL=(-12,-9,-6,-3,0,3,6,9,12)

def extend_jobs(s,seed,w,mode):
    base=base_jobs(s,seed,w)[0];out=[]
    for offset in ALL if mode=='expanded' else (*NEGATIVE,0):
        j=copy.deepcopy(base);j.update(name=f'tz_{offset:+03d}',offset=offset,
            prior=shift(j['prior'],offset).tolist(),actual=shift(j['actual'],offset).tolist())
        out.append(j)
    return out

def bounds(s,seed):
    w=R.W.build(R.C.load(ROOT/f'config/scenarios/scenario_{s}.yaml'),seed)
    base=base_jobs(s,seed,w)
    master=BASE_MASTER(w,[(np.array(j['actual']),j['normalization']) for j in base],seed)
    maximum=0.
    for j in extend_jobs(s,seed,w,'existing'):
        a=adjustments(master,j['actual'])
        for b in master.buyers:
            alpha,_,_,peak=a[b['buyer_id']]
            ratio=b['visit_rate_per_day']/1440*alpha*peak*master.cfg['params']['thickness_multiplier_max']/b['cap_rate_per_min']
            maximum=max(maximum,ratio)
    return dict(scenario=s,seed=seed,maximum_new_rate_over_existing_cap=maximum)

def one(args):
    s,seed,mode,spec,script_hash=args
    assert R.sha(Path(__file__))==script_hash
    def roster(scenario,sd,w):return extend_jobs(scenario,sd,w,mode)
    def envelope(w,conditions,sd):
        base=base_jobs(s,sd,w)
        if mode=='expanded':base+=extend_jobs(s,sd,w,mode)
        return BASE_MASTER(w,[(np.array(j['actual']),j['normalization']) for j in base],sd)
    R.jobs=roster;R.master_proposals=envelope
    result=R.one((s,seed,'timezone-1',spec,False))
    if mode=='existing':
        parent=R.DEST/f'main-2/scenario_{s}/seed_{seed}/lagged/records.json'
        # A main cell can be completed before its parent world finishes all diagnostics.
        a=json.loads(parent.read_text(encoding='utf-8'))['records']
        b=json.loads((R.DEST/f'timezone-1/scenario_{s}/seed_{seed}/tz_+00/records.json').read_text(encoding='utf-8'))['records']
        by={r['policy']:r for r in a}
        for r in b:
            for k in ('state','world_sha256','schedule_sha256','summary'):
                assert r[k]==by[r['policy']][k],(s,seed,r['policy'],k,'zero offset anchor differs')
        result['all5_zero_offset_anchor_exact']=True
    print('TZ PASS',result,flush=True)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    dest=ROOT/'validation/v2_empirical/results/timezone-1_registry.json'
    if dest.exists():raise FileExistsError(dest)
    pairs=[(s,sd) for s in 'BCF' for sd in (1,2,3)]
    checks=[bounds(s,sd) for s,sd in pairs]
    mode='existing' if max(r['maximum_new_rate_over_existing_cap'] for r in checks)<=1+1e-12 else 'expanded'
    spec=R.sources();script_hash=R.sha(Path(__file__))
    assert spec==json.loads((ROOT/'validation/v2_empirical/results/main-2_registry.json').read_text(encoding='utf-8'))['sources']
    R.save(dest,dict(mode=mode,bounds=checks,offsets=list(ALL),additional_offsets=list(ALL if mode=='expanded' else (*NEGATIVE,0)),
        sources=spec,script_sha256=script_hash,protocol_sha256=R.sha(ROOT/'research/activity_20261031/TIMEZONE_EXTENSION_PROTOCOL.md'),
        no_outcome_based_selection=True))
    with ProcessPoolExecutor(a.workers) as pool:
        futures=[pool.submit(one,(s,sd,mode,spec,script_hash)) for s,sd in pairs]
        results=[f.result() for f in as_completed(futures)]
    R.save(ROOT/'validation/v2_empirical/results/timezone-1_completion.json',dict(mode=mode,worlds=results,all_pass=True))

if __name__=='__main__':main()
