"""Opt-in generation into a NEW data/experiments subdirectory only."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
import generate as G
import world as W
from v2_observe.simulator import simulate
from v2_observe.export import write_dataset


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scenario', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--end-times', type=Path)
    p.add_argument('--observer', action=argparse.BooleanOptionalAction, default=True)
    args = p.parse_args()
    allowed = (C.ROOT / 'data/experiments').resolve()
    out = args.out.resolve()
    if out == allowed or not out.is_relative_to(allowed) or out.exists():
        p.error('Use a NEW directory below data/experiments/')
    cfg = C.load(args.scenario)
    w = W.build(cfg, args.seed)
    ends = {a['auction_id']: a['default_end_at'] for a in w.auctions}
    if args.end_times:
        ends.update(G.parse_end_times(args.end_times, w))
    G.check_end_times(w, ends)
    m = simulate(w, ends, args.seed, cfg.get('close_rule', 'hard'), observer=args.observer)
    write_dataset(w, m, out, args.seed, args.scenario,
                  'override:'+args.end_times.name if args.end_times else 'seller_default')
    print('v2-a observer', args.observer, len(m.bids), 'bids ->', out)


if __name__ == '__main__':
    main()
