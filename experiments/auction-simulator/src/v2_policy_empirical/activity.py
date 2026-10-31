"""Piecewise-constant weekly activity; exogenous visit intensity only.

ASSUMED transfer of anonymous ecommerce activity shapes. Not empirical Korean
auction demand. No interpolation, WTP change or added collision preference.
"""
import copy
import hashlib
from unittest.mock import patch
import numpy as np
import world as W
from audit.simulator import Market as AuditMarket

def normalize(values):
    x=np.asarray(values,dtype=float)
    if x.shape!=(7,24) or not np.isfinite(x).all() or (x<0).any() or x.mean()<=0:
        raise ValueError('Need nonnegative finite 7x24 activity with positive total')
    return x/x.mean()

def shift(values,hours):
    return np.roll(np.asarray(values).reshape(168),int(hours)).reshape(7,24)

def old_weekly(w):
    out=np.tile(w.buyer_hour_profile,(7,1)).copy()
    out[5:]*=w.cfg['params']['weekend_activity_factor']
    return out

def week_origin(w):
    return w.origin.weekday()*1440+w.origin.hour*60+w.origin.minute

class Curve:
    def __init__(self,values):
        self.values=np.asarray(values,float)
        if self.values.shape!=(7,24) or not np.isfinite(self.values).all() or (self.values<0).any():
            raise ValueError('Invalid weekly activity')
        self.by_offset={i:np.roll(self.values,i,axis=1).ravel() for i in range(-6,7)}
        self.prefix={i:np.r_[0.,np.cumsum(v)*60.] for i,v in self.by_offset.items()}
    def primitive(self,t,offset=0):
        v=self.by_offset[offset];p=self.prefix[offset]
        cycles=int(t//10080);r=t-cycles*10080;h=min(167,int(r//60))
        return cycles*p[-1]+p[h]+(r-h*60)*v[h]
    def integral(self,start,end,offset=0):
        return self.primitive(end,offset)-self.primitive(start,offset)
    def peak(self,start,end,offset=0):
        v=self.by_offset[offset]
        if end-start>=10080:return float(v.max())
        first=int(start//60);last=int(np.nextafter(end,-np.inf)//60)
        return float(v[np.arange(first,last+1)%168].max())

def adjustments(w,values,normalization='window'):
    new=Curve(values);old=Curve(old_weekly(w));origin=week_origin(w)
    out={}
    for b in w.buyers:
        off=int(round(b['hour_offset']));lo=origin+b['join_at'];hi=origin+b['leave_at']
        j=old.integral(lo,hi,off);i=new.integral(lo,hi,off)
        if i<=0 and j>0:raise ValueError('No activity in a buyer window; no smoothing allowed')
        alpha=j/i if normalization=='window' else float(old.values.mean())
        out[b['buyer_id']]=(alpha,i,j,new.peak(lo,hi,off))
    return out

def captured_world(cfg,seed):
    """Record original end generation without consuming a single extra draw."""
    calls=[];parent=W._default_end
    def capture(w,start,dur,pref,rng):
        calls.append((start,dur,pref,copy.deepcopy(rng.bit_generator.state)))
        return parent(w,start,dur,pref,rng)
    with patch.object(W,'_default_end',capture):w=W.build(cfg,seed)
    assert len(calls)==len(w.auctions)
    return w,calls

def coupled_calendar(w,calls,values,seed,decoupled=False):
    """Preserve original ASSUMED follow/crowded supply-generation rule.

    Reuse nominal durations and exact jitter draws. Change no item/buyer trait.
    Conditional seller CDF ranks are auxiliary exogenous random variables.
    """
    out=copy.copy(w)
    demand=np.asarray(values).mean(axis=0)
    mode='uniform' if decoupled else w.cfg['seller_end_hour_mode']
    target=W._supply_profile(demand,mode,w.cfg['params']['supply_peak_ratio'])
    before=np.r_[0.,np.cumsum(w.seller_end_profile)]
    after=np.cumsum(target);after[-1]=1.
    out.sellers=[];hours={}
    for s in w.sellers:
        h=s['preferred_end_hour'];sid=s['seller_id']
        u=int.from_bytes(hashlib.sha256(f'v2rr-seller-rank|{seed}|{sid}'.encode()).digest()[:8],'big')/2**64
        rank=before[h]+u*(before[h+1]-before[h])
        nh=min(23,int(np.searchsorted(after,rank,side='right')))
        hours[sid]=nh;out.sellers.append(dict(s,preferred_end_hour=nh))
    out.seller_end_profile=target
    out.auctions=[]
    for a,(start,dur,pref,state) in zip(w.auctions,calls):
        assert start==a['start_at']
        rng=np.random.default_rng();rng.bit_generator.state=copy.deepcopy(state)
        end=W._default_end(w,start,dur,hours[a['seller_id']],rng)
        out.auctions.append(dict(a,default_end_at=end))
    return out

def master_proposals(w,conditions,seed):
    """One dominating Poisson pool shared by every condition and policy.

    Conditions contain only preregistered actual activity + normalization.
    The pool does not expose future curves to the recommender.
    """
    bounds={b['buyer_id']:b['cap_rate_per_min'] for b in w.buyers}
    for values,norm in conditions:
        adj=adjustments(w,values,norm)
        for b in w.buyers:
            alpha,_,_,peak=adj[b['buyer_id']]
            cap=b['visit_rate_per_day']/1440*alpha*peak*w.cfg['params']['thickness_multiplier_max']
            bounds[b['buyer_id']]=max(bounds[b['buyer_id']],cap)
    out=copy.copy(w);out.buyers=[]
    for b in w.buyers:
        cap=np.nextafter(bounds[b['buyer_id']],np.inf)
        rng=np.random.default_rng(np.random.SeedSequence([20261031,731,seed,b['buyer_id']]))
        n=rng.poisson(cap*(b['leave_at']-b['join_at']))
        times=np.sort(rng.uniform(b['join_at'],b['leave_at'],n));uniforms=rng.random(n)
        out.buyers.append(dict(b,cap_rate_per_min=cap,cand_t=times,cand_u=uniforms))
    return out

class Market(AuditMarket):
    def __init__(self,w,ends,seed,values,normalization='window',availability='weekly'):
        super().__init__(w,ends,seed)
        self.activity_values=np.asarray(values,float).copy()
        self.activity_adjustments=adjustments(w,values,normalization)
        self.activity_availability=availability
        self.activity_organic=False
        self.activity_legacy_peak=self.avail_norm
        if availability=='weekly':self.avail_norm=float(self.activity_values[:5].max())
        if self.avail_norm<=0:raise ValueError('No weekday availability; unsupported')
        self.activity_max_cap_ratio=0.
        for b in w.buyers:
            alpha,_,_,peak=self.activity_adjustments[b['buyer_id']]
            ratio=b['visit_rate_per_day']/1440*alpha*peak*self.p['thickness_multiplier_max']/b['cap_rate_per_min']
            if ratio>1+1e-12:raise ValueError('Candidate cap would truncate intensity')
            self.activity_max_cap_ratio=max(self.activity_max_cap_ratio,ratio)
    def hour_weight(self,b,t):
        if not self.activity_organic and self.activity_availability=='legacy':
            return super().hour_weight(b,t)
        h=(self.w.hour_of(t)-int(round(b['hour_offset'])))%24
        return float(self.activity_values[self.w.dow_of(t),h])
    def visit(self,t,b,cand_index):
        alpha=self.activity_adjustments[b['buyer_id']][0]
        adjusted=dict(b,visit_rate_per_day=b['visit_rate_per_day']*alpha)
        self.activity_organic=True
        try:return super().visit(t,adjusted,cand_index)
        finally:self.activity_organic=False

def expected_visits(m):
    base=adjusted=0.
    for b in m.w.buyers:
        alpha,i,j,_=m.activity_adjustments[b['buyer_id']]
        base+=b['visit_rate_per_day']/1440*j
        adjusted+=b['visit_rate_per_day']/1440*alpha*i
    return dict(expected_exogenous_legacy=base,expected_exogenous_new=adjusted,
                expected_ratio=adjusted/base if base else None,
                maximum_bound_ratio=m.activity_max_cap_ratio)
