"""Additional raw-profile diagnostics; no raw edits or auction model fitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'research/activity_20261031/retailrocket_analysis'
p=json.loads((OUT/'profiles.json').read_text())
base=np.array(p['profiles']['unique_active']['train'])
rows=[]
for name,entry in p['profiles'].items():
    q=np.array(entry['train'])
    rows.append(dict(profile=name,mean=q.mean(),maximum=q.max(),minimum=q.min(),
        total_variation_vs_primary=float(np.abs(q-base).sum()/336)))
for i,week in enumerate(p['weekly_counts']['unique_active']['evaluation']):
    q=np.array(week);q=q/q.mean()
    rows.append(dict(profile=f'evaluation_week_{i}',mean=q.mean(),maximum=q.max(),minimum=q.min(),
        total_variation_vs_primary=float(np.abs(q-base).sum()/336)))
pd.DataFrame(rows).to_csv(OUT/'profile_sensitivity.csv',index=False)
df=pd.read_csv(ROOT/'data/external/activity_profiles/retailrocket/events.csv',dtype={'transactionid':'Int64'})
tx=df[df.event.eq('transaction')]
check=dict(transaction_ids_with_multiple_visitors=int(tx.groupby('transactionid').visitorid.nunique().gt(1).sum()),
    multirow_transaction_ids=int(tx.groupby('transactionid').size().gt(1).sum()),
    interpretation='transaction events are item-level records; distinct IDs are not identical to event count')
(OUT/'transaction_checks.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
print(check)
