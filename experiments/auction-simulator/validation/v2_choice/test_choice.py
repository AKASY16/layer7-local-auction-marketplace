import ast
import copy
import inspect
import sys
import textwrap
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/audit'))
from common import fixture,C,W,digest_world,MS
from audit.simulator import Market as AuditMarket
from v2_choice.simulator import AlternativeMarket,make_market
from v2_choice.consider import consider_experimental
from v2_choice.policy import compare
sys.path.insert(0,str(ROOT/'validation/v2_observe'))
from checks import instrumented_run,assert_equivalent


def quote(v=10000.,q=1000.,end=1500.,seen=0.,item=1):
    return dict(wtp=v,ask=q,seen_end=end,seen_at=seen,item_id=item,source='view')


class ChoiceTests(unittest.TestCase):
    def test_only_original_skip_block_is_replaced_in_consider_AST(self):
        base=ast.parse(textwrap.dedent(inspect.getsource(MS.Market.consider))).body[0]
        new=ast.parse(textwrap.dedent(inspect.getsource(consider_experimental))).body[0]
        self.assertEqual(ast.dump(ast.Module(body=base.body[:6],type_ignores=[])),ast.dump(ast.Module(body=new.body[:6],type_ignores=[])))
        self.assertEqual(ast.dump(ast.Module(body=base.body[9:],type_ignores=[])),ast.dump(ast.Module(body=new.body[7:],type_ignores=[])))

    def test_legacy_factory_returns_exact_parent_and_RNG_heap_state_match(self):
        w=fixture();ends={1:1500.,2:1500.}
        x=make_market(w,ends,11)
        self.assertIs(type(x),AuditMarket)
        assert_equivalent(instrumented_run(AuditMarket(w,ends,11)),instrumented_run(x))

    def test_focal_discovery_precedes_comparison_and_only_seen_WTP_is_cached(self):
        m=AlternativeMarket(fixture(),{1:1500.,2:1500.},11)
        m.consider(10.,m.buyers[1],m.auc[1],'watch_return',1)
        self.assertEqual(set(m._knowledge[1]),{1})
        self.assertEqual(set(m.wtp_log),{(1,1)})

    def test_better_known_alternative_defers_without_new_events(self):
        m=AlternativeMarket(fixture(),{1:1500.,2:1500.},11,trace=True)
        m._knowledge[1]={2:quote(v=50000.,item=2)}
        m.sim_series=1.
        m.consider(10.,m.buyers[1],m.auc[1],'watch_return',1)
        self.assertFalse(m.bids)
        self.assertFalse(m.heap)
        self.assertEqual(m.decisions[-1]['decision'],'choice_better_known_alternative')
        self.assertEqual(m.decisions[-1]['visit_id'],1)

    def test_similarities_scale_only_comparison_not_current_WTP(self):
        k={1:quote(v=100.,q=10.),2:quote(v=150.,q=10.)}
        self.assertTrue(compare(1.,1,k,1000.,set(),[],lambda i,j:.1)['allow'])
        self.assertFalse(compare(1.,1,k,1000.,set(),[],lambda i,j:1.)['allow'])
        self.assertEqual(k[1]['wtp'],100.)

    def test_budget_unaffordable_and_expired_alternatives_are_not_actionable(self):
        for other in [quote(v=1e6,q=1001.),quote(v=1e6,end=1.)]:
            r=compare(1.,1,{1:quote(),2:other},1000.,set(),[],lambda i,j:1.)
            self.assertTrue(r['allow'])

    def test_held_leading_and_won_are_excluded_separately_not_global_unit_demand(self):
        known={1:quote(),2:quote(v=1e6)}
        a=compare(1.,1,known,1000.,{2},[],lambda i,j:1.)
        b=compare(1.,1,known,1000.,set(),[2],lambda i,j:1.)
        self.assertTrue(a['allow'] and b['allow'])
        self.assertEqual(a['counters']['leading_excluded'],1)
        self.assertEqual(b['counters']['won_excluded'],1)

    def test_multiple_purchases_are_possible_with_budget(self):
        m=AlternativeMarket(fixture(),{1:1500.,2:1500.},11)
        m.consider(10.,m.buyers[1],m.auc[1],'watch_return',1)
        m.close(1500.,m.auc[1])
        m.auc[2]['end']=2000.
        m.consider(1510.,m.buyers[1],m.auc[2],'watch_return',2)
        m.close(2000.,m.auc[2])
        self.assertEqual(m.state[1]['won'],[1,2])

    def test_outside_no_purchase_option_and_end_tie_break(self):
        self.assertFalse(compare(1.,1,{1:quote(v=10.,q=10.)},100.,set(),[],lambda i,j:1.)['allow'])
        k={1:quote(end=100.),2:quote(end=99.)}
        self.assertEqual(compare(1.,1,k,1000.,set(),[],lambda i,j:1.)['best_id'],2)

    def test_future_information_rejected_and_stale_cutoff_explicit(self):
        with self.assertRaises(ValueError):
            compare(1.,1,{1:quote(),2:quote(seen=2.)},1e6,set(),[],lambda i,j:1.)
        k={1:quote(seen=100.),2:quote(v=1e6,seen=0.)}
        self.assertFalse(compare(100.,1,k,1e6,set(),[],lambda i,j:1.)['allow'])
        self.assertTrue(compare(100.,1,k,1e6,set(),[],lambda i,j:1.,60.)['allow'])

    def test_unviewed_price_and_end_changes_are_not_read_by_comparison(self):
        m=AlternativeMarket(fixture(),{1:1500.,2:1500.},11)
        m._knowledge[1]={1:quote(item=1),2:quote(v=1e6,item=2)}
        m.sim_series=1.
        class Forbidden(dict):
            def __getitem__(self,k):raise AssertionError('Unobserved live alternative accessed')
        m.auc[2]=Forbidden(m.auc[2])
        self.assertFalse(m._choose_focal(10.,m.buyers[1],m.auc[1],1))

    def test_six_scenarios_reproduce_complete_state_RNG_queue_and_world(self):
        for scenario in 'ABCDEF':
            cfg=C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml',overrides={'scale':
                {'n_buyers':40,'n_auctions':12,'n_sellers':4,'days':8}})
            w=W.build(cfg,901);before=digest_world(w)
            ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
            x=instrumented_run(AlternativeMarket(w,ends,901))
            y=instrumented_run(AlternativeMarket(w,ends,901))
            assert_equivalent(x,y)
            self.assertEqual(digest_world(w),before)

    def test_soft_close_settlement_after_leave_and_time_order(self):
        w=fixture();w.buyers[0]['leave_at']=1499.5
        m=AlternativeMarket(w,{1:1500.,2:1500.},11,'soft')
        m.push(1499.,MS.RETURN,(1,1,'watch_return'))
        m.run()
        self.assertGreater(m.auc[1]['actual_end_at'],1500.)
        self.assertGreater(m.state[1]['spent'],0.)
        self.assertTrue(all(x['event_time']<1499.5 for x in m.events))
        self.assertEqual([x['event_time'] for x in m.events],sorted(x['event_time'] for x in m.events))


if __name__=='__main__':unittest.main(verbosity=2)
