import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import config as C
import world as W
import generate as G
from v2_choice import MODEL
from v2_choice.simulator import simulate
from v2_choice.export import write_dataset


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scenario',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',choices=['legacy',MODEL],default='legacy')
    p.add_argument('--max-quote-age-min',type=float)
    p.add_argument('--end-times',type=Path)
    a=p.parse_args()
    allowed=(C.ROOT/'data/experiments').resolve()
    dest=a.out.resolve()
    if dest.exists() or dest==allowed or not dest.is_relative_to(allowed):
        p.error('Use a new data/experiments subdirectory')
    cfg=C.load(a.scenario);w=W.build(cfg,a.seed)
    ends={x['auction_id']:x['default_end_at'] for x in w.auctions}
    if a.end_times:ends.update(G.parse_end_times(a.end_times,w))
    G.check_end_times(w,ends)
    m=simulate(w,ends,a.seed,cfg.get('close_rule','hard'),model=a.model,max_quote_age_min=a.max_quote_age_min)
    write_dataset(w,m,dest,a.seed,a.scenario,'override:'+a.end_times.name if a.end_times else 'seller_default')
    print(a.model,len(m.bids),'bids ->',dest)


if __name__=='__main__':main()
