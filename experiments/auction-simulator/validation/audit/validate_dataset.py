"""Extend the frozen hard-close checker, including empty and activity-window checks."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C
sys.path.insert(0, str(ROOT / 'validation'))
import validate as original


def structural(tables, cfg):
    if cfg.get('close_rule', 'hard') != 'hard':
        raise ValueError('This replay validator is for hard close; soft-close budget replay needs actual event order')
    if tables['bids'].empty:
        tables = dict(tables)
        tables['bids'] = tables['bids'].copy()
        tables['bids']['t'] = pd.Series(dtype=float)
    result = original.structural(tables, cfg)
    lat = tables['latent'].set_index('buyer_id')
    lower = original.mins(lat['active_from'], tables['origin'])
    upper = original.mins(lat['active_until'], tables['origin'])
    tol = 1/60  # exported ISO strings have only second precision
    bids, events = tables['bids'], tables['visits']
    result['bids_inside_buyer_activity_csv_precision'] = bool(((bids['t'] >= bids['buyer_id'].map(lower)-tol) &
                                                            (bids['t'] <= bids['buyer_id'].map(upper)+tol)).all())
    if len(events):
        time = original.mins(events['event_time'], tables['origin'])
        result['events_inside_buyer_activity_csv_precision'] = bool(((time >= events['buyer_id'].map(lower)-tol) &
                                                                  (time <= events['buyer_id'].map(upper)+tol)).all())
    else:
        result['events_inside_buyer_activity_csv_precision'] = True
    bid_events = events[events.event_type == 'bid']
    fields = ['visit_id', 'buyer_id', 'auction_id']
    recorded = sorted(tuple(x) for x in bid_events[fields].itertuples(index=False, name=None))
    submitted = sorted(tuple(x) for x in bids[fields].itertuples(index=False, name=None))
    result['bid_events_match_submitted_bids'] = recorded == submitted
    result['activity_timestamp_tolerance_seconds'] = 1
    result['all_pass'] = bool(result['all_pass'] and result['bids_inside_buyer_activity_csv_precision'] and
                              result['events_inside_buyer_activity_csv_precision'] and result['bid_events_match_submitted_bids'])
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'validation/audit').resolve()):
        raise ValueError('Use a NEW report path inside validation/audit/')
    paths = [args.root] if (args.root / 'metadata.json').exists() else sorted(args.root.glob('scenario_*/seed_*/audit-fix-v1'))
    if not paths:
        raise ValueError('No audit datasets found')
    records = {}
    for path in paths:
        tables = original.load(path)
        cfg = C.load(ROOT / tables['meta']['scenario_file'])
        records[str(path.relative_to(ROOT))] = structural(tables, cfg)
    output = {'all_pass': all(r['all_pass'] for r in records.values()), 'datasets': records}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('extended structure:', sum(r['all_pass'] for r in records.values()), '/', len(records))
    if not output['all_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
