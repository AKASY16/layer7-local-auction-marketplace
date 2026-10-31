"""Clock semantics independent of any policy outcome."""
import json
import sys
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from v2_policy_empirical.activity import shift,Curve

class TimeTransferTests(unittest.TestCase):
    def test_negative_offset_not_positive_modulo_day(self):
        x=np.arange(168).reshape(7,24)
        self.assertEqual(shift(x,-3)[0,0],x[0,3])
        self.assertEqual(shift(x,21)[0,0],x[6,3])
        self.assertFalse(np.array_equal(shift(x,-3),shift(x,21)))
    def test_twelve_hour_sign_changes_weekday(self):
        x=np.arange(168).reshape(7,24)
        self.assertEqual(shift(x,-12)[0,0],x[0,12])
        self.assertEqual(shift(x,12)[0,0],x[6,12])
    def test_instant_conversion_vs_lifestyle_transfer(self):
        # Hypothetical UTC+3 source, not a claim about Retailrocket.
        raw=datetime(2015,5,3,17,tzinfo=timezone.utc)
        self.assertEqual(raw.astimezone(timezone(timedelta(hours=9))).isoformat(),'2015-05-04T02:00:00+09:00')
        x=np.zeros((7,24));x[6,17]=1
        self.assertEqual(shift(x,3)[6,20],1)  # source local Sunday20 -> model Sunday20
        self.assertEqual(shift(x,9)[0,2],1)   # same instant Monday02KST, different operation
    def test_export_signed_grid_and_unknown_region(self):
        d=json.loads((ROOT/'research/activity_20261031/activity_transfer_profiles_v2.json').read_text(encoding='utf-8'))
        self.assertEqual(set(map(int,d['local_UTC_offset_hypotheses'])),{-12,-9,-6,-3,0,3,6,9,12})
        self.assertEqual(d['source_local_timezone'],'UNVERIFIED')
        self.assertEqual(d['source_country'],'UNVERIFIED')
    def test_signed_shift_preserves_total_mass(self):
        x=np.arange(1,169).reshape(7,24)
        for h in range(-12,22,3):
            y=shift(x,h);self.assertEqual(y.sum(),x.sum())
            self.assertEqual(Curve(y).integral(0,10080),Curve(x).integral(0,10080))

if __name__=='__main__':unittest.main(verbosity=2)
