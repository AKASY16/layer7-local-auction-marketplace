"""Frozen design. Scenario conditions change, not simulator source/parameters files."""
import copy
import numpy as np

MAIN=['manual','uniform_valid','fixed48h','conservative','activity']
REC=['manual','conservative','activity']

def jobs():
    result=[]
    def add(family,scenarios,seeds,policies,**settings):
        for s in scenarios:
            for seed in seeds:result.append(dict(family=family,scenario=s,seed=seed,policies=policies,**settings))
    add('nominal','ABCDEF',range(1,6),MAIN)
    for profile in ('day','night','weak','flat'):
        add('activity_'+profile,'ABCDEF',range(1,4),MAIN,profile=profile)
    add('uptake20','BCDF',range(1,4),REC,adoption=.2)
    add('choice_best','BCDF',range(1,4),REC,choice='best')
    add('substitution_zero','BCF',range(1,4),REC,substitution='zero')
    add('substitution_high','BF',range(1,4),REC,substitution='high')
    for model in ('known-surplus-v1','known-surplus-followup-v1'):
        add('model_'+model,'BCF',range(1,4),REC,model=model)
    for profile in ('day','night'):
        add('aligned_'+profile,'BCDF',range(1,4),['manual','activity'],profile=profile,aligned=True)
    assert sum(len(j['policies']) for j in result)==729
    assert sum(len(j['policies']) for j in result if j['family']=='nominal' or j['seed']==1)==343
    return result

def varied_world(w,profile):
    clone=copy.deepcopy(w)
    base=w.buyer_hour_profile
    v={'base':base,'day':np.roll(base,-7),'night':np.roll(base,6),'weak':.3*base+.7,'flat':np.ones(24)}[profile]
    assert abs(v.mean()-1)<1e-10 and v.max()<=base.max()+1e-10
    clone.buyer_hour_profile=v.copy()
    # Metadata only; do not regenerate sellers/buyers/candidates or their caps.
    clone.cfg=copy.deepcopy(w.cfg)
    if profile!='base':clone.cfg['v2c_activity_override']=profile
    for a,b in zip(w.buyers,clone.buyers):
        for k in ('cand_t','cand_u'):assert np.array_equal(a[k],b[k])
        assert a['budget']==b['budget'] and a['cap_rate_per_min']==b['cap_rate_per_min']
    return clone
