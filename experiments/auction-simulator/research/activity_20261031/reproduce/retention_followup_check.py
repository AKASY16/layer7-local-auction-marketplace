"""Conservative complete-calendar-day followup; final UTC date is partial.

The initial audit's 'last.floor(D)' bound admitted a partial terminal date.
Keep that audit unchanged and publish this explicit correction separately.
"""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
df=pd.read_csv(ROOT/'data/external/activity_profiles/retailrocket/events.csv',usecols=['timestamp','visitorid'])
ts=pd.to_datetime(df.timestamp,unit='ms',utc=True)
df['date']=ts.dt.floor('D')
days=df[['visitorid','date']].drop_duplicates().sort_values(['visitorid','date'],kind='stable')
days['rank']=days.groupby('visitorid').cumcount()
first=days[days['rank'].eq(0)].set_index('visitorid').date
second=days[days['rank'].eq(1)].set_index('visitorid').date
last_complete=ts.max().floor('D')-pd.Timedelta(days=1)
report={'last_complete_UTC_date':str(last_complete),'first_observed_not_signup':True,
        'left_censoring_and_cookie_identity_remain':True,'retention':{}}
for n in (1,7,28):
    eligible=first[first<=last_complete-pd.Timedelta(days=n)]
    lag=(second.reindex(eligible.index)-eligible).dt.total_seconds()/86400
    report['retention'][str(n)]=dict(eligible=len(eligible),returned_on_later_date=int(lag.le(n).sum()),share=float(lag.le(n).mean()))
dest=ROOT/'research/activity_20261031/retailrocket_analysis/retention_complete_followup.json'
if dest.exists():raise FileExistsError(dest)
dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
