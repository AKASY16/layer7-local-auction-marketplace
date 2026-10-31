"""Uninstrumented paired timings; Python allocation peak is measured separately."""
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
from audit.simulator import Market as AuditMarket
from v2_observe.simulator import Market


def run(w,ends,mode):
    if mode=='audit':
        return AuditMarket(w,ends,1).run()
    return Market(w,ends,1,observer=mode=='on').run()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or not a.out.resolve().is_relative_to((ROOT/'validation/v2_observe').resolve()):
        raise ValueError('Use a new v2_observe report path')
    cfg=C.load(ROOT/'config/scenarios/scenario_A.yaml')
    w=W.build(cfg,1)
    ends={x['auction_id']:x['default_end_at'] for x in w.auctions}
    timings=[]
    for repetition,order in enumerate([('audit','off','on'),('off','on','audit'),('on','audit','off')]):
        for mode in order:
            gc.collect()
            start=time.perf_counter()
            m=run(w,ends,mode)
            elapsed=time.perf_counter()-start
            timings.append({'repeat':repetition,'mode':mode,'seconds_init_plus_simulation':elapsed,
                            'bids':len(m.bids),'events':len(m.events),
                            'diagnostic_rows':sum(len(rows) for rows in m.observer.records.values()) if mode=='on' else 0})
            del m
            print('timing',repetition,mode,round(elapsed,3),flush=True)
    median={mode:statistics.median(r['seconds_init_plus_simulation'] for r in timings if r['mode']==mode)
            for mode in ('audit','off','on')}
    # Smaller, explicitly labeled allocation experiment; tracing isn't timed as
    # production performance and isn't presented as OS RSS or full-size memory.
    small=W.build(C.load(ROOT/'config/scenarios/scenario_A.yaml',overrides={'scale':
        {'n_buyers':200,'n_auctions':60,'n_sellers':15,'days':10}}),1)
    smallends={x['auction_id']:x['default_end_at'] for x in small.auctions}
    memory=[]
    for mode in ('audit','off','on'):
        gc.collect()
        tracemalloc.start()
        m=run(small,smallends,mode)
        retained,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory.append({'mode':mode,'retained_python_bytes':retained,'peak_python_bytes':peak,
                       'diagnostic_rows':sum(len(rows) for rows in m.observer.records.values()) if mode=='on' else 0})
        del m
    result={'timing_case':'scenario_A seed1:1500buyers/500auctions/30days; same World and seller_default policy',
            'timing_includes':'engine construction and simulation, in-memory trace collection; excludes World generation/export/instruments',
            'timing_repetitions':3,'order':'rotating audit/off/on; task regression workers stopped; other system load uncontrolled',
            'raw':timings,'median_seconds':median,
            'on_vs_off_ratio':median['on']/median['off'],'off_vs_audit_ratio':median['off']/median['audit'],
            'memory_case':'200buyers/60auctions/10days, one separate tracemalloc run per mode; not full-size memory or OS RSS',
            'python_allocations':memory,'storage':'See full regression diagnostic_csv_bytes for all18 cases'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print('BENCHMARK',json.dumps(result),flush=True)


if __name__=='__main__':
    main()
