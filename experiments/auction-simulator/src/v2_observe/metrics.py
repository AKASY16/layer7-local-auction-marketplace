"""Read-only N/M/T measurements. No RNG, WTP, queue, or defaultdict writes."""

WINDOW_HOURS = (1, 3, 6, 12, 24)
CATALOG_FIELDS = ('category', 'subcategory', 'series', 'condition', 'rarity')


def participation(market, buyer, time):
    window = market.p['thickness_window_hours'] * 60
    n = sum(weight * sum(market.auc[aid]['start_at'] <= time < market.auc[aid]['end'] <= time + window
                         and not market.auc[aid]['closed']
                         for aid in market.cat_open.get(category, ()))
            for category, weight in buyer['interest'].items())
    p = market.p
    multiplier = ((n + 1.) / (p['thickness_reference_count'] + 1.)) ** p['thickness_elasticity']
    multiplier = min(max(multiplier, p['thickness_multiplier_min']), p['thickness_multiplier_max'])
    attention = ((n + 1.) / (p['thickness_reference_count'] + 1.)) ** p['attention_thickness_elasticity']
    return {'N_near_end_count': n, 'participation_multiplier': multiplier,
            'attention_multiplier': min(max(attention, .5), 4.),
            'window_hours': p['thickness_window_hours']}


def catalog_key(item):
    """A synthetic attribute proxy, NOT a verified SKU or B-04 product identity."""
    values = tuple(item.get(k) for k in CATALOG_FIELDS)
    return values if all(v is not None for v in values) else None


class SupplyMetrics:
    def __init__(self):
        # Only immutable item relations are cached, never open/end-time state.
        self.relations = {}

    def relation(self, market, left, right):
        key = (left, right)
        if key not in self.relations:
            a, b = market.items[left], market.items[right]
            if a['category'] != b['category']:
                similarity = 0.
            elif a['series'] == b['series']:
                similarity = market.sim_series
            elif a['subcategory'] == b['subcategory']:
                similarity = market.sim_sub
            else:
                similarity = market.sim_cat
            ca, cb = catalog_key(a), catalog_key(b)
            self.relations[key] = (similarity, ca == cb if ca is not None and cb is not None else None)
        return self.relations[key]

    def measure(self, market, time, auction_id):
        a = market.auc[auction_id]
        valid_proxy = catalog_key(market.items[a['item_id']]) is not None
        out = {'M_similarity_weighted': 0., 'M_positive_similarity_count': 0,
               'M_catalog_proxy_count': 0 if valid_proxy else None,
               'scheduled_end_min': a['scheduled_end_at'], 'live_end_min': a['end']}
        for h in WINDOW_HOURS:
            for clock in ('live', 'scheduled'):
                out[f'T_{clock}_{h}h_weighted'] = 0.
                out[f'T_{clock}_{h}h_catalog_proxy_count'] = 0 if valid_proxy else None
        for aid in sorted(market.cat_open.get(a['category'], ())):
            other = market.auc[aid]
            if aid == auction_id or other['closed'] or not other['start_at'] <= time < other['end']:
                continue
            similarity, same_proxy = self.relation(market, a['item_id'], other['item_id'])
            out['M_similarity_weighted'] += similarity
            out['M_positive_similarity_count'] += int(similarity > 0)
            if valid_proxy:
                # An unknown competitor identity makes this count unknown.
                if same_proxy is None:
                    out['M_catalog_proxy_count'] = None
                elif out['M_catalog_proxy_count'] is not None:
                    out['M_catalog_proxy_count'] += int(same_proxy)
            for clock, field in (('live', 'end'), ('scheduled', 'scheduled_end_at')):
                gap = abs(other[field] - a[field])
                for h in WINDOW_HOURS:
                    if gap <= h * 60:
                        out[f'T_{clock}_{h}h_weighted'] += similarity
                        name = f'T_{clock}_{h}h_catalog_proxy_count'
                        if same_proxy is None:
                            out[name] = None
                        elif out[name] is not None:
                            out[name] += int(same_proxy)
        return out
