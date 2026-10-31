"""Report every fixed case and metric; do not select a favorable parameter."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'validation/v2_choice/results'


def main():
    data=json.loads((RESULTS/'evaluation-1.json').read_text(encoding='utf-8'))
    refs=json.loads((RESULTS/'references.json').read_text(encoding='utf-8'))
    js=json.loads((ROOT/'calibration/statistical_analysis/results/jank_shmueli.json').read_text(encoding='utf-8'))
    hold=js['pooled']['holdout_pairs']
    refs['JS_pooled_transfer']={'bids_per_pair':hold['bids_per_bidder_in_auction_mean'],
                                'repeat_pair_share':hold['share_repeat_pairs']}
    (RESULTS/'supplemental_rebid_reference.json').write_text(json.dumps({'reference':refs['JS_pooled_transfer'],
        'scope':'Same bidder-auction units, different duration mix; transfer diagnostic, not72h matched validation',
        'source':'calibration/statistical_analysis/results/jank_shmueli.json'},indent=2),encoding='utf-8')
    rows=[]
    for key,cases in data['datasets'].items():
        scenario,seed=key.split('/')
        for variant,r in cases.items():
            row={'scenario':scenario[-1],'seed':int(seed[5:]),'variant':variant,**r['metrics']}
            row.update({'counter_'+k:v for k,v in r['choice_counters'].items()})
            rows.append(row)
    frame=pd.DataFrame(rows)
    frame['JS3_matched_score_allowed']=False
    frame.to_csv(RESULTS/'case_metrics.csv',index=False)
    reference_rows=[]
    for source,fields,status in [('JS3_holdout',['js3_bidders_mean_pos','js3_bids_per_pair','js3_repeat_pair_share'],'definition_duration_matched_external'),
                                 ('JS_pooled_transfer',['bids_per_pair','repeat_pair_share'],'cross_duration_market_transfer_only'),
                                 ('B04_shared_matched',['b04_bidders_mean','b04_sold_rate'],'external_market_transfer'),
                                 ('price_transfer_proxies',['log_price_sd_figure','log_price_sd_limited_goods','log_price_sd_retro_game'],'proxy_only_not_direct_validation')]:
        for metric in fields:
            target=refs[source][metric]
            for r in frame.to_dict('records'):
                value=r.get(metric)
                supported=source!='JS3_holdout'
                reference_rows.append({'scenario':r['scenario'],'seed':r['seed'],'variant':r['variant'],
                    'metric':metric,'reference':target,'value':value,'abs_gap':abs(value-target) if pd.notna(value) and supported else None,
                    'reference_group':source,'comparison_status':status if supported else 'insufficient_matched_support_NO_SCORE'})
    errors=pd.DataFrame(reference_rows)
    errors.to_csv(RESULTS/'external_gaps.csv',index=False)
    comparisons=[]
    for (s,seed,metric),g in errors.groupby(['scenario','seed','metric']):
        base=g[g.variant.eq('legacy')].iloc[0]
        for r in g[g.variant.ne('legacy')].itertuples():
            comparisons.append({'scenario':s,'seed':seed,'metric':metric,'variant':r.variant,
                'legacy':base.value,'new':r.value,'reference':r.reference,'legacy_abs_gap':base.abs_gap,
                'new_abs_gap':r.abs_gap,'delta_abs_gap':r.abs_gap-base.abs_gap,'comparison_status':r.comparison_status})
    compared=pd.DataFrame(comparisons)
    compared.to_csv(RESULTS/'paired_error_changes.csv',index=False)
    # F is a small-market stress case; never fold it into A-E as another equally
    # sized market or call shared-seed scenarios independent observations.
    scenario_summary=frame.groupby(['scenario','variant']).mean(numeric_only=True).drop(columns='seed').reset_index()
    for metric in ('js3_bidders_mean_pos','js3_bids_per_pair','js3_repeat_pair_share'):
        scenario_summary[metric]=None
    scenario_summary['JS3_status']='insufficient exact72h support; raw values only in case_metrics'
    scenario_summary.to_csv(RESULTS/'scenario_summary.csv',index=False)
    aggregate=[]
    for scope,mask in [('A_to_E',frame.scenario.ne('F')),('F_only',frame.scenario.eq('F'))]:
        q=frame[mask]
        for variant,g in q.groupby('variant'):
            row={'scope':scope,'variant':variant,**g.drop(columns=['seed']).mean(numeric_only=True).to_dict()}
            for metric in ('js3_bidders_mean_pos','js3_bids_per_pair','js3_repeat_pair_share'):row[metric]=None
            row['js3_positive_auctions_total']=int(g.js3_n_positive.sum())
            row['JS3_status']='insufficient matched support; NOT a scored validation'
            aggregate.append(row)
    pd.DataFrame(aggregate).to_csv(RESULTS/'aggregate_metrics.csv',index=False)
    stability=[]
    for (variant,metric),g in compared.groupby(['variant','metric']):
        q=g[g.scenario.ne('F')].dropna(subset=['delta_abs_gap'])
        byseed=q.groupby('seed').delta_abs_gap.mean()
        stability.append({'variant':variant,'metric':metric,'scope':'A-E descriptive15cases,3shared seed labels',
                          'cases_improved':int(q.delta_abs_gap.lt(0).sum()),'cases_worsened':int(q.delta_abs_gap.gt(0).sum()),
                          'cases_tied':int(q.delta_abs_gap.eq(0).sum()),'mean_delta_abs_gap':float(q.delta_abs_gap.mean()) if len(q) else None,
                          'n_seed_labels':len(byseed),'seed_mean_changes':{int(k):float(v) for k,v in byseed.items()},
                          'SE_not_reported':'Only3seed labels and transferred references; no18-iid confidence claim'})
    (RESULTS/'stability.json').write_text(json.dumps(stability,indent=2,allow_nan=False),encoding='utf-8')
    uncertainty=[]
    for (scenario,variant,metric),g in compared.groupby(['scenario','variant','metric']):
        q=g.dropna(subset=['delta_abs_gap'])
        n=len(q)
        if n<2:continue
        assert q.seed.is_unique
        mean=q.delta_abs_gap.mean()
        margin=stats.t.ppf(.975,n-1)*q.delta_abs_gap.std(ddof=1)/np.sqrt(n)
        uncertainty.append({'scenario':scenario,'variant':variant,'metric':metric,'n_seeds':n,
                            'mean_delta_abs_gap':mean,'ci95_low':mean-margin,'ci95_high':mean+margin,
                            'scope':'Simulation seed variation only; empirical-reference uncertainty not included'})
    pd.DataFrame(uncertainty).to_csv(RESULTS/'seed_uncertainty.csv',index=False)
    # Validation-only comparison: identical exogenous organic views in hard-close
    # data, ignoring endogenous global visit IDs and allowing planned-event changes.
    organic=[]
    path=ROOT/'data/experiments/v2b-20261031/evaluation-1'
    for key in data['datasets']:
        def view(mode):
            f=pd.read_csv(path/key/mode/'visits.csv')
            return list(f.loc[f.event_type.eq('view')&f.cause.eq('organic'),['event_time','buyer_id','auction_id']].itertuples(index=False,name=None))
        base=view('legacy')
        for variant in ('primary','age60','age360'):
            equal=base==view(variant)
            organic.append({'case':key,'variant':variant,'organic_views_equal_at_exported_second_precision':equal})
            assert equal,'Unexpected change to organic exposure under unchanged hard-close world'
    (RESULTS/'organic_exposure_checks.json').write_text(json.dumps(organic,indent=2),encoding='utf-8')
    print('ANALYSIS COMPLETE',len(frame),'fixed mode/cases',len(organic),'organic exposure checks passed')
    print(pd.DataFrame(aggregate)[['scope','variant','n_bids','bidders_mean_pos','bids_per_pair','repeat_pair_share','sold_rate','b04_sold_rate']].to_string(index=False))


if __name__=='__main__':main()
