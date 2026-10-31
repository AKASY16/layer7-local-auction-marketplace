import argparse
import gc
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import config as C
import world as W
from v2_choice.simulator import make_market
from v2_choice import MODEL
from v2_observe.simulator import Market as ObserveMarket


def run(w,ends,mode):
    if mode=='v2a_full_observer':return ObserveMarket(w,ends,1,observer=True).run()
    model='legacy' if mode=='legacy' else MODEL
    return make_market(w,ends,1,model=model,max_quote_age_min={'age60':60.,'age360':360.}.get(mode)).run()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists() or not a.out.resolve().is_relative_to((ROOT/'validation/v2_choice').resolve()):
        raise ValueError('Use a new v2_choice report path')
    w=W.build(C.load(ROOT/'config/scenarios/scenario_A.yaml'),1)
    ends={x['auction_id']:x['default_end_at'] for x in w.auctions}
    modes=['legacy','primary','age60','age360','v2a_full_observer']
    rows=[]
    for rep in range(3):
        order=modes[rep:]+modes[:rep]
        for mode in order:
            gc.collect();start=time.perf_counter();m=run(w,ends,mode);seconds=time.perf_counter()-start
            rows.append({'repeat':rep,'mode':mode,'seconds':seconds,'bids':len(m.bids),
                         'known_pairs':sum(len(v) for v in getattr(m,'_knowledge',{}).values()),
                         'extra_trace_rows':len(getattr(m,'_choice_trace',[]))})
            del m
            print('timing',rep,mode,round(seconds,3),flush=True)
    med={mode:statistics.median(r['seconds'] for r in rows if r['mode']==mode) for mode in modes}
    small=W.build(C.load(ROOT/'config/scenarios/scenario_A.yaml',overrides={'scale':
        {'n_buyers':200,'n_auctions':60,'n_sellers':15,'days':10}}),1)
    smallends={x['auction_id']:x['default_end_at'] for x in small.auctions}
    mem=[]
    for mode in ('legacy','primary','v2a_full_observer'):
        gc.collect();tracemalloc.start();m=run(small,smallends,mode)
        retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        mem.append({'mode':mode,'retained_python_bytes':retained,'peak_python_bytes':peak})
        del m
    result={'timing_case':'A seed1,1500buyers/500auctions/30days; init+run, no World generation/export/validation instrument',
            'system_load':'No task evaluation workers; other load uncontrolled',
            'repetitions':3,'raw':rows,'median_seconds':med,'primary_vs_legacy_ratio':med['primary']/med['legacy'],
            'primary_vs_V2A_observer_ratio':med['primary']/med['v2a_full_observer'],
            'memory_case':'200buyers/60auctions/10days; Python allocations after World generation, not full-size RSS',
            'allocations':mem}
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('BENCHMARK',json.dumps(result),flush=True)


if __name__=='__main__':main()
