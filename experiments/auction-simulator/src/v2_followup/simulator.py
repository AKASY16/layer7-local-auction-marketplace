"""Allocate an EXISTING organic view slot to the last deferred-to alternative.

ASSUMED, not an estimated behavioral law. No extra visit, view budget, RNG,
valuation change or oracle prices. Parent visit/run/bid/settlement are inherited.
"""
from collections import Counter
from v2_choice.simulator import AlternativeMarket, make_market as parent_factory
from v2_choice import MODEL as V1
from . import MODEL


class FollowupMarket(AlternativeMarket):
    def __init__(self, *args, trace=False, **kwargs):
        super().__init__(*args, trace=True, **kwargs)
        self._keep_choice_trace = trace
        self._intent = {}
        self._organic_context = {}
        self._followup_counts = Counter()

    def _choose_focal(self, time, buyer, auction, visit=None):
        n = len(self._choice_trace)
        allow = super()._choose_focal(time, buyer, auction, visit)
        if len(self._choice_trace) > n:
            row = self._choice_trace[-1]
            if row['reason'] == 'choice_better_known_alternative':
                self._intent[buyer['buyer_id']] = dict(target=row['best_id'], created_visit=visit)
                self._followup_counts['intent_created'] += 1
            if not self._keep_choice_trace:
                self._choice_trace.pop()
        return allow

    def log(self, time, buyer, kind, auction=None, cause=None, visit=None, extra=None):
        result = super().log(time, buyer, kind, auction, cause, visit, extra)
        if kind == 'visit' and cause == 'organic':
            self._organic_context[buyer] = dict(visit=visit, seen=set(), recheck_used=False)
        return result

    def consider(self, time, buyer, auction, mode, visit):
        bid = buyer['buyer_id']
        context = self._organic_context.get(bid)
        if mode == 'organic' and context is not None and context['visit'] == visit:
            intent = self._intent.get(bid)
            if not context['recheck_used'] and intent and intent['created_visit'] != visit:
                context['recheck_used'] = True
                self._intent.pop(bid)
                target = intent['target']
                quote = self._knowledge[bid][target]
                state = self.state[bid]
                free = buyer['budget']-state['spent']-state['committed']
                if quote['seen_end'] <= time or target in state['leading'] or target in state['won'] or quote['ask'] > free:
                    self._followup_counts['intent_no_longer_eligible'] += 1
                else:
                    self._followup_counts['recheck_requested'] += 1
                    candidate = self.auc[target]
                    # Server-side page availability, never an unobserved price oracle.
                    if not candidate['closed'] and candidate['start_at'] <= time <= candidate['end']:
                        self._followup_counts['recheck_view'] += 1
                        self._followup_counts['slot_replaced'] += target != auction['auction_id']
                        auction = candidate
                    else:
                        self._followup_counts['requested_page_unavailable'] += 1
            if auction['auction_id'] in context['seen']:
                self._followup_counts['duplicate_slot_skipped'] += 1
                return
            context['seen'].add(auction['auction_id'])
        intent = self._intent.get(bid)
        if intent and intent['target'] == auction['auction_id']:
            self._intent.pop(bid)
            self._followup_counts['natural_target_view'] += 1
        return super().consider(time, buyer, auction, mode, visit)


def make_market(world, ends, seed, close_rule='hard', *, model='legacy', trace=False):
    if model in ('legacy', V1):
        return parent_factory(world, ends, seed, close_rule, model=model, trace=trace)
    if model != MODEL:
        raise ValueError('Unknown model: '+str(model))
    return FollowupMarket(world, ends, seed, close_rule, trace=trace)


def simulate(world, ends, seed, close_rule='hard', **kwargs):
    return make_market(world, ends, seed, close_rule, **kwargs).run()
