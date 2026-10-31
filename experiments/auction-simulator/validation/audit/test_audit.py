"""Targeted regression tests for confirmed defects and statistical units."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, C, MS, W, fixture, simulate, json_safe
from baseline_audit import protection
from uncertainty import exploratory_cluster_ols, paired_seed_summary
from validate_dataset import structural
from audit.simulator import Market
from audit.export import to_tables, write_tables
sys.path.insert(0, str(ROOT / 'validation'))
import validate as original
import barista


class AuditTests(unittest.TestCase):
    def test_undefined_moments_are_standard_json_null(self):
        encoded = json.dumps(json_safe({'sd': np.float64(np.nan), 'nested': [float('inf'), 0., 1.5]}), allow_nan=False)
        self.assertEqual(json.loads(encoded), {'sd': None, 'nested': [None, 0., 1.5]})

    def test_frozen_manifest_intact(self):
        self.assertTrue(protection()['ok'])

    def test_active_interval_is_left_closed_right_open_for_every_buyer_event(self):
        for kind in (MS.VISIT, MS.ALERT, MS.RETURN, MS.SNIPE):
            w = fixture()
            w.buyers[0].update(join_at=100., leave_at=200.)
            market = Market(w, {1: 1500., 2: 1500.}, 11)
            for time in (99., 100., 199.999, 200., 201.):
                market.push(time, kind, (1, 1))
            self.assertEqual([e[0] for e in sorted(market.heap)], [100., 199.999])
            self.assertEqual(len(market.rejected_inactive_events), 3)

    def test_standing_proxy_can_settle_after_buyer_leaves(self):
        w = fixture()
        w.buyers[0]['leave_at'] = 1495.
        market = Market(w, {1: 1500., 2: 1500.}, 11)
        market.push(1490., MS.RETURN, (1, 1, 'watch_return'))
        market.run()
        self.assertEqual(market.auc[1]['leader'], 1)
        self.assertEqual(market.auc[1]['actual_end_at'], 1500.)
        self.assertGreater(market.state[1]['spent'], 0)

    def test_thickness_window_and_optional_extension_use_live_open_state(self):
        w = fixture()
        w.cfg['params']['thickness_window_hours'] = 1.
        market = Market(w, {1: 1500., 2: 1510.}, 11)
        market.cat_open['tcg'].update((1, 2))
        self.assertEqual(market.thickness(w.buyers[0], 1440.)[1], 1.)
        market.auc[1]['end'] = 1515.
        self.assertEqual(market.thickness(w.buyers[0], 1440.)[1], 0.)
        market.cat_open['tcg'].clear()
        self.assertEqual(market.thickness(w.buyers[0], 1490.)[1], 0.)

    def test_six_hour_window_future_listing_fix_is_inert_in_baseline_domain(self):
        # Minimum duration 24h > thickness window 6h. An unlisted auction
        # cannot end in the next 6h. Disable the separate activity fix.
        class ThicknessOnly(Market):
            push = MS.Market.push
        cfg = C.load(ROOT / 'config/scenarios/scenario_F.yaml', overrides={'scale':
                     {'n_buyers': 40, 'n_auctions': 12, 'n_sellers': 4, 'days': 10}})
        w = W.build(cfg, 902)
        ends = {a['auction_id']: a['default_end_at'] for a in w.auctions}
        self.assertEqual(cfg['params']['thickness_window_hours'], 6.)
        original = MS.Market(w, ends, 902).run()
        corrected = ThicknessOnly(w, ends, 902).run()
        self.assertEqual(original.bids, corrected.bids)
        self.assertEqual(original.events, corrected.events)

    def test_empty_market_roundtrip_and_extended_validation(self):
        w = fixture()
        market = simulate('audit-fix-v1', w, {1: 1500., 2: 1500.}, 11)
        tables = to_tables(w, market, w.cfg, 'control')
        parent = ROOT / 'data/experiments/audit-20261030/unit'
        parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix='empty-', dir=parent))
        destination = temp / 'dataset'
        write_tables(tables, destination, w.cfg, 11, ROOT / 'config/scenarios/scenario_B.yaml', 'control')
        loaded = original.load(destination)
        self.assertTrue(structural(loaded, w.cfg)['all_pass'])
        self.assertEqual(json.loads((destination / 'metadata.json').read_text())['generator_version'], 'audit-fix-v1')
        for name in ('bids', 'visits', 'hidden/valuations', 'hidden/decisions'):
            self.assertTrue(pd.read_csv(destination / f'{name}.csv').empty)
        with self.assertRaises(FileExistsError):
            write_tables(tables, destination, w.cfg, 11, None, 'control')

    def test_export_refuses_frozen_data(self):
        for path in (ROOT / 'data/synthetic/scenario_A/seed_1', ROOT / 'src', ROOT / 'data/experiments'):
            with self.assertRaises(ValueError):
                write_tables({}, path, {}, 11, None, 'test')

    def test_independent_seed_uncertainty_and_duplicate_rejection(self):
        summary = paired_seed_summary([1., 2., 3.], [11, 12, 13])
        self.assertAlmostEqual(summary['mean'], 2.)
        self.assertAlmostEqual(summary['sd_between_worlds'], 1.)
        self.assertAlmostEqual(summary['se_of_mean'], 1/math.sqrt(3))
        self.assertEqual(summary['n_independent_worlds'], 3)
        with self.assertRaises(ValueError):
            paired_seed_summary([1., 2., 3., 1.], [11, 12, 13, 11])
        with self.assertRaises(ValueError):
            paired_seed_summary([1., np.nan], [11, 12])

    def test_cluster_intercept_has_world_level_variance(self):
        # Three independent worlds, each observed twice. The known variance of
        # the mean is sample_variance([0,1,2])/3 = 1/3, not an iid six-row SE.
        result = exploratory_cluster_ols([0., 0., 1., 1., 2., 2.], np.empty((6, 0)), [1, 1, 2, 2, 3, 3])
        self.assertAlmostEqual(result['beta'][0], 1.)
        self.assertAlmostEqual(result['seed_cluster_se'][0], math.sqrt(1/3))
        self.assertEqual(result['cluster_df'], 2)

    def test_barista_inverse_cdf_unchanged(self):
        model = barista.Barista(3., .4, 1., .2, .002, 1.)
        u = np.linspace(.001, .999, 100)
        np.testing.assert_allclose(model.cdf(model.ppf(u)), u, rtol=1e-10, atol=1e-10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
