"""Separate diagnostic storage. Never writes an engine-owned container."""
from .awareness import Awareness
from .metrics import SupplyMetrics, participation


def quote(market, auction):
    return {'observed_price': auction['price'],
            'minimum_acceptable': market.min_acceptable(auction),
            'seen_scheduled_end_min': auction['scheduled_end_at'],
            'seen_live_end_min': auction['end']}


class Observer:
    def __init__(self):
        self.records = {name: [] for name in ('participation', 'market_context', 'awareness_events',
                                             'purchase_state', 'decision_context')}
        self.awareness = Awareness()
        self.supply = SupplyMetrics()
        self.serial = 0
        self.observation_id = 0
        self.view_counts = {}
        self.active = None
        self.candidate = None

    def emit(self, table, market, time, **fields):
        self.serial += 1
        row = {'trace_id': self.serial, 'time_min': time,
               'engine_log_length': len(market.events), **fields}
        self.records[table].append(row)
        return row

    def n(self, market, buyer, time, stage, values=None, **fields):
        return self.emit('participation', market, time, buyer_id=buyer['buyer_id'], stage=stage,
                         **(values if values is not None else participation(market, buyer, time)), **fields)

    def context(self, market, time, auction, scope, observation_id=None):
        self.emit('market_context', market, time, auction_id=auction['auction_id'], scope=scope,
                  observation_id=observation_id, **self.supply.measure(market, time, auction['auction_id']))

    def q(self, market, time, buyer_id, stage, auction_id=None):
        st = market.state[buyer_id]
        self.emit('purchase_state', market, time, buyer_id=buyer_id, auction_id=auction_id, stage=stage,
                  observation_id=self.active['observation_id'] if self.active else None,
                  budget=market.buyers[buyer_id]['budget'], spent=st['spent'], committed=st['committed'],
                  uncommitted_budget=market.buyers[buyer_id]['budget'] - st['spent'] - st['committed'],
                  leading_auction_ids=tuple(sorted(st['leading'])), won_auction_ids=tuple(st['won']))

    def begin(self, market, time, buyer, auction, mode, visit):
        self.observation_id += 1
        order = self.view_counts.get(visit, 0) + 1
        self.view_counts[visit] = order
        bid, aid = buyer['buyer_id'], auction['auction_id']
        context = {'observation_id': self.observation_id, 'buyer_id': bid, 'auction_id': aid,
                   'visit_id': visit, 'mode': mode, 'view_order': order,
                   'decisions_start': len(market.decisions), 'bids_start': len(market.bids),
                   'cached_wtp_before': market.wtp_log.get((bid, aid)),
                   'minimum_acceptable_before': market.min_acceptable(auction)}
        self.active = context
        self.n(market, buyer, time, 'at_decision', observation_id=self.observation_id)
        self.context(market, time, auction, 'at_decision', self.observation_id)
        self.q(market, time, bid, 'before_consider', aid)
        return context

    def actual_view(self, market, time, buyer_id, auction_id, mode, visit):
        row = self.awareness.view(buyer_id, auction_id, time, quote(market, market.auc[auction_id]), mode)
        self.emit('awareness_events', market, time, observation_id=self.active['observation_id'] if self.active else None,
                  visit_id=visit, view_order=self.active['view_order'] if self.active else None, **row)

    def finish(self, market, time, context):
        bid, aid = context['buyer_id'], context['auction_id']
        cached = market.wtp_log.get((bid, aid))
        reasons = tuple(d['decision'] for d in market.decisions[context['decisions_start']:]
                        if d['buyer_id'] == bid and d['auction_id'] == aid)
        public = {k: v for k, v in context.items() if k not in ('decisions_start', 'bids_start')}
        self.emit('decision_context', market, time, **public, cached_wtp_after=cached,
                  wtp_status='evaluated_by_legacy' if cached is not None else 'not_evaluated_by_legacy',
                  cached_quote_surplus_after_legacy=(cached - context['minimum_acceptable_before']) if cached is not None else None,
                  legacy_decisions=reasons, submitted_bids=len(market.bids)-context['bids_start'])
        self.q(market, time, bid, 'after_consider', aid)
        self.active = None
