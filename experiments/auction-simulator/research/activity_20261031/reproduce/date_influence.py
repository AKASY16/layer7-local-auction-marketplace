"""Leave-one-date/week source-profile leverage, not exclusion or policy tuning."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'research/activity_20261031/retailrocket_analysis'
df=pd.read_csv(BASE/'date_hour_metrics.csv')
df=df[df.metric.eq('unique_active')&df.period.eq('train')].copy()
df['date']=pd.to_datetime(df.date,utc=True)
matrix=df.pivot(index='date',columns='hour',values='count').sort_index()
def profile(table):
    x=table.groupby(table.index.weekday).mean().to_numpy()
    return x/x.mean()
p=profile(matrix)
ref=np.array(json.loads((BASE/'profiles.json').read_text(encoding='utf-8'))['profiles']['unique_active']['train'])
assert np.allclose(p,ref,rtol=0,atol=1e-12)
rows=[]
for d in matrix.index:
    q=profile(matrix.drop(d))
    rows.append(dict(unit='date',label=str(d.date()),TV=float(np.abs(p-q).sum()/336),max_cell_change=float(np.abs(p-q).max())))
weeks=(matrix.index-matrix.index[0]).days//7
for week in sorted(set(weeks)):
    q=profile(matrix[weeks!=week])
    rows.append(dict(unit='week',label=int(week),TV=float(np.abs(p-q).sum()/336),max_cell_change=float(np.abs(p-q).max())))
out=BASE/'date_influence.csv'
if out.exists():raise FileExistsError(out)
pd.DataFrame(rows).to_csv(out,index=False)
summary={unit:{'maximum_TV':max(r['TV'] for r in rows if r['unit']==unit),
               'median_TV':float(np.median([r['TV'] for r in rows if r['unit']==unit])),
               'most_influential':max((r for r in rows if r['unit']==unit),key=lambda r:r['TV'])['label']}
         for unit in ('date','week')}
(BASE/'date_influence_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
