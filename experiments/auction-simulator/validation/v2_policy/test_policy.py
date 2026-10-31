import copy
import sys
import unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from v2_policy.policy import recommend,schedules,select,activity60,similarity
from design import jobs,varied_world
from evaluate_policy import C,W,build_market,run_checked,old_reference,digest_world,verify_trace
from measures import auction_rows,summary

ITEM=dict(item_id=1,category='tcg',subcategory='single',series='same')
WEIGHTS=dict(same_series=.7,same_subcategory=.3,same_category=.1)

def entry(i=2,start=0.,end=1800.):
    return dict(auction_id=i,registered_at=start,end=end,item=dict(ITEM,item_id=i))

class Tests(unittest.TestCase):
    def test_registry_counts_and_fixed_seeds(self):
        j=jobs();self.assertEqual(sum(len(x['policies']) for x in j),729)
        self.assertEqual(sum(len(x['policies']) for x in j if x['family']=='nominal' or x['seed']==1),343)

    def test_time_limits_spacing_and_bins(self):
        for mode in ('conservative','activity'):
            top=recommend(ITEM,17.,[],np.ones(24),WEIGHTS,mode)
            self.assertEqual(len(top),3)
            self.assertTrue(all(1457<=r['end']<=4337 for r in top))
            self.assertTrue(all(abs(x['end']-y['end'])>=180 for i,x in enumerate(top) for y in top[i+1:]))
            if mode=='conservative':
                self.assertEqual([int((r['duration_hours']-24)//16) if r['duration_hours']<72 else 2 for r in top],[0,1,2])

    def test_future_competitors_cannot_change_candidates(self):
        a=recommend(ITEM,0.,[],np.ones(24),WEIGHTS,'activity')
        future=entry(start=1.)
        b=recommend(ITEM,0.,[future],np.ones(24),WEIGHTS,'activity')
        self.assertEqual(a,b)

    def test_expired_and_other_category_do_not_create_conflict(self):
        book=[entry(end=-1.),dict(entry(),item=dict(ITEM,item_id=3,category='figure'))]
        self.assertTrue(all(r['conflict']==0 for r in recommend(ITEM,0.,book,np.ones(24),WEIGHTS,'conservative')))

    def test_exact_kernel_and_information_fields(self):
        top=recommend(ITEM,0.,[entry(end=1440.)],np.ones(24),WEIGHTS,'activity')
        # The chosen less crowded alternatives do not include unknown outcome fields.
        self.assertTrue(all('winner' not in r for r in top))
        with self.assertRaises(ValueError):recommend(dict(ITEM,appeal=2.),0.,[],np.ones(24),WEIGHTS,'activity')
        with self.assertRaises(ValueError):recommend(ITEM,0.,[dict(entry(),item=dict(ITEM,item_id=2,wtp=9000))],np.ones(24),WEIGHTS,'activity')

    def test_activity_window_and_prior_validation(self):
        p=np.ones(24);p[0]=3.
        self.assertAlmostEqual(activity60(30.,p),2.)
        self.assertAlmostEqual(activity60(60.,p),3.)
        with self.assertRaises(ValueError):activity60(1.,[0.]*24)

    def test_choice_uses_declared_candidates_not_realized_results(self):
        top=recommend(ITEM,0.,[],np.ones(24),WEIGHTS,'conservative')
        self.assertEqual(select(top,4000.,'conservative')['end'],min(top,key=lambda r:abs(r['end']-4000))['end'])
        self.assertIn(select(top,0.,'conservative','best'),top)

    def test_sequential_registration_and_repeat_determinism(self):
        a=[dict(auction_id=1,item_id=1,start_at=0.,default_end_at=1800.),dict(auction_id=2,item_id=2,start_at=1.,default_end_at=1900.)]
        items={1:ITEM,2:dict(ITEM,item_id=2)}
        for mode in ('manual','uniform_valid','fixed48h','conservative','activity'):
            x=schedules(a,items,5,np.ones(24),WEIGHTS,mode)
            y=schedules(a,items,5,np.ones(24),WEIGHTS,mode)
            self.assertEqual(x,y);verify_trace(x[1],a)
            self.assertTrue(all(not r['competitor_ids'] for r in x[1] if r['auction_id']==1))

    def test_activity_variants_preserve_buyer_conditions_and_cap(self):
        cfg=C.load(ROOT/'config/scenarios/scenario_A.yaml');cfg['scale'].update(n_buyers=50,n_auctions=20,n_sellers=5,days=6)
        w=W.build(cfg,1);old=digest_world(w)
        for profile in ('day','night','weak','flat'):
            v=varied_world(w,profile)
            self.assertEqual(w.buyers[0]['budget'],v.buyers[0]['budget'])
            self.assertTrue(np.array_equal(w.buyers[0]['cand_t'],v.buyers[0]['cand_t']))
            self.assertLessEqual(v.buyer_hour_profile.max(),w.buyer_hour_profile.max()+1e-8)
        self.assertEqual(old,digest_world(w))

    def test_legacy_full_F_regression_and_changed_policy_replay(self):
        cfg=C.load(ROOT/'config/scenarios/scenario_F.yaml');w=W.build(cfg,1)
        items={i['item_id']:i for i in w.items}
        for pol in ('manual','conservative','activity'):
            ends,trace,ctx=schedules(w.auctions,items,1,W.profile('korea_evening'),w.cfg['similarity'],pol)
            m=build_market(w,ends,1,{})
            x,_=run_checked(m)
            y,_=run_checked(build_market(w,ends,1,{}))
            self.assertEqual(x,y)
            rows=auction_rows(m,w,ends,ctx)
            self.assertEqual(len(rows),len(w.auctions))
            self.assertEqual(summary(rows,m)['n_auctions'],50)
            if pol=='manual':self.assertTrue(old_reference(w,m,dict(scenario='F',seed=1),pol)['all11_exact'])

if __name__=='__main__':unittest.main(verbosity=2)
