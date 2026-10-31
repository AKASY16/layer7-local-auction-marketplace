import copy
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/v2_choice'))
from evaluate import C,W,digest_world,to_tables,signatures,instrumented_run
from audit.simulator import Market as AuditMarket
from v2_policy_empirical.activity import (Curve,Market,normalize,shift,old_weekly,adjustments,
    captured_world,coupled_calendar,master_proposals,expected_visits,week_origin)
from v2_policy_empirical.policy import recommend,schedules,activity60
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import jobs

class EmpiricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=C.load(ROOT/'config/scenarios/scenario_F.yaml')
        cls.cfg=C.deep_merge(cls.cfg,{'scale':{'n_buyers':20,'n_auctions':12,'n_sellers':4}})
        cls.w,cls.calls=captured_world(cls.cfg,1)
    def test_capture_is_exact(self):self.assertEqual(digest_world(self.w),digest_world(W.build(self.cfg,1)))
    def test_calendar_control_exact(self):
        w=coupled_calendar(self.w,self.calls,normalize(old_weekly(self.w)),1)
        self.assertEqual(w.auctions,self.w.auctions)
    def test_periodic_integral_and_shift(self):
        x=np.arange(1,169).reshape(7,24);c=Curve(x)
        self.assertEqual(c.integral(0,10080),x.sum()*60)
        self.assertEqual(c.integral(-60,60),60*(x[-1,-1]+x[0,0]))
        y=shift(x,9);self.assertEqual(y[0,9],x[0,0]);self.assertEqual(y[1,0],x[0,15])
        # Hourly piecewise constant; no inferred half-hour detail.
        self.assertEqual(activity60(90,x,0),(x[0,0]+x[0,1])/2)
    def test_window_volume_and_cap(self):
        values=np.ones((7,24));values[:,17:21]=8;values=normalize(values)
        w=master_proposals(self.w,[(values,'window'),(values,'global')],1)
        m=Market(w,{a['auction_id']:a['default_end_at'] for a in w.auctions},1,values)
        self.assertAlmostEqual(expected_visits(m)['expected_ratio'],1.,places=12)
        for b in w.buyers:
            alpha,i,j,_=m.activity_adjustments[b['buyer_id']]
            self.assertAlmostEqual(alpha*i,j,places=8)
        self.assertLessEqual(m.activity_max_cap_ratio,1+1e-12)
    def test_old_weekly_rng_heap_and_business(self):
        w=self.w;ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
        old=AuditMarket(w,ends,1);new=Market(w,ends,1,normalize(old_weekly(w)))
        a=instrumented_run(old);b=instrumented_run(new)
        for k in ('rng_sha256','queue_sha256','counts'):self.assertEqual(a[k],b[k])
        self.assertEqual(signatures(to_tables(w,old,w.cfg,'seller_default')),signatures(to_tables(w,new,w.cfg,'seller_default')))
    def test_zero_activity_rejected_not_smoothed(self):
        self.assertRaises(ValueError,adjustments,self.w,np.zeros((7,24)))
    def test_feature_purity_and_future_book(self):
        item=dict(item_id=1,category='a',subcategory='s',series='x')
        other=dict(item_id=2,category='a',subcategory='s',series='x')
        book=[dict(auction_id=2,registered_at=-1,end=2880,item=other)]
        flat=np.ones((7,24));peak=flat.copy();peak[:,17]=10
        args=(item,0,book,flat,{'same_series':.8,'same_subcategory':.5,'same_category':.2})
        a=recommend(*args,'activity_only',0)
        b=recommend(item,0,[],flat,args[-1],'activity_only',0)
        self.assertEqual([r['end'] for r in a],[r['end'] for r in b])
        a=recommend(*args,'competition_only',0)
        b=recommend(item,0,book,peak,args[-1],'competition_only',0)
        self.assertEqual([r['end'] for r in a],[r['end'] for r in b])
        future=[dict(book[0],registered_at=1)]
        a=recommend(item,0,future,flat,args[-1],'combined',0)
        b=recommend(item,0,[],flat,args[-1],'combined',0)
        self.assertEqual(a,b)
        self.assertRaises(ValueError,recommend,dict(item,budget=1),0,[],flat,args[-1],'combined',0)
    def test_dominating_stream_deterministic(self):
        x=np.ones((7,24));conditions=[(x,'window')]
        self.assertEqual(digest_world(master_proposals(self.w,conditions,3)),digest_world(master_proposals(self.w,conditions,3)))
    def test_schedule_bounds_spacing_and_adoption(self):
        items={x['item_id']:x for x in self.w.items}
        for kind in ('manual','uniform_valid','activity_only','competition_only','combined'):
            ends,trace,context=schedules(self.w.auctions,items,1,np.ones((7,24)),self.w.cfg['similarity'],kind,week_origin(self.w),.2)
            starts={a['auction_id']:a['start_at'] for a in self.w.auctions}
            for aid,end in ends.items():self.assertTrue(starts[aid]+1440<=end<=starts[aid]+4320)
            groups={}
            for r in trace:groups.setdefault(r['auction_id'],[]).append(r)
            for rows in groups.values():
                self.assertEqual(len(rows),3)
                self.assertTrue(all(abs(a['end']-b['end'])>=180 for i,a in enumerate(rows) for b in rows[i+1:]))
    def test_registry_timezone_grid(self):
        names={j['name'] for j in jobs('B',1,self.w)}
        self.assertTrue({f'phase_{h:02}' for h in (3,6,9,12,15,18,21)}<=names)

if __name__=='__main__':unittest.main(verbosity=2)
