"""Accounting diagnostic: original V2-C universal prior, original vs shared pool.

No new policy or tuning. Primary policy registry/results are untouched.
The main runner's world-prior bridge differs for scenario A's flat blend.
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'validation/v2_empirical'))
import run as R
from design import jobs

def one(pair):
    scenario,seed=pair
    cfg=R.C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml')
    original,calls=R.captured_world(cfg,seed)
    cells=jobs(scenario,seed,original)
    master=R.master_proposals(original,[(np.array(j['actual']),j['normalization']) for j in cells],seed)
    reference=json.loads((ROOT/'validation/v2_policy/results/evaluation-2.json').read_text(encoding='utf-8'))['datasets'][f'nominal/scenario_{scenario}/seed_{seed}']
    rows=[]
    for pool,w in [('original',original),('shared_envelope',master)]:
        items={i['item_id']:i for i in w.items}
        prior=R.W.profile('korea_evening')
        for policy in ('activity','conservative'):
            ends,trace,contexts=R.old_schedules(w.auctions,items,seed,prior,w.cfg['similarity'],policy,
                origin_minute=w.origin.hour*60+w.origin.minute)
            m=R.AuditMarket(w,ends,seed);checked=R.checked(m)
            result=R.summary(R.auction_rows(m,w,ends,contexts),m)
            exact=None
            if pool=='original':
                exact=all(result[k]==reference[policy]['summary'][k] for k in result)
                assert exact,(scenario,seed,policy,'Original policy summary no longer matches')
            rows.append(dict(scenario=scenario,seed=seed,pool=pool,policy=policy,summary=result,
                original_v2c_summary_exact=exact,**checked))
    print('BRIDGE PASS',scenario,seed,flush=True)
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=6);a=ap.parse_args()
    dest=ROOT/'validation/v2_empirical/results/exact_prior_bridge.json'
    if dest.exists():raise FileExistsError(dest)
    with ProcessPoolExecutor(a.workers) as pool:
        futures=[pool.submit(one,(s,sd)) for s in 'ABCDEF' for sd in (1,2,3)]
        records=[r for f in as_completed(futures) for r in f.result()]
    R.save(dest,dict(purpose='Accounting diagnostic, not policy selection',
        prior='Original universal korea_evening, including scenario A',records=records,
        original_exact_count=sum(r['original_v2c_summary_exact'] is True for r in records)))

if __name__=='__main__':main()
