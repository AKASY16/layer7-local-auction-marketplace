"""Read frozen CSVs; re-use original structural checks without their write/delete CLI."""
import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C, json_safe
sys.path.insert(0, str(ROOT / 'validation'))
import validate as V


def one(path):
    d = Path(path)
    t = V.load(d)
    cfg = C.load(ROOT / t['meta']['scenario_file'])
    structure = V.structural(t, cfg)
    import pandas as pd
    lat = t['latent'].set_index('buyer_id')
    leave = V.mins(lat['active_until'], t['origin'])
    join = V.mins(lat['active_from'], t['origin'])
    bids = t['bids']
    bad = (bids['t'] > bids['buyer_id'].map(leave) + 1/60) | (bids['t'] < bids['buyer_id'].map(join) - 1/60)
    visits = t['visits']
    event_t = V.mins(visits['event_time'], t['origin'])
    bad_ev = (event_t > visits['buyer_id'].map(leave) + 1/60) | (event_t < visits['buyer_id'].map(join) - 1/60)
    return d.parent.name + '/' + d.name, {'original_structure': structure,
        'n_bids': len(bids), 'activity_window_bad_bids_conservative': int(bad.sum()),
        'bad_bid_types': bids.loc[bad, 'bid_type'].value_counts().to_dict(),
        'activity_window_bad_events_conservative': int(bad_ev.sum()),
        'timestamp_tolerance_seconds': 1,
        'late_bid_max_minutes': float((bids['t'] - bids['buyer_id'].map(leave)).max()),
        'moments': V.moments(t)}


def protection():
    manifest = json.loads((ROOT / 'BASELINE_v4.json').read_text(encoding='utf-8'))
    changed = []
    for section, prefix in [('defining_files', ROOT), ('data_csv', ROOT / 'data/synthetic')]:
        for name, expected in manifest[section].items():
            p = prefix / name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                changed.append(str(p.relative_to(ROOT)))
    return {'defining_files': len(manifest['defining_files']), 'data_csv_files': len(manifest['data_csv']),
            'changed': changed, 'ok': not changed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    paths = [str(p) for p in sorted((ROOT / 'data/synthetic').glob('scenario_*/seed_*'))]
    with ProcessPoolExecutor(args.workers) as pool:
        result = dict(pool.map(one, paths))
    out = {'protection': protection(), 'datasets': result,
           'structure_pass': sum(r['original_structure']['all_pass'] for r in result.values()),
           'activity_bad_bids_conservative': sum(r['activity_window_bad_bids_conservative'] for r in result.values())}
    (ROOT / 'validation/audit/baseline_data_audit.json').write_text(json.dumps(json_safe(out), indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'datasets'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
