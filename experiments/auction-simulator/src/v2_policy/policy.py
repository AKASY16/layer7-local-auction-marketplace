"""Point-in-time port of user report sections4.4-4.7, not an optimal policy.

Only detached public listing snapshots and declared priors enter this module.
No simulator, World, buyer, WTP, future listing or outcome access is available.
"""
import hashlib
import math

ITEM_FIELDS={'item_id','category','subcategory','series'}

def uniform(seed,purpose,aid):
    raw=hashlib.sha256(f'v2c-policy-v1|{seed}|{purpose}|{aid}'.encode()).digest()
    return int.from_bytes(raw[:8],'big')/2**64

def similarity(a,b,weights):
    if a['category']!=b['category']:return 0.
    if a['series']==b['series']:return weights['same_series']
    if a['subcategory']==b['subcategory']:return weights['same_subcategory']
    return weights['same_category']

def activity60(t,prior,origin_minute=0):
    if len(prior)!=24 or any(not math.isfinite(x) or x<=0 for x in prior):
        raise ValueError('Declared activity prior must have24 finite positive values')
    left=t-60.;value=0.
    while left<t-1e-9:
        clock=origin_minute+left
        stop=min(t,left+(60.-clock%60))
        value+=(stop-left)*prior[int(clock//60)%24]
        left=stop
    return value/60.

def rank(row,kind):
    # pi unspecified in source: explicit lexicographic night avoidance.
    main=-row['conflict'] if kind=='conservative' else row['score']
    return (-int(row['night']),main,float('inf') if row['nearest_min'] is None else row['nearest_min'],-row['end'])

def recommend(item,t0,book,prior,weights,kind,origin_minute=0):
    if set(item)!=ITEM_FIELDS:raise ValueError('Only declared public item fields allowed')
    if kind not in ('conservative','activity'):raise ValueError(kind)
    visible=[x for x in book if x['registered_at']<=t0 and x['end']>t0 and x['item']['item_id']!=item['item_id']]
    for x in visible:
        if set(x['item'])!=ITEM_FIELDS:raise ValueError('Hidden competitor information')
    competitors=[(x,similarity(item,x['item'],weights)) for x in visible]
    rows=[]
    for k in range(97):
        t=t0+1440.+30*k
        eligible=[(x,s) for x,s in competitors if s>0]
        contributors=[(x,s*(1-abs(x['end']-t)/60.)) for x,s in eligible if abs(x['end']-t)<60.]
        c=sum(weight for _,weight in contributors)
        a=activity60(t,prior,origin_minute)
        nearest=min([abs(x['end']-t) for x,s in eligible],default=None)
        rows.append(dict(end=t,duration_hours=(t-t0)/60.,night=int((origin_minute+t)//60)%24<5,
            activity=a,conflict=c,score=math.log(a)-math.log1p(c),nearest_min=nearest,
            competitor_ids=[x['auction_id'] for x,_ in contributors]))
    chosen=[]
    groups=[rows] if kind=='activity' else [[r for r in rows if low<=r['duration_hours'] and
        (r['duration_hours']<high or high==72 and r['duration_hours']<=high)] for low,high in ((24,40),(40,56),(56,72))]
    for group in groups:
        for row in sorted(group,key=lambda x:rank(x,kind),reverse=True):
            if all(abs(row['end']-r['end'])>=180.-1e-8 for r in chosen):
                chosen.append(row)
                if kind=='conservative' or len(chosen)==3:break
        if kind=='activity':break
    return [dict(r,display_rank=i+1) for i,r in enumerate(chosen)]

def select(top,manual,kind,choice='closest'):
    if not top:raise ValueError('No valid recommendation')
    if choice=='closest':return min(top,key=lambda r:(abs(r['end']-manual),r['end']))
    if choice=='best':return max(top,key=lambda r:rank(r,kind))
    raise ValueError(choice)

def schedules(auctions,items,seed,prior,weights,policy,*,adoption=1.,choice='closest',origin_minute=0):
    """Immediate sequential registration; future listings never enter book."""
    ids=sorted(a['auction_id'] for a in auctions)
    chosen=set(sorted(ids,key=lambda i:(uniform(seed,'adoption',i),i))[:int(len(ids)*adoption+1e-8)])
    book=[];ends={};trace=[];contexts=[]
    for a in sorted(auctions,key=lambda x:(x['start_at'],x['auction_id'])):
        aid=a['auction_id'];t0=a['start_at'];manual=a['default_end_at']
        public={k:items[a['item_id']][k] for k in ITEM_FIELDS}
        selected=policy!='manual' and aid in chosen
        if not selected:end=manual
        elif policy=='uniform_valid':end=t0+1440.+30*int(uniform(seed,'uniform_end',aid)*97)
        elif policy=='fixed48h':end=t0+2880.
        else:
            top=recommend(public,t0,book,prior,weights,policy,origin_minute)
            picked=select(top,manual,policy,choice)
            end=picked['end']
            for row in top:trace.append(dict(auction_id=aid,t0=t0,**row,selected=row['end']==end))
        assert t0+1440.-1e-8<=end<=t0+4320.+1e-8
        visible=[x for x in book if x['registered_at']<=t0 and x['end']>t0]
        series=[x for x in visible if x['item']['category']==public['category'] and x['item']['series']==public['series']]
        contexts.append(dict(auction_id=aid,adopted=selected,known_series_supply=len(series),
            known_series_near_manual=sum(abs(x['end']-manual)<=60. for x in series),
            known_series_near_chosen=sum(abs(x['end']-end)<=60. for x in series)))
        ends[aid]=end
        book.append(dict(auction_id=aid,registered_at=t0,end=end,item=public))
    return ends,trace,contexts
