"""A separate experiment. Only the substitute-skip branch is replaced."""
import math
from collections import Counter

from audit.simulator import Market as AuditMarket
from . import MODEL
from .consider import consider_experimental
from .policy import compare


class AlternativeMarket(AuditMarket):
    consider = consider_experimental

    def __init__(self, *args, max_quote_age_min=None, trace=False, **kwargs):
        if max_quote_age_min is not None and (not math.isfinite(max_quote_age_min) or max_quote_age_min < 0):
            raise ValueError('max_quote_age_min must be nonnegative finite or None')
        super().__init__(*args, **kwargs)
        self._knowledge = {}
        self._choice_counts = Counter()
        self._choice_trace = []
        self._record_trace = trace
        self._max_quote_age_min = max_quote_age_min

    def _observe_quote(self, time, buyer_id, auction_id, source):
        a = self.auc[auction_id]  # Only actual current view / own bid response.
        b = self.buyers[buyer_id]
        known = self._knowledge.setdefault(buyer_id, {})
        known[auction_id] = {'seen_at': time, 'seen_end': a['end'], 'ask': self.min_acceptable(a), 'item_id': a['item_id'],
                             'wtp': self.wtp(b, a), 'source': source}
        self._choice_counts['views' if source == 'view' else 'own_bid_feedback'] += 1

    def log(self, time, buyer, kind, auction=None, cause=None, visit=None, extra=None):
        result = super().log(time, buyer, kind, auction, cause, visit, extra)
        if kind == 'view':
            self._observe_quote(time, buyer, auction, 'view')
        return result

    def place_bid(self, time, buyer, auction, max_amount, bid_type, visit):
        result = super().place_bid(time, buyer, auction, max_amount, bid_type, visit)
        self._observe_quote(time, buyer['buyer_id'], auction['auction_id'], 'own_bid_feedback')
        return result

    def _choose_focal(self, time, buyer, auction, visit=None):
        bid, aid = buyer['buyer_id'], auction['auction_id']
        focal = self._knowledge[bid][aid]
        room = self.headroom(buyer, auction)
        # Preserve the parent's exact price/budget failure paths and reasons.
        if focal['wtp'] < focal['ask'] or room < focal['ask']:
            self._choice_counts['core_ineligible'] += 1
            return True
        state = self.state[bid]
        result = compare(time, aid, self._knowledge[bid], room, state['leading'], state['won'],
                         lambda i, j: self.similarity(self._knowledge[bid][i]['item_id'], self._knowledge[bid][j]['item_id']),
                         self._max_quote_age_min)
        for key, value in result['counters'].items():
            if key == 'max_quote_age_min':
                self._choice_counts[key] = max(self._choice_counts[key], value)
            else:
                self._choice_counts[key] += value
        self._choice_counts[result['reason']] += 1
        if self._record_trace:
            self._choice_trace.append({'time': time, 'buyer_id': bid, 'auction_id': aid,
                                       'free_budget': room, 'focal': dict(focal), **result})
        if not result['allow']:
            self.decide(time, bid, aid, result['reason'], visit)
        return result['allow']


def make_market(world, ends, seed, close_rule='hard', *, model='legacy', max_quote_age_min=None, trace=False):
    if model == 'legacy':
        if max_quote_age_min is not None or trace:
            raise ValueError('Choice diagnostics/age are experimental-mode settings only')
        return AuditMarket(world, ends, seed, close_rule)
    if model != MODEL:
        raise ValueError('Unknown model: '+str(model))
    return AlternativeMarket(world, ends, seed, close_rule, max_quote_age_min=max_quote_age_min, trace=trace)


def simulate(world, ends, seed, close_rule='hard', **kwargs):
    return make_market(world, ends, seed, close_rule, **kwargs).run()
