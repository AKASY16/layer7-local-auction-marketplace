"""Passive history of actual views; never refresh an unviewed alternative."""


class Awareness:
    def __init__(self):
        self.known = {}

    def view(self, buyer_id, auction_id, time, quote, mode):
        known = self.known.setdefault(buyer_id, {})
        previous = known.get(auction_id)
        row = {'known_before_current_view': previous is not None,
               'known_count_before': len(known),
               'previous_seen_min': previous['last_seen_min'] if previous else None,
               'previous_minimum_acceptable': previous['minimum_acceptable'] if previous else None,
               'previous_seen_live_end_min': previous['seen_live_end_min'] if previous else None}
        # All values are detached scalars; no references to mutable market state.
        current = {'buyer_id': buyer_id, 'auction_id': auction_id,
                   'first_seen_min': previous['first_seen_min'] if previous else time,
                   'last_seen_min': time, 'mode': mode, **quote}
        known[auction_id] = current
        return {**row, **current, 'known_count_after': len(known)}

    def final_rows(self):
        return [dict(value) for buyer in sorted(self.known)
                for _, value in sorted(self.known[buyer].items())]
