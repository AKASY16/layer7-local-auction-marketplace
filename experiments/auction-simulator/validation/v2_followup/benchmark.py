"""Same-machine interleaved execution; time excludes World construction/validation."""
import copy
import gc
import json
import statistics
import sys
import tracemalloc
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/audit'))
from common import C,W
from v2_followup.simulator import make_market
from v2_followup import MODEL
from v2_choice import MODEL as V1

def main():
    out=ROOT/'validation/v2_followup/results/benchmark.json'
    if out.exists():raise FileExistsError(out)
    cfg=C.load(ROOT/'config/scenarios/scenario_A.yaml');w=W.build(cfg,1)
    ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
    models=['legacy',V1,MODEL];times={k:[] for k in models}
    for i in range(3):
        for model in models[i:]+models[:i]:
            gc.collect();start=perf_counter();m=make_market(w,ends,1,model=model).run()
            times[model].append(perf_counter()-start);del m
    cfg=copy.deepcopy(cfg);cfg['scale'].update(n_buyers=200,n_sellers=20,n_auctions=60,days=10)
    small=W.build(cfg,1);e={a['auction_id']:a['default_end_at'] for a in small.auctions}
    peaks={}
    for model in models:
        gc.collect();tracemalloc.start()
        m=make_market(small,e,1,model=model).run()
        peaks[model]=tracemalloc.get_traced_memory()[1];tracemalloc.stop();del m
    out.write_text(json.dumps(dict(world='A seed1 1500buyers500auctions30d',repeats=3,
        measured='init+run only, one process; no validation/serialization/audit; after main evaluation',
        times=times,medians={k:statistics.median(v) for k,v in times.items()},
        Python_allocation_peak_small_world_bytes=peaks,
        memory_scope='200buyers60auctions10d, after World constructed; Python tracemalloc, not full RSS'),indent=2),encoding='utf-8')
    print(out.read_text(encoding='utf-8'))

if __name__=='__main__':main()
