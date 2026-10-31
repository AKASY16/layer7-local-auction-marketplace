"""Negative UTC offsets carry weekdays differently from their modulo24 phases."""
import hashlib
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'research/activity_20261031'
source=BASE/'activity_transfer_profiles.json'
original=json.loads(source.read_text(encoding='utf-8'))
p=json.loads((BASE/'retailrocket_analysis/profiles.json').read_text(encoding='utf-8'))['profiles']['unique_active']
def rotate(values,h):return np.roll(np.asarray(values).ravel(),h).reshape(7,24).tolist()
out=dict(source_country='UNVERIFIED',source_local_timezone='UNVERIFIED',
    classification='ASSUMED foreign-to-Korean lifestyle transfer; not empirical Korean activity',
    utc_to_kst_same_instant=original['utc_to_kst_same_instant'],
    local_UTC_offset_hypotheses={str(z):dict(source_offset_hypothesis_hours=z,
        training=rotate(p['train'],z),evaluation=rotate(p['evaluation'],z),
        meaning='Assume source local=UTC+z, then map same local weekday/hour to Korean model calendar; not simultaneous UTC->KST conversion')
        for z in (-12,-9,-6,-3,0,3,6,9,12)},
    abstract_phase_stress=original['lifestyle_phase_hypotheses'],
    abstract_phase_warning='15,18,21 are phase stress values, not geographic UTC-offset hypotheses; weekday differs from their negative modulo24 equivalents',
    limitations=original['limitations'],
    preserved_v1_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
dest=BASE/'activity_transfer_profiles_v2.json'
if dest.exists():raise FileExistsError(dest)
dest.write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Exported9signed local-offset hypotheses,8abstract phase stresses and separate KST display')
