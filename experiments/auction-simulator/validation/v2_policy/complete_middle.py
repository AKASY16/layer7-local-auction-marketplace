"""Additional CPU dispatch of already preregistered uptake/choice jobs only."""
import json
from concurrent.futures import ProcessPoolExecutor,as_completed
from evaluate_policy import ROOT,one,sources
from design import jobs

def main():
    selected=[j for j in jobs() if j['family'] in ('uptake20','choice_best')]
    assert len(selected)==24
    root=ROOT/'data/experiments/v2c-20261031/evaluation-2';spec=sources()
    registry=ROOT/'validation/v2_policy/results/auxiliary_middle_dispatch.json'
    if registry.exists():raise FileExistsError(registry)
    registry.write_text(json.dumps(dict(role='same preregistered checkpoints, no extra observations',workers=3,
        sources=spec,jobs=selected),indent=2),encoding='utf-8')
    with ProcessPoolExecutor(3) as pool:
        for i,f in enumerate(as_completed([pool.submit(one,(j,str(root),spec)) for j in reversed(selected)]),1):
            key,row=f.result();print('MIDDLE PASS',i,'/24',key,flush=True)
    print('MIDDLE COMPLETE',flush=True)

if __name__=='__main__':main()
