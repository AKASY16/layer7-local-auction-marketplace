"""Old/new bridge, uptake interference and volume accounting; descriptive only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from summarize_results import ci
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'validation/v2_empirical/results'
DATA=ROOT/'data/experiments/v2c-retailrocket-20261031/main-2'
df=pd.read_csv(BASE/'main-2-analysis/market_metrics.csv')
ref=json.loads((ROOT/'validation/v2_policy/results/evaluation-2.json').read_text(encoding='utf-8'))['datasets']
bridge=json.loads((BASE/'exact_prior_bridge.json').read_text(encoding='utf-8'))['records']
bybridge={(r['scenario'],r['seed'],r['pool'],r['policy']):r for r in bridge}
raw=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(DATA.glob('scenario_*/seed_*/completed.json'))]
records=[r for d in raw for r in d['records']]
stages=[]
for s in 'ABCDE':
    for seed in (1,2,3):
        original=ref[f'nominal/scenario_{s}/seed_{seed}']
        manual=df[df.condition.eq('old_control')&df.scenario.eq(s)&df.seed.eq(seed)&df.policy.eq('manual')].iloc[0].revenue_per_listing
        oldworld=next(d for d in raw if d['scenario']==s and d['seed']==seed)
        worldprior=next(r for r in oldworld['bridge'] if r['policy']=='activity')['summary']['revenue_per_listing']
        rows=[('old_original_universal_prior',original['activity']['summary']['revenue_per_listing'],original['manual']['summary']['revenue_per_listing']),
              ('old_shared_universal_prior',bybridge[(s,seed,'shared_envelope','activity')]['summary']['revenue_per_listing'],manual),
              ('old_shared_world_prior',worldprior,manual)]
        for condition in ('old_control','lagged'):
            x=df[df.condition.eq(condition)&df.scenario.eq(s)&df.seed.eq(seed)]
            rows.append((f'new_combined_{condition}',x[x.policy.eq('combined')].iloc[0].revenue_per_listing,x[x.policy.eq('manual')].iloc[0].revenue_per_listing))
        for label,amount,base in rows:stages.append(dict(scenario=s,seed=seed,stage=label,pct=100*(amount/base-1)))
stage_df=pd.DataFrame(stages)
stage_summary=[dict(stage=stage,**ci(g.groupby('seed').pct.mean())) for stage,g in stage_df.groupby('stage')]
spill=pd.read_csv(BASE/'main-2-analysis/spillovers.csv');outspill=[]
for group,ss in [('mean_BCD',set('BCD')),('F',{'F'})]:
    sub=spill[spill.condition.eq('adoption20')&spill.scenario.isin(ss)]
    for (policy,adopted),g in sub.groupby(['policy','adopted']):
        outspill.append(dict(group=group,policy=policy,adopted=bool(adopted),
            revenue_delta_KRW=ci(g.groupby('seed').revenue_delta.mean()),
            mean_price_or_bidder_changed=float(g.changed_unchosen_outcomes.mean()),n_per_world=int(g.n.iloc[0])))
volume=[]
for condition in ('lagged','global_normalization','frozen_availability'):
    for policy in ('manual','activity_only','combined'):
        g=df[df.condition.eq(condition)&df.scenario.isin(set('BCF'))&df.seed.le(3)&df.policy.eq(policy)]
        volume.append(dict(condition=condition,policy=policy,expected_ratio=float(g.expected_ratio.mean()),
            organic=float(g.organic_visits.mean()),planned=float(g.planned_visits.mean())))
unique={r['cache_key']:r for r in records}
runtime={}
for group,ss in [('ABCDE',set('ABCDE')),('F',{'F'})]:
    values=[r['seconds'] for r in unique.values() if r['scenario'] in ss]
    runtime[group]=dict(unique_markets=len(values),median_validation_seconds=float(np.median(values)),
        p95_validation_seconds=float(np.quantile(values,.95)),mean_validation_seconds=float(np.mean(values)))
wall=(BASE/'main-2_completion.json').stat().st_mtime-(BASE/'main-2_registry.json').stat().st_mtime
result=dict(bridge_matched3seed_stage_uplift=stage_summary,adoption20_interference=outspill,matched_volume=volume,
    runtime=runtime,wall_seconds_with_concurrent_other_work=wall,
    note='Bridge stages change different assumptions; final stage is a bundle, not pure causal profile effect. Runtime includes guards/invariants/state hashes and excludes model initialization; not a production benchmark.')
dest=BASE/'main-2-analysis/comparison_accounting.json'
if dest.exists():raise FileExistsError(dest)
dest.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
