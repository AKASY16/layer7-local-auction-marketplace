"""Read all150 registered primary policies, independent of unfinished diagnostics."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'data/experiments/v2c-retailrocket-20261031/main-2'
paths=sorted(BASE.glob('scenario_*/seed_*/lagged/records.json'))
assert len(paths)==30,'Wait for every primary World, never summarize a favorable subset'
records=[]
for path in paths:
    d=json.loads(path.read_text(encoding='utf-8'))
    for name,h in d['files'].items():assert hashlib.sha256((path.parent/name).read_bytes()).hexdigest()==h
    for r in d['records']:
        assert r['invariants']['all_pass'] and r['replayed']
        records.append(dict(scenario=r['scenario'],seed=r['seed'],policy=r['policy'],**r['summary']))
assert len(records)==150
df=pd.DataFrame(records);results=[]
for label,ss in [('mean_ABCDE',set('ABCDE')),('F',{'F'})]:
    x=df[df.scenario.isin(ss)].copy()
    for baseline in ('manual','activity_only'):
        b=x[x.policy.eq(baseline)][['scenario','seed','revenue_per_listing']]
        for policy in x.policy.unique():
            if policy==baseline:continue
            a=x[x.policy.eq(policy)].merge(b,on=['scenario','seed'],suffixes=('_p','_b'))
            a['pct']=100*(a.revenue_per_listing_p/a.revenue_per_listing_b-1)
            values=a.groupby('seed').pct.mean();m=float(values.mean());half=float(t.ppf(.975,4)*values.std(ddof=1)/np.sqrt(5))
            results.append(dict(group=label,policy=policy,baseline=baseline,mean=m,lo=m-half,hi=m+half,n_seed=5))
out=ROOT/'validation/v2_empirical/results/primary_snapshot.json'
if out.exists():raise FileExistsError(out)
out.write_text(json.dumps(dict(n_primary_markets=150,all_replayed=True,results=results),indent=2),encoding='utf-8')
for r in results:
    if r['baseline']=='manual' or r['policy']=='combined':print(r)
