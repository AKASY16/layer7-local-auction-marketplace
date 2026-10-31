"""Report favorable AND unfavorable metrics; repeated buyers/auctions aren't iid."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_followup/results'


def detailed_followthrough(key,mode,flow_path,data_path):
    pairs=pd.read_csv(flow_path)
    events=pd.read_csv(data_path/'visits.csv')
    decisions=pd.read_csv(data_path/'hidden/decisions.csv')
    bids=pd.read_csv(data_path/'bids.csv')
    latent=pd.read_csv(data_path/'hidden/buyers_latent.csv').set_index('buyer_id')
    origin=pd.Timestamp('2026-11-02T00:00:00+09:00')
    events['minute']=(pd.to_datetime(events.event_time)-origin).dt.total_seconds()/60
    buyer_events={int(b):g for b,g in events.groupby('buyer_id')}
    reason={(int(r.buyer_id),int(r.visit_id),int(r.auction_id)):r.decision for r in decisions.dropna(subset=['visit_id']).itertuples()}
    submitted={(int(r.buyer_id),int(r.visit_id),int(r.auction_id)) for r in bids.dropna(subset=['visit_id']).itertuples()}
    planned={}
    for r in decisions[decisions.decision.isin(['snipe_scheduled','snipe_planned_unavailable'])].dropna(subset=['visit_id']).itertuples():
        k=(int(r.buyer_id),int(r.auction_id))
        planned[k]=min(planned.get(k,float('inf')),int(r.visit_id))
    rows=[]
    for r in pairs.itertuples():
        f=buyer_events[r.buyer_id]
        # Original event order, not rounded timestamp sorting. Only the deadline
        # uses exported timestamps (one-second precision), disclosed in report.
        f=f[(f.index>=r.event_ordinal)&(f.minute<r.window_end)]
        viewed=f[f.event_type.eq('view')&f.auction_id.eq(r.target_id)]
        first=None
        if len(viewed):
            v=viewed.iloc[0];k=(int(r.buyer_id),int(v.visit_id),int(r.target_id))
            first='submitted_bid' if k in submitted else reason.get(k,'no_explicit_decision')
            if first=='no_explicit_decision' and latent.loc[r.buyer_id,'bidding_style']=='sniper' and planned.get((int(r.buyer_id),int(r.target_id)),float('inf'))<v.visit_id:
                first='sniper_already_planned'
        rows.append(dict(case=key,variant=mode,buyer_id=r.buyer_id,target_id=r.target_id,
            first_revisit_reason=first,later_organic_opportunity=bool((f.event_type.eq('visit')&f.cause.eq('organic')).any()),
            category=r.category,known_window_remaining_min=r.window_end-r.time))
    return rows


def main():
    data=json.loads((RES/'evaluation-1.json').read_text(encoding='utf-8'))
    refs=json.loads((ROOT/'validation/v2_choice/results/references.json').read_text(encoding='utf-8'))
    js=json.loads((ROOT/'calibration/statistical_analysis/results/jank_shmueli.json').read_text(encoding='utf-8'))['pooled']['holdout_pairs']
    rows=[];windowrows=[];flows=[];details=[]
    old_audit=json.loads((RES/'cause-audit/summary.json').read_text(encoding='utf-8'))
    for key,cases in data['datasets'].items():
        s,sd=key.split('/');seed=int(sd[5:])
        for variant,r in cases.items():
            rows.append(dict(scenario=s[-1],seed=seed,variant=variant,**r['metrics']))
            for window,m in r['windows'].items():
                windowrows.append(dict(scenario=s[-1],seed=seed,variant=variant,window=window,**m))
            if variant=='legacy':continue
            if variant=='v1':
                flow=old_audit[key]
                fp=RES/'cause-audit'/key/'first_target_followthrough.csv'
                dp=ROOT/'data/experiments/v2b-20261031/evaluation-1'/key/'primary'
            else:
                flow=r['followthrough']
                dp=ROOT/'data/experiments/v2b1-20261031/evaluation-1'/key/'v2b1'
                fp=dp/'first_target_followthrough.csv'
            flows.append(dict(scenario=s[-1],seed=seed,variant=variant,
                **{k:v for k,v in flow.items() if isinstance(v,(float,int))},
                **{'category_'+k:v for k,v in flow['categories'].items()}))
            details.extend(detailed_followthrough(key,variant,fp,dp))
    frame=pd.DataFrame(rows);frame.to_csv(RES/'case_metrics.csv',index=False)
    windows=pd.DataFrame(windowrows);windows.to_csv(RES/'window_metrics.csv',index=False)
    pd.DataFrame(details).to_csv(RES/'followthrough_details.csv',index=False)
    flowframe=pd.DataFrame(flows);flowframe.to_csv(RES/'followthrough_by_case.csv',index=False)
    aggreg=[]
    for scope,scenarios in [('A_to_E','ABCDE'),('F_only','F')]:
        for variant,g in frame[frame.scenario.isin(list(scenarios))].groupby('variant'):
            row=dict(scope=scope,variant=variant,**g.drop(columns=['seed']).mean(numeric_only=True).to_dict())
            for metric in ('js3_bidders_mean_pos','js3_bids_per_pair','js3_repeat_pair_share'):row[metric]=None
            row['js3_positive_total']=int(g.js3_n_positive.sum())
            row['JS3_status']='insufficient exact72h support; NO aggregate accuracy score'
            aggreg.append(row)
    pd.DataFrame(aggreg).to_csv(RES/'aggregate_metrics.csv',index=False)
    scenario_summary=frame.groupby(['scenario','variant']).mean(numeric_only=True).drop(columns='seed')
    for metric in ('js3_bidders_mean_pos','js3_bids_per_pair','js3_repeat_pair_share'):scenario_summary[metric]=None
    scenario_summary.to_csv(RES/'scenario_metrics.csv')
    targets={'bids_per_pair':js['bids_per_bidder_in_auction_mean'],
             'repeat_pair_share':js['share_repeat_pairs'],
             **{k:v for k,v in refs['B04_shared_matched'].items() if k in ('b04_bidders_mean','b04_sold_rate','b04_sold_log_price_sd')},
             **{k:v for k,v in refs['price_transfer_proxies'].items() if k.startswith('log_price_sd_')}}
    gaps=[]
    for r in frame.to_dict('records'):
        for metric,target in targets.items():
            if pd.notna(r[metric]):
                gaps.append(dict(scenario=r['scenario'],seed=r['seed'],variant=r['variant'],metric=metric,
                    value=r[metric],reference=target,abs_gap=abs(r[metric]-target),
                    status='cross-market/duration-transfer ONLY' if metric in ('bids_per_pair','repeat_pair_share') else 'external proxy ONLY'))
    gaps=pd.DataFrame(gaps);gaps.to_csv(RES/'external_gaps.csv',index=False)
    paired=[]
    # Both baselines reported; no aggregate score mixing incomparable units.
    for (s,seed,metric),g in gaps.groupby(['scenario','seed','metric']):
        new=g[g.variant.eq('v2b1')].iloc[0]
        for base in ('legacy','v1'):
            b=g[g.variant.eq(base)].iloc[0]
            paired.append(dict(scenario=s,seed=seed,metric=metric,baseline=base,
                delta_abs_gap=new.abs_gap-b.abs_gap,baseline_value=b.value,new_value=new.value))
    paired=pd.DataFrame(paired);paired.to_csv(RES/'paired_gap_changes.csv',index=False)
    uncertainty=[]
    for (s,metric,base),g in paired.groupby(['scenario','metric','baseline']):
        d=g.delta_abs_gap;mean=float(d.mean())
        margin=float(stats.t.ppf(.975,len(d)-1)*d.std(ddof=1)/np.sqrt(len(d)))
        uncertainty.append(dict(scenario=s,metric=metric,baseline=base,n_seeds=len(d),mean_delta_abs_gap=mean,
            ci95_low=mean-margin,ci95_high=mean+margin,
            improved=int((d<0).sum()),worsened=int((d>0).sum()),tied=int((d==0).sum()),
            limitation='Simulation seed variation only; n=3, no reference uncertainty; shared-seed scenarios not pooled iid'))
    pd.DataFrame(uncertainty).to_csv(RES/'seed_uncertainty.csv',index=False)
    # Difference of actual metrics, including quantities without valid real-data target.
    changes=[]
    for s in 'ABCDEF':
        for base in ('legacy','v1'):
            b=frame[frame.scenario.eq(s)&frame.variant.eq(base)].set_index('seed')
            n=frame[frame.scenario.eq(s)&frame.variant.eq('v2b1')].set_index('seed')
            for metric in ('n_bids','bidders_mean_pos','bids_per_pair','repeat_pair_share','sold_rate',
                           'multi_auction_bidder_share','switch_rate','open_switch_share',
                           'log_price_sd_figure','log_price_sd_limited_goods','log_price_sd_retro_game'):
                d=n[metric]-b[metric];mean=d.mean();margin=stats.t.ppf(.975,2)*d.std(ddof=1)/np.sqrt(3)
                changes.append(dict(scenario=s,baseline=base,metric=metric,mean_delta=mean,
                    ci95_low=mean-margin,ci95_high=mean+margin,positive=int(d.gt(0).sum()),negative=int(d.lt(0).sum())))
    pd.DataFrame(changes).to_csv(RES/'metric_seed_differences.csv',index=False)
    print(pd.DataFrame(aggreg)[['scope','variant','n_bids','bids_per_pair','repeat_pair_share','sold_rate','open_switch_share']].to_string(index=False))
    for variant,g in flowframe.groupby('variant'):
        totals=g.sum(numeric_only=True);n=totals.unique_buyer_targets
        print('FLOW',variant,int(n),{k:float(totals[k]/n) for k in ('target_revisited','target_bid','target_purchased','later_any_view')})
    print('DETAIL',pd.DataFrame(details).groupby('variant').first_revisit_reason.value_counts().to_string())

if __name__=='__main__':main()
