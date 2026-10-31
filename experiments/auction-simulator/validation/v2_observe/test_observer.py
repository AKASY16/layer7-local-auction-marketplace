"""Behavioral equivalence and independent, hand-calculated diagnostics."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'validation/audit'))
from common import fixture, digest_world, C, W, MS
from audit.simulator import Market as AuditMarket
from audit.export import to_tables
from v2_observe.simulator import Market
from v2_observe.metrics import participation, SupplyMetrics
from v2_observe.export import diagnostic_tables, write_dataset, SCHEMAS
sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks import instrumented_run, assert_equivalent, diagnostic_invariants, engine_state


def triple(world, ends, seed, close_rule='hard', setup=None):
    before = digest_world(world)
    result = []
    markets = []
    for cls, kwargs in [(AuditMarket, {}), (Market, {'observer':False}), (Market, {'observer':True})]:
        m = cls(world, ends, seed, close_rule, **kwargs)
        if setup:
            setup(m)
        result.append(instrumented_run(m))
        markets.append(m)
        assert before == digest_world(world)
    assert_equivalent(result[0], result[1])
    assert_equivalent(result[0], result[2])
    diagnostic_invariants(markets[-1])
    return markets


class ObserverTests(unittest.TestCase):
    def test_inherits_all_behavioral_functions_without_copying(self):
        for name in ('run','wtp','place_bid','headroom','min_acceptable','push','schedule_watch','hour_weight','similarity'):
            self.assertIs(getattr(Market,name), getattr(AuditMarket,name), name)

    def test_six_scenarios_all_parent_state_rng_and_heap_operations_identical(self):
        for scenario in 'ABCDEF':
            with self.subTest(scenario=scenario):
                cfg = C.load(ROOT/f'config/scenarios/scenario_{scenario}.yaml', overrides={'scale':
                    {'n_buyers':40,'n_auctions':12,'n_sellers':4,'days':8}})
                w = W.build(cfg,903)
                ends = {a['auction_id']:a['default_end_at'] for a in w.auctions}
                triple(w,ends,903)

    def test_changed_policy_also_has_complete_parity(self):
        cfg=C.load(ROOT/'config/scenarios/scenario_C.yaml',overrides={'scale':
            {'n_buyers':40,'n_auctions':12,'n_sellers':4,'days':8}})
        w=W.build(cfg,24)
        ends={a['auction_id']:a['start_at']+1440. for a in w.auctions}
        triple(w,ends,24)

    def test_soft_extension_ties_and_settlement_preserve_heap_sequence(self):
        w=fixture()
        def setup(m):
            m.push(1499.,MS.RETURN,(1,1,'watch_return'))
            m.push(1500.,MS.RETURN,(1,2,'watch_return'))
        markets=triple(w,{1:1500.,2:1500.},11,'soft',setup)
        self.assertGreater(markets[-1].auc[1]['actual_end_at'],1500.)

    def test_empty_market_registration_excludes_unprocessed_same_time_listings(self):
        markets=triple(fixture(),{1:1500.,2:1500.},11)
        contexts=markets[-1].observer.records['market_context']
        self.assertEqual([r['M_positive_similarity_count'] for r in contexts],[0,0])
        self.assertFalse(markets[-1].observer.awareness.known)

    def metric_market(self):
        w=fixture()
        w.cfg['similarity'].update(same_series=.7,same_subcategory=.3,same_category=.1)
        w.cfg['params']['thickness_window_hours']=1.
        w.buyers[0]['interest']={'tcg':.6,'figure':.4}
        for i in (3,4,5,6,7,8):
            it=copy.deepcopy(w.items[0]);it['item_id']=i
            if i==3:it['series']='other'
            if i==4:it.update(series='other',subcategory='other')
            if i==5:it['category']='figure'
            w.items.append(it)
            a=copy.deepcopy(w.auctions[0]);a.update(auction_id=i,item_id=i,category=it['category'])
            if i==6:a['start_at']=1100.
            w.auctions.append(a)
        ends={1:1200.,2:1230.,3:1400.,4:2000.,5:1050.,6:1500.,7:1040.,8:999.}
        m=Market(w,ends,11)
        m.cat_open['tcg'].update((1,2,3,4,6,7,8))
        m.cat_open['figure'].add(5)
        m.auc[7]['closed']=True
        return m

    def test_N_and_M_T_are_distinct_hand_calculated_quantities(self):
        m=self.metric_market()
        n=participation(m,m.buyers[1],1000.)
        self.assertAlmostEqual(n['N_near_end_count'],.4)
        r=SupplyMetrics().measure(m,1000.,1)
        self.assertAlmostEqual(r['M_similarity_weighted'],1.1)
        self.assertEqual(r['M_positive_similarity_count'],3)
        self.assertEqual(r['M_catalog_proxy_count'],1)
        for h, expected in [(1,.7),(3,.7),(6,1.),(12,1.),(24,1.1)]:
            self.assertAlmostEqual(r[f'T_live_{h}h_weighted'],expected)

    def test_live_soft_extension_is_not_cached_and_scheduled_gap_is_separate(self):
        m=self.metric_market();metric=SupplyMetrics()
        before=metric.measure(m,1000.,1)
        m.auc[2]['end']=1500.
        after=metric.measure(m,1000.,1)
        self.assertAlmostEqual(before['T_live_1h_weighted'],.7)
        self.assertEqual(after['T_live_1h_weighted'],0.)
        self.assertAlmostEqual(after['T_scheduled_1h_weighted'],.7)
        self.assertAlmostEqual(after['M_similarity_weighted'],1.1)

    def test_supply_excludes_right_endpoint_and_future_registration(self):
        m=self.metric_market()
        m.auc[2]['end']=1000.
        r=SupplyMetrics().measure(m,1000.,1)
        self.assertAlmostEqual(r['M_similarity_weighted'],.4)
        self.assertEqual(r['M_positive_similarity_count'],2)

    def test_proxy_settlement_after_buyer_leaves_is_admin_state_not_a_view(self):
        w=fixture();w.buyers[0]['leave_at']=1495.
        markets=triple(w,{1:1500.,2:1500.},11,
                       setup=lambda m:m.push(1490.,MS.RETURN,(1,1,'watch_return')))
        o=markets[-1].observer
        self.assertTrue(any(r['stage']=='after_settlement' and r['time_min']==1500.
                            for r in o.records['purchase_state']))
        self.assertTrue(all(r['time_min']<1495. for r in o.records['awareness_events']))

    def test_missing_identity_is_unknown_and_not_a_verified_SKU(self):
        m=self.metric_market()
        del m.items[2]['condition']
        r=SupplyMetrics().measure(m,1000.,1)
        self.assertIsNone(r['M_catalog_proxy_count'])
        self.assertIsNone(r['T_live_1h_catalog_proxy_count'])

    def test_metrics_do_not_create_defaultdict_keys_or_mutate_market(self):
        m=Market(fixture(),{1:1500.,2:1500.},11)
        before=dict(m.cat_open)
        participation(m,m.buyers[1],10.)
        SupplyMetrics().measure(m,10.,1)
        self.assertEqual(before,dict(m.cat_open))

    def test_registration_order_has_no_future_same_time_information(self):
        w=fixture(similarity=.7)
        m=Market(w,{1:1500.,2:1500.},11).run()
        r=m.observer.records['market_context']
        self.assertEqual([x['scope'] for x in r],['at_registration']*2)
        self.assertEqual([x['M_similarity_weighted'] for x in r],[0.,.7])

    def test_skipped_view_never_populates_WTP_cache(self):
        m=Market(fixture(),{1:1500.,2:1500.},11)
        m.auc[1]['leader']=1
        with patch.object(m,'wtp',side_effect=AssertionError('observer evaluated WTP')):
            m.consider(10.,m.buyers[1],m.auc[1],'organic',1)
        self.assertEqual(m.wtp_log,{})
        row=m.observer.records['decision_context'][0]
        self.assertEqual(row['wtp_status'],'not_evaluated_by_legacy')
        self.assertIsNone(row['cached_quote_surplus_after_legacy'])

    def test_awareness_only_actual_views_and_no_automatic_quote_refresh(self):
        m=Market(fixture(),{1:1500.,2:1500.},11)
        m.auc[1]['leader']=1
        self.assertFalse(m.observer.awareness.known)
        m.consider(10.,m.buyers[1],m.auc[1],'organic',1)
        initial=copy.deepcopy(m.observer.awareness.known[1][1])
        m.auc[1].update(price=9999.,end=1800.)
        m.auc[2]['leader']=1
        m.consider(20.,m.buyers[1],m.auc[2],'organic',1)
        self.assertEqual(m.observer.awareness.known[1][1],initial)
        self.assertEqual([r['view_order'] for r in m.observer.records['awareness_events']],[1,2])
        self.assertEqual([r['known_count_before'] for r in m.observer.records['awareness_events']],[0,1])
        m.consider(30.,m.buyers[1],m.auc[1],'organic',2)
        self.assertEqual(m.observer.awareness.known[1][1]['seen_live_end_min'],1800.)

    def test_outbid_and_settlement_capture_other_buyers_and_detached_snapshots(self):
        w=fixture()
        other=copy.deepcopy(w.buyers[0]);other.update(buyer_id=2,price_level=2.)
        w.buyers.append(other)
        m=Market(w,{1:1500.,2:1500.},11)
        a=m.auc[1]
        a.update(price=1000.,leader=1,leader_max=5000.)
        m.state[1].update(committed=5000.,leading={1})
        m.consider(1490.,m.buyers[2],a,'watch_return',1)
        rows=[r for r in m.observer.records['purchase_state'] if r['buyer_id']==1 and 'outbid' in r['stage']]
        self.assertEqual([r['committed'] for r in rows],[5000.,0.])
        self.assertEqual(rows[0]['leading_auction_ids'],(1,))
        m.close(1500.,a)
        final=m.observer.records['purchase_state'][-1]
        self.assertEqual(final['stage'],'after_settlement')
        self.assertEqual(final['won_auction_ids'],(1,))

    def test_inactive_buyer_events_are_not_discoveries(self):
        w=fixture();w.buyers[0]['leave_at']=100.
        markets=triple(w,{1:1500.,2:1500.},11,setup=lambda m:m.push(101.,MS.RETURN,(1,1,'watch_return')))
        self.assertEqual(markets[-1].observer.records['awareness_events'],[])
        self.assertEqual(len(markets[-1].rejected_inactive_events),1)

    def test_empty_export_and_off_schemas_and_no_overwrite(self):
        parent=ROOT/'data/experiments/v2a-20261031/unit'
        parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(dir=parent,prefix='schemas-'))
        w=fixture()
        for enabled in (False,True):
            m=Market(w,{1:1500.,2:1500.},11,observer=enabled).run()
            destination=temp/str(enabled)
            base,diagnostics=write_dataset(w,m,destination,11,ROOT/'config/scenarios/scenario_B.yaml')
            self.assertEqual(set(diagnostics),set(SCHEMAS))
            for name,columns in SCHEMAS.items():
                self.assertEqual(list(diagnostics[name].columns),columns)
            ref=AuditMarket(w,{1:1500.,2:1500.},11).run()
            expected=to_tables(w,ref,w.cfg,'seller_default')
            for name in base:
                self.assertEqual(base[name].to_csv(index=False),expected[name].to_csv(index=False))
            with self.assertRaises(FileExistsError):
                write_dataset(w,m,destination,11,None)
        with self.assertRaises(ValueError):
            write_dataset(w,m,ROOT/'data/synthetic',11,None)

    def test_nonempty_diagnostic_export_and_frame_edits_do_not_mutate_parent(self):
        cfg=C.load(ROOT/'config/scenarios/scenario_A.yaml',overrides={'scale':
            {'n_buyers':40,'n_auctions':12,'n_sellers':4,'days':8}})
        w=W.build(cfg,903)
        m=Market(w,{a['auction_id']:a['default_end_at'] for a in w.auctions},903).run()
        before=engine_state(m)
        world_before=digest_world(w)
        frames=diagnostic_tables(m)
        self.assertGreater(len(frames['decision_context']),0)
        frames['decision_context'].loc[0,'cached_wtp_after']=-1.
        frames['purchase_state'].loc[0,'spent']=-1.
        self.assertEqual(before,engine_state(m))
        self.assertEqual(world_before,digest_world(w))


if __name__=='__main__':
    unittest.main(verbosity=2)
