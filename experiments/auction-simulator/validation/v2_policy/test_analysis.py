import unittest
import pandas as pd
from analyze_policy import interval,summarize_pairs,METRICS

class StatisticalTests(unittest.TestCase):
    def test_shared_seed_scenarios_are_not_independent_samples(self):
        rows=[]
        for seed in range(1,6):
            for scenario in 'AB':
                rows.append(dict(family='test',policy='activity',scenario=scenario,seed=seed,
                    **{'delta_'+m:float(seed) for m in METRICS+['revenue_percent']}))
        q=summarize_pairs(pd.DataFrame(rows))
        r=q[q.scope.eq('large_AB')&q.metric.eq('revenue_per_listing')].iloc[0]
        self.assertEqual(r.n_seeds,5)
        self.assertEqual(r['mean'],3.)
        self.assertAlmostEqual(r.low,interval([1,2,3,4,5])['low'])

    def test_undefined_prices_are_not_filled_with_zero(self):
        r=interval([None,float('nan'),0.,1.])
        self.assertEqual(r['n_seeds'],2)
        self.assertEqual(r['mean'],.5)
        self.assertEqual((r['positive'],r['tied']),(1,1))
        self.assertIsNone(interval([None])['low'])

if __name__=='__main__':unittest.main(verbosity=2)
