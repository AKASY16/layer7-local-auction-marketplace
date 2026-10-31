"""New output directories only; defaults to the frozen legacy engine."""
import argparse
import json
from pathlib import Path
import config as C
import world as W
from audit.export import to_tables,write_tables
from v2_choice import MODEL as V1
from . import MODEL,ENGINE_VERSION
from .simulator import make_market


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=1)
    ap.add_argument('--model',choices=['legacy',V1,MODEL],default='legacy')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    allowed=(C.ROOT/'data/experiments/v2b1-20261031').resolve()
    dest=args.out.resolve()
    if dest.exists() or dest==allowed or not dest.is_relative_to(allowed):
        raise ValueError('Use a NEW child of data/experiments/v2b1-20261031')
    cfg=C.load(args.scenario)
    w=W.build(cfg,args.seed)
    m=make_market(w,{a['auction_id']:a['default_end_at'] for a in w.auctions},args.seed,model=args.model).run()
    write_tables(to_tables(w,m,cfg,'seller_default'),dest,cfg,args.seed,args.scenario,'seller_default')
    p=dest/'metadata.json';meta=json.loads(p.read_text(encoding='utf-8'))
    meta.update(choice_model=args.model,experimental=args.model!='legacy')
    if args.model==MODEL:
        meta.update(engine=ENGINE_VERSION,generator_version=ENGINE_VERSION,
            parent_choice=V1,assumption_class='ASSUMED',new_numeric_parameters=0)
    p.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (dest/'choice_counters.json').write_text(json.dumps(dict(getattr(m,'_choice_counts',{})),indent=2),encoding='utf-8')
    (dest/'followup_counters.json').write_text(json.dumps(dict(getattr(m,'_followup_counts',{})),indent=2),encoding='utf-8')
    print(dest)

if __name__=='__main__':main()
