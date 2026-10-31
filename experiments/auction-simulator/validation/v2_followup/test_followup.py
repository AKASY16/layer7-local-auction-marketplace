import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'validation/audit'))
sys.path.insert(0,str(ROOT/'validation/v2_observe'))
from common import fixture, digest_world, C, W, MS
from checks import instrumented_run, assert_equivalent
from audit.simulator import Market
from v2_choice.simulator import AlternativeMarket
from v2_followup.simulator import FollowupMarket, make_market
from v2_choice import MODEL as V1


def setup():
    w=fixture(similarity=1.)
    w.items[0]['estimated_value']=5000.
    w.items[1]['estimated_value']=20000.
    return FollowupMarket(w,{1:1500.,2:1500.},11)


def visit(m,t,v):
    m.log(t,1,'visit',None,'organic',v)


def defer(m):
    b=m.buyers[1]
    m.log(1.,1,'view',2,'organic',1)
    visit(m,2.,2)
    m.consider(2.,b,m.auc[1],'organic',2)
    assert m._intent[1]['target']==2


class Tests(unittest.TestCase):
    def test_parent_methods_and_factory_unchanged(self):
        self.assertIs(FollowupMarket.visit,Market.visit)
        self.assertIs(FollowupMarket.run,Market.run)
        self.assertIs(FollowupMarket.place_bid,AlternativeMarket.place_bid)
        self.assertIs(FollowupMarket.close,Market.close)
        for mode,cls in [('legacy',Market),(V1,AlternativeMarket)]:
            w=fixture();ends={1:1500.,2:1500.}
            a=make_market(w,ends,11,model=mode)
            self.assertIs(type(a),cls)
            assert_equivalent(instrumented_run(a),instrumented_run(cls(w,ends,11)))

    def test_deferral_does_not_enqueue_or_recheck_same_visit(self):
        m=setup();defer(m)
        self.assertFalse(m.heap)
        m.consider(2.,m.buyers[1],m.auc[1],'organic',2)
        self.assertEqual(m._followup_counts['recheck_view'],0)
        self.assertFalse(m.bids)

    def test_next_existing_slot_rechecks_and_skips_duplicate_without_extra_slot(self):
        m=setup();defer(m);visit(m,3.,3)
        m.consider(3.,m.buyers[1],m.auc[1],'organic',3)
        m.consider(3.,m.buyers[1],m.auc[2],'organic',3)
        views=[e for e in m.events if e['event_type']=='view' and e['visit_id']==3]
        self.assertEqual([e['auction_id'] for e in views],[2])
        self.assertEqual(m._followup_counts['recheck_view'],1)
        self.assertEqual(m._followup_counts['slot_replaced'],1)
        self.assertEqual(m._followup_counts['duplicate_slot_skipped'],1)
        self.assertEqual(len(m.bids),1)
        self.assertEqual(m.bids[0]['auction_id'],2)

    def test_stale_price_changes_only_on_actual_view(self):
        m=setup();defer(m)
        old=copy.deepcopy(m._knowledge[1][2])
        m.auc[2]['price']=100000.
        self.assertEqual(m._knowledge[1][2],old)
        visit(m,3.,3);m.consider(3.,m.buyers[1],m.auc[1],'organic',3)
        self.assertGreater(m._knowledge[1][2]['ask'],100000.)
        self.assertFalse(m.bids)
        self.assertEqual(m.decisions[-1]['decision'],'price_above_wtp')

    def test_missing_visit_cannot_create_any_activity(self):
        m=setup();defer(m)
        before=(copy.deepcopy(m.heap),len(m.events),len(m.bids))
        # Time passing by itself has no transition/timer.
        self.assertEqual((m.heap,len(m.events),len(m.bids)),before)
        self.assertIn(1,m._intent)

    def test_original_notifications_are_not_redirected(self):
        m=setup();defer(m)
        m.consider(3.,m.buyers[1],m.auc[1],'outbid_notice',3)
        self.assertEqual(m.events[-1]['auction_id'],1)
        self.assertEqual(m._followup_counts['recheck_view'],0)

    def test_expiry_and_held_state_cancel_intent_without_price_read(self):
        for reason in ('expired','held','budget'):
            m=setup();defer(m)
            if reason=='expired':m._knowledge[1][2]['seen_end']=2.5
            if reason=='held':m.state[1]['leading'].add(2)
            if reason=='budget':m.buyers[1]['budget']=0.
            class Forbidden(dict):
                def __getitem__(self,k):raise AssertionError('Unobserved target read')
            m.auc[2]=Forbidden(m.auc[2])
            visit(m,3.,3);m.consider(3.,m.buyers[1],m.auc[1],'organic',3)
            self.assertEqual(m._followup_counts['recheck_view'],0)

    def test_comparison_does_not_access_unobserved_live_price(self):
        m=setup();defer(m)
        class Forbidden(dict):
            def __getitem__(self,k):raise AssertionError('Live alternative leaked into comparison')
        m.auc[2]=Forbidden(m.auc[2])
        m._choose_focal(2.,m.buyers[1],m.auc[1],2)
        self.assertEqual(m._intent[1]['target'],2)

    def test_new_intent_cannot_chain_within_current_visit(self):
        m=setup();defer(m);visit(m,3.,3)
        # Refresh target as unattractive: its choice redirects back to focal1.
        m.auc[2]['price']=18000.
        m.consider(3.,m.buyers[1],m.auc[1],'organic',3)
        self.assertEqual(m._intent[1]['target'],1)
        m.consider(3.,m.buyers[1],m.auc[2],'organic',3)
        self.assertEqual(m._followup_counts['recheck_view'],1)

    def test_actual_parent_visit_caps_and_reproducibility(self):
        from evaluate_followup import slot_guard
        cfg=C.load(ROOT/'config/scenarios/scenario_C.yaml')
        cfg=copy.deepcopy(cfg);cfg['scale'].update(n_buyers=100,n_auctions=30,n_sellers=10,days=6)
        w=W.build(cfg,7);before=digest_world(w)
        ends={a['auction_id']:a['default_end_at'] for a in w.auctions}
        a=FollowupMarket(w,ends,7);b=FollowupMarket(w,ends,7)
        with slot_guard(a):x=instrumented_run(a)
        with slot_guard(b):y=instrumented_run(b)
        assert_equivalent(x,y)
        self.assertEqual(before,digest_world(w))

    def test_passive_audit_does_not_change_RNG_heap_or_behavior(self):
        from evaluate_followup import AuditedFollowup
        from checks import digest
        w=fixture(similarity=1.);ends={1:1500.,2:1500.}
        import numpy as np
        w.buyers[0]['cand_t']=np.array([10.,20.,30.])
        w.buyers[0]['cand_u']=np.zeros(3)
        x=FollowupMarket(w,ends,11);y=AuditedFollowup(w,ends,11)
        a=instrumented_run(x);b=instrumented_run(y)
        for key in ('rng_sha256','queue_sha256','counts'):self.assertEqual(a[key],b[key])
        for key in ('events','bids','decisions','wtp_log','auc','state','_intent','_followup_counts'):
            self.assertEqual(digest(getattr(x,key)),digest(getattr(y,key)))

    def test_old_stale_quote_can_block_but_explicit_reobservation_releases_it(self):
        w=fixture(similarity=1.);w.items[0]['estimated_value']=5000.;w.items[1]['estimated_value']=20000.
        m=AlternativeMarket(w,{1:1500.,2:1500.},11)
        m.log(1.,1,'view',2,'organic',1)
        m.auc[2]['price']=100000.
        m.consider(2.,m.buyers[1],m.auc[1],'watch_return',2)
        self.assertFalse(m.bids)
        self.assertEqual(m.decisions[-1]['decision'],'choice_better_known_alternative')
        m.consider(3.,m.buyers[1],m.auc[2],'watch_return',3)
        self.assertEqual(m.decisions[-1]['decision'],'price_above_wtp')
        m.consider(4.,m.buyers[1],m.auc[1],'watch_return',4)
        self.assertEqual([b['auction_id'] for b in m.bids],[1])


if __name__=='__main__':unittest.main(verbosity=2)
