"""Fixed experiment registry; no policy outcomes used in design."""
import json
from pathlib import Path
import numpy as np
from v2_policy_empirical.activity import normalize,shift,old_weekly

ROOT=Path(__file__).resolve().parents[2]
PROFILES=ROOT/'research/activity_20261031/retailrocket_analysis/profiles.json'

def jobs(scenario,seed,w):
    p=json.loads(PROFILES.read_text(encoding='utf-8'));profiles=p['profiles']
    train=np.array(profiles['unique_active']['train']);actual=np.array(profiles['unique_active']['evaluation'])
    result=[]
    def add(name,prior=train,real=actual,**kw):
        result.append(dict(name=name,prior=prior.tolist(),actual=real.tolist(),adoption=1.,
                           availability='weekly',normalization='window',decoupled=False,**kw))
    add('lagged')
    if seed>3:return result
    add('aligned',prior=actual)
    add('old_control',prior=np.tile(w.buyer_hour_profile,(7,1)),real=normalize(old_weekly(w)))
    add('flat',prior=np.ones((7,24)),real=np.ones((7,24)))
    if scenario in 'BCDF':
        for off in (-6,-3,3,6,12):add(f'input_error_{off:+d}',prior=shift(train,off),offset=off)
        add('adoption20',**{'adoption_fraction':.2})
        add('decoupled',**{'seller_decoupled':True})
    if scenario in 'BCF':
        for off in (3,6,9,12,15,18,21):add(f'phase_{off:02}',prior=shift(train,off),real=shift(actual,off),offset=off)
        add('weak_peak',prior=.5*train+.5,real=.5*actual+.5)
        weeks=p['weekly_counts']['unique_active']['evaluation']
        for i,values in enumerate(weeks):add(f'eval_week_{i}',real=normalize(values),evaluation_week=i)
        add('views_prior',prior=np.array(profiles['views']['train']))
        add('transactions_prior',prior=np.array(profiles['transactions']['train']))
        filt=profiles['unique_active_exclude_training_top01']
        add('exclude_heavy',prior=np.array(filt['train']),real=np.array(filt['evaluation']))
        add('frozen_availability',**{'availability_override':'legacy'})
        add('global_normalization',**{'normalization_override':'global'})
    for j in result:
        j['adoption']=j.pop('adoption_fraction',j['adoption'])
        j['decoupled']=j.pop('seller_decoupled',j['decoupled'])
        j['availability']=j.pop('availability_override',j['availability'])
        j['normalization']=j.pop('normalization_override',j['normalization'])
        j['scenario']=scenario;j['seed']=seed
    return result
