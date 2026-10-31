"""Market estimands; prices conditional on sale never substitute for revenue."""
from collections import Counter
import numpy as np

def auction_rows(m,w,ends,contexts):
    context={r['auction_id']:r for r in contexts}
    items={r['item_id']:r for r in w.items}
    rows=[]
    for aid,a in sorted(m.auc.items()):
        sold=a['leader'] is not None
        it=items[a['item_id']]
        assert context[aid]['auction_id']==aid
        rows.append(dict(start=a['start_at'],manual_end=a['default_end_at'],end=ends[aid],
            duration_hours=(ends[aid]-a['start_at'])/60.,sold=sold,price=a['price'] if sold else 0.,
            bidders=len(a['bidders']),bids=a['n_bids'],winner=a['leader'],
            value=it['estimated_value'],category=a['category'],series=it['series'],
            end_changed=abs(ends[aid]-a['default_end_at'])>1e-8,**context[aid]))
    return rows

def summary(rows,m):
    n=len(rows);sold=[r for r in rows if r['sold']]
    prices=np.array([r['price'] for r in sold])
    slots=Counter(int(r['end']//60) for r in rows)
    return dict(n_auctions=n,revenue_total=sum(r['price'] for r in rows),
        revenue_per_listing=sum(r['price'] for r in rows)/n,sold_rate=len(sold)/n,unsold_rate=1-len(sold)/n,
        bidders_mean=sum(r['bidders'] for r in rows)/n,
        price_sold_mean=float(prices.mean()) if len(prices) else None,
        price_sold_median=float(np.median(prices)) if len(prices) else None,
        bids_total=len(m.bids),market_participants=len({b['buyer_id'] for b in m.bids}),
        duration_mean=np.mean([r['duration_hours'] for r in rows]),
        revenue_over_value=np.mean([r['price']/r['value'] for r in rows]),
        end_hour_slot_HHI=sum((v/n)**2 for v in slots.values()),
        changed_count=sum(r['end_changed'] for r in rows))
