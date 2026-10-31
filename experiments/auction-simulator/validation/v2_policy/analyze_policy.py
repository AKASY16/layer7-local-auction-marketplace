"""Seed-paired market contrasts, dependence-aware summaries and spillovers."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_policy/results'
METRICS=['revenue_per_listing','revenue_total','sold_rate','unsold_rate','bidders_mean',
         'price_sold_mean','price_sold_median','bids_total','market_participants',
         'duration_mean','revenue_over_value','end_hour_slot_HHI']

def interval(values):
    x=np.array([v for v in values if pd.notna(v)],float)
    n=len(x)
    if not n:return dict(n_seeds=0,mean=None,sd=None,low=None,high=None,positive=0,negative=0,tied=0)
    mean=float(x.mean());sd=float(x.std(ddof=1)) if n>1 else None
    margin=stats.t.ppf(.975,n-1)*sd/np.sqrt(n) if n>1 else None
    return dict(n_seeds=n,mean=mean,sd=sd,low=mean-margin if margin is not None else None,
                high=mean+margin if margin is not None else None,
                positive=int((x>0).sum()),negative=int((x<0).sum()),tied=int((x==0).sum()))

def summarize_pairs(frame):
    rows=[]
    # Same seed, then mean over configured scenarios: not18/30 independent worlds.
    for (family,policy),g in frame.groupby(['family','policy']):
        scopes={s:[s] for s in sorted(g.scenario.unique())}
        large=sorted(s for s in g.scenario.unique() if s!='F')
        if large:scopes['large_'+''.join(large)]=large
        for scope,scenarios in scopes.items():
            selected=g[g.scenario.isin(scenarios)]
            for metric in METRICS+['revenue_percent']:
                byseed=selected.groupby('seed')['delta_'+metric].mean()
                rows.append(dict(family=family,policy=policy,scope=scope,metric=metric,
                    scenarios=''.join(scenarios),**interval(byseed)))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='evaluation-2');a=ap.parse_args()
    data=json.loads((RES/f'{a.name}.json').read_text(encoding='utf-8'))
    root=ROOT/'data/experiments/v2c-20261031'/a.name
    markets=[];pairs=[];spills=[];strata=[];diagnostics=[]
    for key,policies in data['datasets'].items():
        base=policies['manual']['summary']
        manual=pd.read_csv(root/key/'manual/auctions.csv').sort_values('auction_id').reset_index(drop=True)
        for pol,record in policies.items():
            row=dict(family=record['family'],scenario=record['scenario'],seed=record['seed'],policy=pol,**record['summary'])
            markets.append(row)
            if pol=='manual':continue
            paired={**{k:row[k] for k in ('family','scenario','seed','policy')}}
            for metric in METRICS:
                value=row.get(metric);b=base.get(metric)
                paired['delta_'+metric]=value-b if value is not None and b is not None else None
            paired['delta_revenue_percent']=100*(row['revenue_total']/base['revenue_total']-1) if base['revenue_total'] else None
            pairs.append(paired)
            new=pd.read_csv(root/key/pol/'auctions.csv').sort_values('auction_id').reset_index(drop=True)
            assert np.array_equal(new.auction_id,manual.auction_id)
            assert np.array_equal(new.reference_M,manual.reference_M) and np.array_equal(new.reference_T,manual.reference_T)
            new['delta_revenue']=new.price-manual.price
            new['delta_bidders']=new.bidders-manual.bidders
            new['delta_sold']=new.sold.astype(int)-manual.sold.astype(int)
            new['outcome_changed']=(new.price.ne(manual.price)|new.bidders.ne(manual.bidders)|new.sold.ne(manual.sold)|
                new.bids.ne(manual.bids)|new.winner.fillna(-1).ne(manual.winner.fillna(-1)))
            common={k:row[k] for k in ('family','scenario','seed','policy')}
            for group,mask in [('adopted',new.adopted),('not_adopted',~new.adopted),
                               ('end_changed',new.end_changed),('end_unchanged',~new.end_changed)]:
                q=new[mask];n=len(q)
                spills.append(dict(**common,group=group,n=n,revenue_delta_sum=q.delta_revenue.sum(),
                    revenue_delta_mean=q.delta_revenue.mean() if n else None,
                    sold_delta_sum=q.delta_sold.sum(),bidders_delta_sum=q.delta_bidders.sum(),
                    outcome_changed_count=int(q.outcome_changed.sum()),
                    outcome_changed_share=float(q.outcome_changed.mean()) if n else None))
            # Exact accounting identity: selected gains do not equal market gains.
            assert abs(new.loc[new.adopted,'delta_revenue'].sum()+new.loc[~new.adopted,'delta_revenue'].sum()-
                       paired['delta_revenue_total'])<1e-6
            new['M_bin']=pd.cut(new.reference_M,[-.5,.5,2.5,float('inf')],labels=['0','1-2','3+'])
            new['T_bin']=np.where(new.reference_T.eq(0),'0','1+')
            for (mb,tb),q in new.groupby(['M_bin','T_bin'],observed=True):
                strata.append(dict(**common,M_bin=str(mb),T_bin=tb,n_auctions=len(q),
                    revenue_delta=q.delta_revenue.mean(),sold_delta=q.delta_sold.mean(),bidders_delta=q.delta_bidders.mean()))
            diagnostics.append(dict(**common,future_fraction_of_realized_near=(new.future_listed_series_near.sum()/new.realized_series_near.sum()
                if new.realized_series_near.sum() else None),known_near_mean=new.known_series_near_chosen.mean(),
                realized_near_mean=new.realized_series_near.mean(),known_M_mean=new.known_series_supply.mean(),
                zero_known_series_near_count=int((new.adopted&new.known_series_near_chosen.eq(0)).sum()),
                future_series_near_despite_zero_known=int((new.adopted&new.known_series_near_chosen.eq(0)&new.future_listed_series_near.gt(0)).sum()),
                duration_delta=new.duration_hours.mean()-manual.duration_hours.mean(),
                clock_hour_HHI=sum((c/len(new))**2 for c in new.end.floordiv(60).mod(24).value_counts()),
                price_sold_n=int(new.sold.sum())))
    frame=pd.DataFrame(markets);paired=pd.DataFrame(pairs)
    frame.to_csv(RES/'market_metrics.csv',index=False);paired.to_csv(RES/'paired_market_differences.csv',index=False)
    # Matched1-3 nominal subset for profile comparisons; no new simulation/outcome selection.
    matched=paired[paired.family.eq('nominal')&paired.seed.le(3)].copy();matched['family']='nominal_matched3'
    allpairs=pd.concat([paired,matched],ignore_index=True)
    summarize_pairs(allpairs).to_csv(RES/'seed_uncertainty.csv',index=False)
    pd.DataFrame(spills).to_csv(RES/'spillovers.csv',index=False)
    st=pd.DataFrame(strata);st.to_csv(RES/'supply_proximity_strata.csv',index=False)
    ss=[]
    for keys,g in st.groupby(['family','scenario','policy','M_bin','T_bin']):
        for metric in ('revenue_delta','sold_delta','bidders_delta'):
            ss.append(dict(zip(['family','scenario','policy','M_bin','T_bin'],keys),metric=metric,
                total_auction_support=int(g.n_auctions.sum()),**interval(g[metric])))
    pd.DataFrame(ss).to_csv(RES/'strata_seed_uncertainty.csv',index=False)
    pd.DataFrame(diagnostics).to_csv(RES/'exposure_and_future_supply.csv',index=False)
    # In the main sensitivity the recommender must NOT change with actual activity.
    invariant=[];engine_invariant=[]
    for key,policies in data['datasets'].items():
        if not key.startswith(('activity_','substitution_','model_')):continue
        _,s,seed=key.split('/')
        baseline=data['datasets'][f'nominal/{s}/{seed}']
        for pol,r in policies.items():
            exact=r['schedule_sha256']==baseline[pol]['schedule_sha256']
            assert exact
            row=dict(case=key,policy=pol,fixed_prior_schedule_exact=exact)
            if key.startswith('activity_'):invariant.append(row)
            else:engine_invariant.append(row)
    (RES/'information_and_schedule_checks.json').write_text(json.dumps(dict(
        fixed_prior_profile_changes=len(invariant),buyer_engine_changes=len(engine_invariant),all_exact=True,
        checks=invariant,engine_checks=engine_invariant),indent=2),encoding='utf-8')
    # Automated conservative application of preregistered criteria. Sensitivities
    # without allA-E use their PREDEFINED configured large-market scope.
    uncertainty=pd.read_csv(RES/'seed_uncertainty.csv')
    verdict={}
    for pol in ('conservative','activity'):
        q=uncertainty[uncertainty.policy.eq(pol)]
        nominal=q[q.family.eq('nominal')&q.scope.eq('large_ABCDE')].set_index('metric')
        supported=nominal.loc['revenue_per_listing','low']>0
        nominal_harm=any(nominal.loc[k,'high']<0 for k in ('sold_rate','bidders_mean'))
        stress=q[q.scope.str.startswith('large_')&~q.family.isin(['nominal','nominal_matched3'])]
        adverse=stress[(stress.metric.eq('revenue_per_listing')&stress['mean'].lt(0))|
                       (stress.metric.isin(['sold_rate','bidders_mean'])&stress.high.lt(0))]
        # A matched-seed display subset, privileged aligned prior or unadopted
        # buyer model cannot be the sole positive evidence for recommendation.
        eligible=~q.family.eq('nominal_matched3')&~q.family.str.startswith(('aligned_','model_'))
        clear_positive=q[eligible&q.metric.eq('revenue_per_listing')&q.scope.str.startswith('large_')&q.low.gt(0)]
        decision='조건부 추천' if supported and not nominal_harm and adverse.empty else '제한적 추천' if len(clear_positive) else '자동 추천 보류'
        verdict[pol]=dict(simulation_verdict=decision,nominal_revenue_supported=bool(supported),
            nominal_secondary_harm=bool(nominal_harm),adverse_stress_cells=adverse[['family','metric','mean','low','high']].to_dict('records'),
            clear_positive_conditions=clear_positive[['family','scope','mean','low','high']].to_dict('records'),
            live_market_effect='UNVERIFIED; no causal validation; activity/seller uptake ASSUMED',
            production_auto_optimization='HOLD without observed/validated applicable conditions')
    (RES/'verdict.json').write_text(json.dumps(verdict,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('ANALYZED',len(frame),'markets',len(paired),'contrasts, exact fixed-prior schedules',len(invariant))
    print(json.dumps({k:v['simulation_verdict'] for k,v in verdict.items()},ensure_ascii=False))

if __name__=='__main__':main()
