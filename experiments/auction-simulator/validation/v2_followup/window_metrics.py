"""Pre-specified supplementary comparisons, never a 72h whole-auction substitute.

60<=duration<=72h uses a near-duration stratum. Last24h uses a common terminal
observation window and conditions on >=1 bid IN that window. Duration-bin
effects remain possible; no reweighting, generator edits or target fitting.
"""
from collections import Counter
from pathlib import Path
import json
import zlib
import numpy as np
import pandas as pd


def pair_stats(bids, auction_ids):
    pairs=Counter((a,b) for a,b in bids if a in auction_ids)
    positive={a for a,_ in pairs}
    return dict(n_positive=len(positive), n_pairs=len(pairs), n_bids=sum(pairs.values()),
        bidders_mean_pos=len(pairs)/len(positive) if positive else None,
        bids_per_pair=sum(pairs.values())/len(pairs) if pairs else None,
        repeat_pair_share=sum(v>=2 for v in pairs.values())/len(pairs) if pairs else None)


def model_windows(m):
    durations={i:(a['scheduled_end_at']-a['start_at'])/60 for i,a in m.auc.items()}
    near={i for i,d in durations.items() if 60-1e-8<=d<=72+1e-8}
    allpairs=[(r['auction_id'],r['buyer_id']) for r in m.bids]
    result={'near72':dict(n_auctions=len(near),**pair_stats(allpairs,near))}
    windows=[(r['auction_id'],r['buyer_id']) for r in m.bids
             if m.auc[r['auction_id']]['scheduled_end_at']-1440<=r['bid_time']
             <=m.auc[r['auction_id']]['scheduled_end_at']]
    result['terminal24']=dict(n_auctions=len(m.auc),**pair_stats(windows,set(m.auc)))
    for low,high in ((24,36),(36,48),(48,60),(60,72)):
        ids={i for i,d in durations.items() if low-1e-8<=d and (d<high-1e-8 or high==72 and d<=72+1e-8)}
        result[f'terminal24_duration_{low}_{high}']=dict(n_auctions=len(ids),**pair_stats(windows,ids))
    return result


def empirical(root):
    refs=json.loads((root/'validation/v2_choice/results/references.json').read_text(encoding='utf-8'))
    rows=[]
    for filename in refs['file_sha256']:
        if filename.endswith('.csv'):
            f=pd.read_csv(filename)
            f=f[f.auctionid.map(lambda x:zlib.crc32(str(x).encode())%1000<300)].copy()
            f['auction_key']=[(Path(filename).name,str(a)) for a in f.auctionid]
            rows.append(f)
    df=pd.concat(rows,ignore_index=True)
    allpairs=list(zip(df.auction_key,df.bidder))
    ids=set(df.auction_key)
    late=df[df.bidtime.between(2.,3.,inclusive='both')]
    return dict(whole72=pair_stats(allpairs,ids),
        terminal24=pair_stats(list(zip(late.auction_key,late.bidder)),ids),
        status='Previously known 30% holdout; terminal window conditioned on bids in last24h, not whole auction',
        near72_status='Reference actual72h; model60-72h APPROXIMATE only; no duration-equivalence claim')
