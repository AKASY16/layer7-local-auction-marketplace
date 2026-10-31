"""Opt-in passive wrappers around audit-fix-v1. No behavioral overrides."""
from audit.simulator import Market as AuditMarket
from .observer import Observer


class Market(AuditMarket):
    def __init__(self, *args, observer=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.observer = Observer() if observer else None
        if self.observer is not None:
            for buyer in self.buyers:
                self.observer.q(self, 0., buyer, 'initial')

    def thickness(self, buyer, time):
        multiplier, count = super().thickness(buyer, time)
        if self.observer is not None:
            row = self.observer.n(self, buyer, time, 'visit_candidate',
                                  candidate_index=self.observer.candidate,
                                  accepted=None)
            # The actual engine result is recorded, not substituted into it.
            row['N_near_end_count'] = count
            row['participation_multiplier'] = multiplier
        return multiplier, count

    def visit(self, time, buyer, candidate_index):
        if self.observer is None:
            return super().visit(time, buyer, candidate_index)
        o = self.observer
        before_visits = self.visit_counter
        start = len(o.records['participation'])
        o.candidate = candidate_index
        try:
            return super().visit(time, buyer, candidate_index)
        finally:
            o.candidate = None
            # First row is the original thickness call; later rows may be views.
            if len(o.records['participation']) > start:
                o.records['participation'][start]['accepted'] = self.visit_counter > before_visits

    def schedule_alerts(self, time, auction):
        if self.observer is not None:
            self.observer.context(self, time, auction, 'at_registration')
        return super().schedule_alerts(time, auction)

    def log(self, time, buyer, kind, auction=None, cause=None, visit=None, extra=None):
        result = super().log(time, buyer, kind, auction, cause, visit, extra)
        if self.observer is not None and kind == 'view':
            self.observer.actual_view(self, time, buyer, auction, cause, visit)
        return result

    def consider(self, time, buyer, auction, mode, visit):
        if self.observer is None:
            return super().consider(time, buyer, auction, mode, visit)
        context = self.observer.begin(self, time, buyer, auction, mode, visit)
        try:
            result = super().consider(time, buyer, auction, mode, visit)
        except BaseException:
            self.observer.active = None
            raise
        self.observer.finish(self, time, context)
        return result

    def outbid(self, time, buyer_id, auction, old_max):
        if self.observer is not None:
            self.observer.q(self, time, buyer_id, 'before_outbid', auction['auction_id'])
        result = super().outbid(time, buyer_id, auction, old_max)
        if self.observer is not None:
            self.observer.q(self, time, buyer_id, 'after_outbid', auction['auction_id'])
        return result

    def close(self, time, auction):
        leader = auction['leader']
        if self.observer is not None and leader is not None:
            self.observer.q(self, time, leader, 'before_settlement', auction['auction_id'])
        result = super().close(time, auction)
        if self.observer is not None and leader is not None:
            self.observer.q(self, time, leader, 'after_settlement', auction['auction_id'])
        return result


def simulate(world, end_times, seed, close_rule='hard', *, observer=True):
    return Market(world, end_times, seed, close_rule, observer=observer).run()
