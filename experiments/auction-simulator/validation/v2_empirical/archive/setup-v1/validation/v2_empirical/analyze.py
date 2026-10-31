"""Seed-paired inference. Auction rows are never independent inferential units."""
import argparse
import json
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'data/experiments/v2c-retailrocket-20261031'

def interval(values):
    x=np.array(values,float);n=len(x);mean=float(x.mean())
    half=float(t.ppf(.975,n-1)*x.std(ddof=1)/np.sqrt(n)) if n>1 else None
    return dict(n_seed=n,mean=mean,lo=mean-half if half is not None else None,hi=mean+half if half is not None else None,
                positive_seeds=int((x>0).sum()),negative_seeds=int((x<0).sum()))

def analyze(name,out):
    if out.exists():raise FileExistsError('Analysis outputs immutable; use fresh directory')
    out.mkdir(parents=True)
    records=[];bridges=[];regressions=[];runs=replays=0
    for path in sorted((DEST/name).glob('scenario_*/seed_*/completed.json')):
        d=json.loads(path.read_text(encoding='utf-8'));bridges+=d['bridge']
        if d['regression']:regressions.append(d['regression'])
        runs+=d['executed_simulations_this_invocation'];replays+=d['replays_this_invocation']
        for r in d['records']:
            rows=pd.read_csv(path.parent/r['condition']/f"{r['policy']}.csv")
            organic=r['visit_causes'].get('organic',0)
            rec={k:r[k] for k in ('condition','scenario','seed','policy','prior_actual_TV','replayed','repeat_required','seconds','cache_hit','cache_key')}
            rec.update(r['summary']);rec.update(r['volume'])
            rec.update(organic_visits=organic,planned_visits=sum(r['visit_causes'].values())-organic,
                mean_absolute_shift_hours=float(rows.end_shift_hours.abs().mean()),
                end_hour_mean=float(rows.end_hour.mean()),night_end_share=float((rows.end_hour<5).mean()),
                end_hour_changed_share=float((rows.end_hour!=rows.manual_hour).mean()))
            records.append(rec)
    df=pd.DataFrame(records);df.to_csv(out/'market_metrics.csv',index=False)
    metrics=['revenue_per_listing','sold_rate','unsold_rate','bidders_mean','revenue_total','duration_mean',
             'organic_visits','planned_visits','mean_absolute_shift_hours','night_end_share']
    pairs=[]
    for (condition,s,sd),group in df.groupby(['condition','scenario','seed']):
        by=group.set_index('policy')
        for baseline in ('manual','activity_only'):
            for policy in by.index:
                if policy==baseline:continue
                row=dict(condition=condition,scenario=s,seed=int(sd),policy=policy,baseline=baseline,prior_actual_TV=float(by.loc[policy,'prior_actual_TV']))
                for metric in metrics:
                    a=float(by.loc[policy,metric]);b=float(by.loc[baseline,metric])
                    row[metric]=a-b
                    row[metric+'_pct']=100*(a/b-1) if b else np.nan
                pairs.append(row)
    paired=pd.DataFrame(pairs);paired.to_csv(out/'paired_market_differences.csv',index=False)
    intervals=[]
    for keys,g in paired.groupby(['condition','scenario','policy','baseline']):
        for metric in metrics+['revenue_per_listing_pct']:
            intervals.append(dict(zip(('condition','scenario','policy','baseline'),keys),metric=metric,**interval(g[metric])))
    # Equal-scenario average WITHIN seed; no reuse of scenarios as independent markets.
    for keys,g in paired[paired.scenario.isin(list('ABCDE'))].groupby(['condition','policy','baseline']):
        expected=set(g.scenario.unique())
        by=g.groupby('seed')[metrics+['revenue_per_listing_pct']].mean()
        for metric in by:
            intervals.append(dict(zip(('condition','policy','baseline'),keys),scenario='mean_'+''.join(sorted(expected)),metric=metric,**interval(by[metric])))
    ci=pd.DataFrame(intervals);ci.to_csv(out/'seed_uncertainty.csv',index=False)
    # Within-seed heldout-week variability stays separate from inferential seed count.
    week=paired[paired.condition.str.startswith('eval_week')].copy()
    if len(week):
        week.groupby(['scenario','seed','policy','baseline']).agg(
            revenue_delta_mean=('revenue_per_listing','mean'),revenue_delta_min=('revenue_per_listing','min'),
            revenue_delta_max=('revenue_per_listing','max'),positive_weeks=('revenue_per_listing',lambda x:int((x>0).sum())),
            weeks=('condition','nunique')).reset_index().to_csv(out/'heldout_week_within_seed.csv',index=False)
    # Interference and supply strata use paired sums within a seed, not row-level tests.
    spill=[];strata=[]
    for path in sorted((DEST/name).glob('scenario_*/seed_*/completed.json')):
        d=json.loads(path.read_text(encoding='utf-8'))
        names=sorted({r['condition'] for r in d['records']})
        for cond in names:
            if cond not in ('lagged','adoption20'):continue
            folder=path.parent/cond;manual=pd.read_csv(folder/'manual.csv').set_index('auction_id')
            for policy in ('activity_only','competition_only','combined'):
                rows=pd.read_csv(folder/f'{policy}.csv').set_index('auction_id')
                assert rows.index.equals(manual.index)
                for adopted in (True,False):
                    ids=rows.index[rows.adopted==adopted]
                    if len(ids):spill.append(dict(condition=cond,scenario=d['scenario'],seed=d['seed'],policy=policy,
                        adopted=adopted,n=len(ids),revenue_delta=float((rows.loc[ids,'price']-manual.loc[ids,'price']).sum()),
                        changed_unchosen_outcomes=int(((rows.loc[ids,'price']!=manual.loc[ids,'price'])|(rows.loc[ids,'bidders']!=manual.loc[ids,'bidders'])).sum())))
                if cond=='lagged':
                    # Condition on the same manual-registration public baseline supply.
                    for dim in ('known_series_supply','known_series_near_manual'):
                        for label,mask in [('zero',manual[dim]==0),('positive',manual[dim]>0)]:
                            ids=manual.index[mask]
                            if len(ids):strata.append(dict(scenario=d['scenario'],seed=d['seed'],policy=policy,dimension=dim,stratum=label,n=len(ids),
                                revenue_delta_per_listing=float((rows.loc[ids,'price']-manual.loc[ids,'price']).mean()),
                                bidders_delta=float((rows.loc[ids,'bidders']-manual.loc[ids,'bidders']).mean())))
    pd.DataFrame(spill).to_csv(out/'spillovers.csv',index=False)
    pd.DataFrame(strata).to_csv(out/'public_supply_strata_seed.csv',index=False)
    pd.DataFrame([dict(scenario=r['scenario'],seed=r['seed'],policy=r['policy'],**r['summary']) for r in bridges]).to_csv(out/'old_policy_bridge.csv',index=False)
    checks=dict(markets=len(df),unique_market_cache_keys=int(df.cache_key.nunique()),executed_simulations=runs,replayed_unique_markets=replays,
        all_records_requiring_replay_pass=all(r['replayed'] for r in records if r['repeat_required']),legacy_worlds=len(regressions),
        legacy_all11_exact=all(r['all11_exact'] for r in regressions),
        normalization_max_error=float(np.max(np.abs(df.loc[~df.condition.eq('global_normalization'),'expected_ratio']-1))),
        maximum_cap_ratio=float(df.maximum_bound_ratio.max()),
        inference_unit='seed, with scenario averages formed within seed; no auction IID',
        scope='ASSUMED relative activity transfer; not causal Korean auction validation')
    (out/'checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();analyze(args.name,args.out)
