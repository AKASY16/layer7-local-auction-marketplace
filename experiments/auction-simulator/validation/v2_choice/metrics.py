"""Observable units only; no WTP fitting or raw USD/KRW price-level comparison."""
import math
from collections import Counter, defaultdict
import numpy as np


def summaries(m):
    auctions=list(m.auc.values())
    bids=m.bids
    pairs=Counter((r['auction_id'],r['buyer_id']) for r in bids)
    positive=[a for a in auctions if a['n_bids']>0]
    sold=[a for a in auctions if a['leader'] is not None]
    bybuyer=defaultdict(list)
    for i,r in enumerate(bids):bybuyer[r['buyer_id']].append((r['bid_time'],r['auction_id'],i))
    transitions=switches=open_switches=ties=multi=0
    for rows in bybuyer.values():
        rows.sort(key=lambda x:(x[0],x[1]))  # same convention as A-01 supplied analysis
        multi+=len({r[1] for r in rows})>=2
        for previous,current in zip(rows,rows[1:]):
            transitions+=1
            ties+=previous[0]==current[0]
            if previous[1]!=current[1]:
                switches+=1
                open_switches+=current[0]<m.auc[previous[1]]['actual_end_at']
    n=len(auctions)
    out={'n_auctions':n,'n_bids':len(bids),'n_bidder_auction_pairs':len(pairs),'n_participants':len(bybuyer),
         'bidders_mean_pos':float(np.mean([len(a['bidders']) for a in positive])) if positive else None,
         'bids_per_pair':len(bids)/len(pairs) if pairs else None,
         'repeat_pair_share':sum(v>=2 for v in pairs.values())/len(pairs) if pairs else None,
         'sold_rate':len(sold)/n if n else None,
         'multi_auction_bidder_share':multi/len(bybuyer) if bybuyer else None,
         'switch_rate':switches/transitions if transitions else None,
         'open_switch_share':open_switches/switches if switches else None,
         'same_time_transition_share':ties/transitions if transitions else None}
    # Duration-matched eBay J&S 3-day reference: positive-bid, exactly72h.
    d3=[a for a in auctions if abs((a['scheduled_end_at']-a['start_at'])-4320.)<1e-6 and a['n_bids']>0]
    ids={a['auction_id'] for a in d3}
    p3=Counter((r['auction_id'],r['buyer_id']) for r in bids if r['auction_id'] in ids)
    out.update(js3_n_positive=len(d3),js3_n_pairs=len(p3),
               js3_bidders_mean_pos=float(np.mean([len(a['bidders']) for a in d3])) if d3 else None,
               js3_bids_per_pair=sum(p3.values())/len(p3) if p3 else None,
               js3_repeat_pair_share=sum(v>=2 for v in p3.values())/len(p3) if p3 else None)
    # Shared B03/B04 family: same new condition and [24,72] hour RANGE only.
    matched=[a for a in auctions if m.items[a['item_id']]['condition']=='new'
             and 1440.-1e-6<=a['scheduled_end_at']-a['start_at']<=4320.+1e-6]
    prices=[a['price'] for a in matched if a['leader'] is not None]
    out.update(b04_n_matched=len(matched),
               b04_bidders_mean=float(np.mean([len(a['bidders']) for a in matched])) if matched else None,
               b04_sold_rate=float(np.mean([a['leader'] is not None for a in matched])) if matched else None,
               b04_sold_log_price_sd=float(np.std(np.log(prices),ddof=1)) if len(prices)>1 else None)
    for c in m.w.categories:
        prices=[a['price'] for a in sold if a['category']==c]
        out['log_price_sd_'+c]=float(np.std(np.log(prices),ddof=1)) if len(prices)>1 else None
    return out


def exact_invariants(m):
    events=m.events
    assert all(x['event_time']<=y['event_time'] for x,y in zip(events,events[1:]))
    for r in events:
        b=m.buyers[r['buyer_id']]
        assert b['join_at']<=r['event_time']<b['leave_at']
    views={(r['buyer_id'],r['auction_id']) for r in events if r['event_type']=='view'}
    assert set(m.wtp_log).issubset(views)
    for r in m.bids:
        a=m.auc[r['auction_id']]
        assert a['start_at']<=r['bid_time']<=a['actual_end_at']
        assert r['bid_amount']<=m.wtp_log[(r['buyer_id'],r['auction_id'])]+1e-8
    for bid,st in m.state.items():
        won=[a for a in m.auc.values() if a['leader']==bid]
        assert set(st['won'])=={a['auction_id'] for a in won}
        assert not st['leading'] and abs(st['committed'])<1e-8
        assert abs(st['spent']-sum(a['price'] for a in won))<1e-8
        assert st['spent']<=m.buyers[bid]['budget']+1e-8
    if hasattr(m,'_knowledge'):
        assert set(m.wtp_log)==views
        for bid,known in m._knowledge.items():
            for aid,q in known.items():
                assert (bid,aid) in views and q['source'] in ('view','own_bid_feedback')
                assert q['wtp']==m.wtp_log[(bid,aid)]
    return {'all_pass':True,'view_pairs':len(views),'bid_caps_checked':len(m.bids),
            'settlements_checked':sum(a['leader'] is not None for a in m.auc.values())}
