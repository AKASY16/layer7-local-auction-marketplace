"""Read-only raw audit and UTC-reference activity profiles, no auction fitting.

Run with the Codex bundled Python; all CSV/JSON files are analysis intermediates.
Never treat unknown source-local time as observed Korean local time.
"""
import hashlib,json,math,sys,platform
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'data/external/activity_profiles/retailrocket/events.csv'
OUT=ROOT/'research/activity_20261031/retailrocket_analysis'

def safe(v):
    if isinstance(v,dict):return {str(k):safe(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [safe(x) for x in v]
    if isinstance(v,np.generic):return safe(v.item())
    if isinstance(v,float):return v if math.isfinite(v) else None
    if isinstance(v,(pd.Timestamp,Path)):return str(v)
    return v
def write(name,value):
    (OUT/name).write_text(json.dumps(safe(value),indent=2,allow_nan=False),encoding='utf-8')
def shape(a):
    a=np.asarray(a,float);assert a.shape==(7,24) and np.all(a>=0) and a.mean()>0
    return a/a.mean()
def table_profile(daily,dates):
    rows=[]
    for dow in range(7):
        keep=[i for i,d in enumerate(dates) if d.weekday()==dow]
        assert keep
        rows.append(daily[keep].mean(axis=0))
    return shape(rows)
def bootstrap(weeks,n=2000):
    rng=np.random.default_rng(2026103101)
    nweek=len(weeks)
    draws=np.array([shape(weeks[rng.integers(0,nweek,nweek)].mean(axis=0)) for _ in range(n)])
    return np.quantile(draws,[.025,.5,.975],axis=0)

def main():
    if OUT.exists():raise FileExistsError('Use a fresh audit version; keep all previous outputs')
    OUT.mkdir(parents=True)
    print('Reading94MB raw file',flush=True)
    df=pd.read_csv(RAW,dtype=dict(timestamp='int64',visitorid='int64',event='category',itemid='int64',transactionid='Int64'))
    assert list(df.columns)==['timestamp','visitorid','event','itemid','transactionid']
    assert not df[['timestamp','visitorid','event','itemid']].isna().any().any()
    assert (df.timestamp>=0).all() and (df.visitorid>=0).all() and (df.itemid>=0).all()
    expected={'view','addtocart','transaction'}
    assert set(df.event.unique())==expected
    timestamp=pd.to_datetime(df.timestamp,unit='ms',utc=True,errors='raise')
    df['date']=timestamp.dt.floor('D');df['hour']=timestamp.dt.hour.astype('int8')
    first,last=timestamp.min(),timestamp.max()
    first_monday=first.floor('D')+pd.Timedelta(days=(7-first.weekday())%7)
    if first_monday<first:first_monday+=pd.Timedelta(days=7)
    last_monday=last.floor('D')-pd.Timedelta(days=last.weekday())
    nweeks=int((last_monday-first_monday).days//7)
    ntrain=int(2*nweeks//3);split=first_monday+pd.Timedelta(weeks=ntrain)
    assert ntrain>=4 and nweeks-ntrain>=4
    dates=pd.date_range(first_monday,last_monday-pd.Timedelta(days=1),freq='D')
    index=pd.MultiIndex.from_product([dates,range(24)],names=['date','hour'])
    totaldays=pd.date_range(first.floor('D'),last.floor('D'),freq='D')
    daily=pd.DataFrame(index=totaldays)
    daily.index.name='date'
    daily['unique_visitors']=df.groupby('date',observed=True).visitorid.nunique()
    daily['events']=df.groupby('date',observed=True).size()
    daily['observed_hours']=df.groupby('date',observed=True).hour.nunique()
    for e in sorted(expected):daily[e]=df[df.event.eq(e)].groupby('date',observed=True).size()
    daily=daily.fillna(0)
    tr=daily[(daily.index>=first_monday)&(daily.index<split)]
    med=tr.unique_visitors.median();mad=(tr.unique_visitors-med).abs().median()
    daily['training_MAD_z']=.67448975*(daily.unique_visitors-med)/(mad if mad else float('nan'))
    daily['flag_5MAD']=daily.training_MAD_z.abs()>5
    daily['boundary_day']=daily.index.isin([first.floor('D'),last.floor('D')])
    daily.to_csv(OUT/'daily_quality.csv')
    training=df[(df.date>=first_monday)&(df.date<split)]
    counts=training.visitorid.value_counts().sort_values(ascending=False,kind='stable')
    top_train=set(counts.head(math.ceil(len(counts)*.001)).index)
    all_counts=df.visitorid.value_counts()
    top_all=all_counts.head(math.ceil(len(all_counts)*.001))
    print('Grouping distinct users and event profiles',flush=True)
    metrics={
        'unique_active':df.groupby(['date','hour'],observed=True).visitorid.nunique(),
        'views':df[df.event.eq('view')].groupby(['date','hour'],observed=True).size(),
        'transactions':df[df.event.eq('transaction')].groupby(['date','hour'],observed=True).size(),
        'unique_buyers':df[df.event.eq('transaction')].groupby(['date','hour'],observed=True).visitorid.nunique(),
        'unique_orders':df[df.event.eq('transaction')].groupby(['date','hour'],observed=True).transactionid.nunique(),
        'unique_active_exclude_training_top01':df[~df.visitorid.isin(top_train)].groupby(['date','hour'],observed=True).visitorid.nunique(),
        'views_exact_dedup':df.drop_duplicates(subset=['timestamp','visitorid','event','itemid','transactionid']).query("event=='view'").groupby(['date','hour'],observed=True).size(),
    }
    ntd=ntrain*7;profiles={};week_arrays={};metric_rows=[]
    for name,series in metrics.items():
        a=series.reindex(index,fill_value=0).to_numpy().reshape(len(dates),24).astype(float)
        train=a[:ntd].reshape(ntrain,7,24);test=a[ntd:].reshape(nweeks-ntrain,7,24)
        p=shape(train.mean(axis=0));q=shape(test.mean(axis=0))
        profiles[name]=dict(train=p.tolist(),evaluation=q.tolist(),train_total=float(train.sum()),evaluation_total=float(test.sum()),
            bootstrap_week_ci=bootstrap(train).tolist(),zero_train_cells=int((p==0).sum()),
            definition='mean date-hour distinct visitor counts' if name.startswith('unique_active') else 'date-hour event/identifier counts; not auction bids')
        week_arrays[name]=dict(train=train.tolist(),evaluation=test.tolist())
        for d,r in zip(dates,a):
            for hour,value in enumerate(r):metric_rows.append(dict(date=d.isoformat(),weekday=d.weekday(),hour=hour,metric=name,count=value,period='train' if d<split else 'evaluation'))
    # Equal daily volume removes high-traffic dates' weighting; not the main estimator.
    ua=np.array(week_arrays['unique_active']['train']).reshape(ntd,24)
    eq=ua/ua.sum(axis=1,keepdims=True)
    profiles['unique_active_daily_equal_volume']=dict(train=table_profile(eq,list(dates[:ntd])).tolist(),
        definition='Each observed date has equal total weight; diagnostic only')
    # Stratified day bootstrap retains weekday cells while breaking week clustering.
    rng=np.random.default_rng(2026103102)
    uaweek=np.array(week_arrays['unique_active']['train'])
    daydraw=np.array([shape(np.stack([uaweek[rng.integers(0,ntrain,ntrain),d,:].mean(axis=0) for d in range(7)])) for _ in range(2000)])
    profiles['unique_active']['bootstrap_day_ci']=np.quantile(daydraw,[.025,.5,.975],axis=0).tolist()
    pd.DataFrame(metric_rows).to_csv(OUT/'date_hour_metrics.csv',index=False)
    # Pooled unique visitors differs from a visitor-date-hour mean.
    pooled=df.assign(weekday=df.date.dt.weekday).groupby(['weekday','hour'],observed=True).agg(unique_visitors=('visitorid','nunique'),events=('event','size'))
    pooled.to_csv(OUT/'pooled_weekday_hour_distinct.csv')
    profile_errors=[]
    for name,values in profiles.items():
        if 'evaluation' not in values:continue
        p=np.array(values['train']);q=np.array(values['evaluation'])
        profile_errors.append(dict(metric=name,MAE=float(np.abs(p-q).mean()),RMSE=float(np.sqrt(((p-q)**2).mean())),
            total_variation=float(np.abs(p-q).sum()/336),correlation=float(np.corrcoef(p.ravel(),q.ravel())[0,1])))
    pd.DataFrame(profile_errors).to_csv(OUT/'chronological_profile_errors.csv',index=False)
    print('Revisit patterns with temporal sorting',flush=True)
    ordered=df.sort_values(['visitorid','timestamp'],kind='stable')
    gap=ordered.groupby('visitorid',observed=True).timestamp.diff()/1000
    positive=gap[gap>0]
    active_days=df[['visitorid','date']].drop_duplicates().sort_values(['visitorid','date'],kind='stable')
    first_two=active_days.assign(rank=active_days.groupby('visitorid').cumcount())
    starts=first_two[first_two['rank'].eq(0)].set_index('visitorid').date
    second=first_two[first_two['rank'].eq(1)].set_index('visitorid').date
    returns={}
    for days in (1,7,28):
        eligible=starts[starts<=last.floor('D')-pd.Timedelta(days=days)]
        lag=(second.reindex(eligible.index)-eligible).dt.total_seconds()/86400
        returns[str(days)]=dict(eligible_first_observed_visitors=len(eligible),returned_on_later_date_within_window=int(lag.le(days).sum()),
            share=float(lag.le(days).mean()),right_censoring='first-observed dates with complete follow-up only; left censoring remains')
    report=dict(file=dict(path=str(RAW),bytes=RAW.stat().st_size,sha256=hashlib.sha256(RAW.read_bytes()).hexdigest()),
        rows=len(df),columns=list(df.columns[:5]),dtypes={k:str(v) for k,v in df.iloc[:,:5].dtypes.items()},
        min_UTC=first,max_UTC=last,n_unique_visitors=df.visitorid.nunique(),n_unique_items=df.itemid.nunique(),
        event_counts=df.event.value_counts().to_dict(),missing=df.iloc[:,:5].isna().sum().to_dict(),
        exact_duplicate_rows=int(df.duplicated(subset=['timestamp','visitorid','event','itemid','transactionid']).sum()),
        timestamp_inversions_in_raw=int((df.timestamp.diff()<0).sum()),
        transaction_without_id=int((df.event.eq('transaction')&df.transactionid.isna()).sum()),
        id_on_nontransaction=int((~df.event.eq('transaction')&df.transactionid.notna()).sum()),
        unique_transaction_ids=int(df.transactionid.nunique()),
        publisher_counts_match=(len(df)==2756101 and df.visitorid.nunique()==1407580),
        cryptographic_publisher_checksum_available=False,source_local_timezone='UNVERIFIED',source_country='UNVERIFIED',
        categories='No category/property files or semantic labels in supplied file; entire ecommerce, not collectibles',
        split=dict(complete_week_start=first_monday,train_end_exclusive=split,evaluation_end_exclusive=last_monday,
            n_train_weeks=ntrain,n_evaluation_weeks=nweeks-ntrain,boundary_rows_excluded_from_primary=int(((df.date<first_monday)|(df.date>=last_monday)).sum())),
        concentration=dict(top01_user_count=len(top_all),top01_event_share=float(top_all.sum()/len(df)),
            top_visitor_events=int(all_counts.max()),training_top01_count=len(top_train)),
        abnormal_dates=daily[daily.flag_5MAD|daily.observed_hours.lt(24)].reset_index().assign(date=lambda x:x.date.astype(str)).to_dict('records'),
        revisits=dict(multiday_visitors=int((active_days.groupby('visitorid').size()>1).sum()),
            positive_gap_seconds_quantiles=positive.quantile([.1,.5,.9,.95,.99]).to_dict(),
            observed_sessions_30min=int((gap.isna()|gap.gt(1800)).sum()),retention=returns),
        environment=dict(python=sys.version,pandas=pd.__version__,numpy=np.__version__,platform=platform.platform()))
    write('audit.json',report)
    write('profiles.json',dict(clock='UTC-reference bins; local timezone/country unknown; NOT empirical KST',
        split=report['split'],normalization='global mean over168hourly cells=1; no subhour interpolation',
        profiles=profiles,weekly_counts=week_arrays,training_top01_ids=list(map(int,sorted(top_train)))))
    print(json.dumps(safe({k:report[k] for k in ('rows','min_UTC','max_UTC','event_counts','exact_duplicate_rows','split','concentration')}),indent=2),flush=True)

if __name__=='__main__':main()
