"""Compute only disjoint tail families before the ordered main queue reaches them.

Same evaluate_policy.one, same frozen source hashes and checkpoints. No additional
policies/seeds or choice of results. Main runner verifies and reuses completed
files when it reaches these queued jobs. Separate audit records this dispatch.
"""
import json
from concurrent.futures import ProcessPoolExecutor,as_completed
from evaluate_policy import ROOT,one,sources
from design import jobs

def main():
    selected=[j for j in jobs() if j['family'].startswith(('substitution_','model_','aligned_'))]
    assert len(selected)==57
    root=ROOT/'data/experiments/v2c-20261031/evaluation-2'
    spec=sources()
    registry=ROOT/'validation/v2_policy/results/auxiliary_dispatch.json'
    if registry.exists():raise FileExistsError(registry)
    registry.write_text(json.dumps(dict(role='same-condition tail checkpoints, not extra experimental observations',
        workers=3,sources=spec,jobs=selected),indent=2),encoding='utf-8')
    with ProcessPoolExecutor(3) as pool:
        futures=[pool.submit(one,(j,str(root),spec)) for j in reversed(selected)]
        for i,f in enumerate(as_completed(futures),1):
            key,result=f.result();print('TAIL PASS',i,'/57',key,flush=True)
    print('TAIL COMPLETE; main runner will hash-verify/reuse these records',flush=True)

if __name__=='__main__':main()
