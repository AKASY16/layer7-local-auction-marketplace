"""Export explicit clock conversion vs ASSUMED lifestyle transfer hypotheses."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'research/activity_20261031'
p=json.loads((BASE/'retailrocket_analysis/profiles.json').read_text(encoding='utf-8'))
audit=json.loads((BASE/'retailrocket_analysis/audit.json').read_text(encoding='utf-8'))
ua=p['profiles']['unique_active']
def shifted(values,h):return np.roll(np.asarray(values).reshape(168),h).reshape(7,24).tolist()
out=dict(source_local_timezone='UNVERIFIED',source_country='UNVERIFIED',assumption='ASSUMED foreign lifestyle transfer, NOT measured Korean activity',
    units='168 relative weekday-hour cells, weekly mean1; constant within each observed hour',
    split='Fixed in original UTC chronology before any phase rotation',
    utc_to_kst_same_instant=dict(offset_hours=9,
        first_UTC=audit['min_UTC'],first_KST=str(pd.Timestamp(audit['min_UTC']).tz_convert('Asia/Seoul')),
        last_UTC=audit['max_UTC'],last_KST=str(pd.Timestamp(audit['max_UTC']).tz_convert('Asia/Seoul')),
        training_shape=shifted(ua['train'],9),
        meaning='Same instants expressed in KST; NOT a Korean lifestyle demand estimate'),
    lifestyle_phase_hypotheses={str(h):dict(phase_hours=h,training=shifted(ua['train'],h),evaluation=shifted(ua['evaluation'],h),
        meaning='If a source-local clock phase h were appropriate, map that same weekday/lifestyle hour to model KST. No country inferred; no best phase selection.')
        for h in range(0,24,3)},
    limitations=['Source offsets and regions unidentified; fixed grid is not a posterior probability over timezones',
        'DST, half-hour offsets, mixed-region users and Korean-market transfer are not identified',
        'Positive shift moves peaks later on model clock and carries weekday boundaries',
        'The+9 same-instant shape numerically coincides with one hypothesis without making it the correct lifestyle transfer'])
path=BASE/'activity_transfer_profiles.json'
if path.exists():raise FileExistsError(path)
path.write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Exported8fixed phase hypotheses; KST display separated from lifestyle assumption')
print(out['utc_to_kst_same_instant']['first_KST'],out['utc_to_kst_same_instant']['last_KST'])
