"""Clean feature ablation; public point-in-time listing data and declared prior only."""
import math
import numpy as np
from v2_policy.policy import ITEM_FIELDS,similarity,uniform
from .activity import Curve

POLICIES=('manual','uniform_valid','activity_only','competition_only','combined')

def activity60(t,prior,origin):
    return Curve(prior).integral(origin+t-60,origin+t)/60

def recommend(item,t0,book,prior,weights,kind,origin):
    if set(item)!=ITEM_FIELDS:raise ValueError('Only public item fields permitted')
    if kind not in POLICIES[2:]:raise ValueError(kind)
    curve=Curve(prior)
    competitors=[]
    for x in book:
        if set(x['item'])!=ITEM_FIELDS:raise ValueError('Hidden item field')
        if x['registered_at']<=t0 and x['end']>t0 and x['item']['item_id']!=item['item_id']:
            s=similarity(item,x['item'],weights)
            if s>0:competitors.append((x,s))
    rows=[]
    for k in range(97):
        t=t0+1440+30*k
        contributing=[(x,s*(1-abs(x['end']-t)/60)) for x,s in competitors if abs(x['end']-t)<60]
        c=sum(s for _,s in contributing)
        a=curve.integral(origin+t-60,origin+t)/60
        score=(0. if kind=='competition_only' else math.log(a) if a>0 else -math.inf)
        if kind!='activity_only':score-=math.log1p(c)
        rows.append(dict(end=t,activity=a,conflict=c,score=score,
            night=int((origin+t)//60)%24<5,competitor_ids=[x['auction_id'] for x,_ in contributing]))
    top=[]
    for row in sorted(rows,key=lambda r:(r['night'],-r['score'],r['end'])):
        if all(abs(row['end']-x['end'])>=180-1e-8 for x in top):
            top.append(row)
            if len(top)==3:break
    return top

def schedules(auctions,items,seed,prior,weights,policy,origin,adoption=1.):
    if policy not in POLICIES:raise ValueError(policy)
    ids=sorted(a['auction_id'] for a in auctions)
    chosen=set(sorted(ids,key=lambda i:(uniform(seed,'adoption',i),i))[:int(len(ids)*adoption+1e-8)])
    book=[];ends={};trace=[];contexts=[]
    for a in sorted(auctions,key=lambda x:(x['start_at'],x['auction_id'])):
        aid=a['auction_id'];t0=a['start_at'];manual=a['default_end_at']
        public={k:items[a['item_id']][k] for k in ITEM_FIELDS}
        selected=policy!='manual' and aid in chosen
        if not selected:end=manual
        elif policy=='uniform_valid':end=t0+1440+30*int(uniform(seed,'uniform_end',aid)*97)
        else:
            top=recommend(public,t0,book,prior,weights,policy,origin)
            end=min(top,key=lambda r:(abs(r['end']-manual),r['end']))['end']
            for r in top:
                trace.append(dict(auction_id=aid,t0=t0,selected=r['end']==end,**r))
        assert t0+1440<=end<=t0+4320
        visible=[x for x in book if x['registered_at']<=t0 and x['end']>t0]
        series=[x for x in visible if x['item']['category']==public['category'] and x['item']['series']==public['series']]
        contexts.append(dict(auction_id=aid,adopted=selected,known_series_supply=len(series),
            known_series_near_manual=sum(abs(x['end']-manual)<=60 for x in series),
            known_series_near_chosen=sum(abs(x['end']-end)<=60 for x in series)))
        ends[aid]=end
        book.append(dict(auction_id=aid,registered_at=t0,end=end,item=public))
    return ends,trace,contexts
