"""Three surgical extensions; no recalibration or new collision preference.

Standing proxy commitments can settle after leave_at. A NEW buyer event cannot
occur outside [join_at, leave_at). Availability within that interval is still
the baseline's ASSUMED hourly rule, including its session exemption.
"""
import market_simulator as baseline


class Market(baseline.Market):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rejected_inactive_events = []

    def push(self, t, kind, payload):
        if kind in (baseline.VISIT, baseline.ALERT, baseline.RETURN, baseline.SNIPE):
            buyer = self.buyers[payload[0]]
            if not buyer['join_at'] <= t < buyer['leave_at']:
                self.rejected_inactive_events.append({'time': t, 'kind': kind, 'buyer_id': payload[0]})
                return
        super().push(t, kind, payload)

    def thickness(self, b, t):
        # cat_open is maintained by the original LIST/CLOSE event handlers.
        # Use the live end, so optional soft extensions cannot leave stale ends.
        win = self.p['thickness_window_hours'] * 60
        n = sum(weight * sum(self.auc[aid]['start_at'] <= t < self.auc[aid]['end'] <= t + win
                             for aid in self.cat_open[category])
                for category, weight in b['interest'].items())
        multiplier = ((n + 1.) / (self.p['thickness_reference_count'] + 1.)) ** self.p['thickness_elasticity']
        return min(max(multiplier, self.p['thickness_multiplier_min']), self.p['thickness_multiplier_max']), n


def simulate(world, end_times, seed, close_rule='hard'):
    return Market(world, end_times, seed, close_rule).run()
