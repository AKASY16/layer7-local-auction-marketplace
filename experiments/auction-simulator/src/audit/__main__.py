"""Opt-in generation: python src/audit/__main__.py --scenario ... --seed ... --out data/experiments/NEW"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
import generate as G
import world as W
from audit.export import to_tables, write_tables
from audit.simulator import simulate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', required=True, type=Path)
    ap.add_argument('--seed', required=True, type=int)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--end-times', type=Path)
    args = ap.parse_args()
    cfg = C.load(args.scenario)
    w = W.build(cfg, args.seed)
    ends = {a['auction_id']: a['default_end_at'] for a in w.auctions}
    if args.end_times:
        ends.update(G.parse_end_times(args.end_times, w))
    G.check_end_times(w, ends)
    m = simulate(w, ends, args.seed, cfg.get('close_rule', 'hard'))
    source = 'override:' + args.end_times.name if args.end_times else 'seller_default'
    tables = to_tables(w, m, cfg, source)
    write_tables(tables, args.out, cfg, args.seed, args.scenario, source)
    print('audit-fix-v1:', len(m.bids), 'bids ->', args.out)


if __name__ == '__main__':
    main()
