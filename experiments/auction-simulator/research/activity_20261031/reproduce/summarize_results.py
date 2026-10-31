"""Fixed seed-paired presentation; all registered conditions retained."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]

def ci(x):
    x=np.array(x,float);n=len(x);m=float(x.mean())
    h=float(t.ppf(.975,n-1)*x.std(ddof=1)/np.sqrt(n)) if n>1 else 0.
    return dict(mean=m,lo=m-h,hi=m+h,n_seed=n,positive=int((x>0).sum()),negative=int((x<0).sum()))

def main(name):
    folder=ROOT/'validation/v2_empirical/results'/f'{name}-analysis'
    df=pd.read_csv(folder/'market_metrics.csv');paired=pd.read_csv(folder/'paired_market_differences.csv')
    out=folder/'presentation'
    if out.exists():raise FileExistsError(out)
    out.mkdir()
    stats=[]
    for condition in sorted(df.condition.unique()):
        scenarios=set(df[df.condition.eq(condition)].scenario)
        groups=[('mean_'+''.join(sorted(scenarios-{'F'})),scenarios-{'F'}),('F',{'F'})]
        for group,ss in groups:
            if not ss:continue
            for (policy,baseline),g in paired[paired.condition.eq(condition)&paired.scenario.isin(ss)].groupby(['policy','baseline']):
                for metric in ('revenue_per_listing','revenue_per_listing_pct','sold_rate','bidders_mean','duration_mean','organic_visits','planned_visits'):
                    v=g.groupby('seed')[metric].mean()
                    stats.append(dict(condition=condition,group=group,policy=policy,baseline=baseline,metric=metric,**ci(v)))
    stats=pd.DataFrame(stats);stats.to_csv(out/'condition_seed_summary.csv',index=False)
    main=df[df.condition.eq('lagged')].copy()
    tables=[]
    for group,ss in [('mean_ABCDE',set('ABCDE')),('F',{'F'})]:
        for policy,g in main[main.scenario.isin(ss)].groupby('policy'):
            v=g.groupby('seed')[['revenue_per_listing','revenue_total','sold_rate','unsold_rate','bidders_mean','duration_mean','night_end_share']].mean().mean()
            tables.append(dict(group=group,policy=policy,**v.to_dict()))
    pd.DataFrame(tables).to_csv(out/'primary_policy_table.csv',index=False)
    # Same3seed paired contrasts for aligning profile vs lagged forecast.
    contrasts=[]
    for condition in ('aligned','old_control','flat'):
        for group,ss in [('mean_ABCDE',set('ABCDE')),('F',{'F'})]:
            for policy in ('activity_only','competition_only','combined'):
                a=df[df.condition.eq(condition)&df.scenario.isin(ss)&df.policy.eq(policy)&df.seed.le(3)]
                b=df[df.condition.eq('lagged')&df.scenario.isin(ss)&df.policy.eq(policy)&df.seed.le(3)]
                # Separate policies' uplift vs their OWN same-world manual.
                def uplift(x):
                    c=df[df.condition.isin(x.condition.unique())&df.scenario.isin(ss)&df.policy.eq('manual')&df.seed.le(3)]
                    m=x.merge(c,on=['condition','scenario','seed'],suffixes=('_policy','_manual'))
                    m['uplift']=100*(m.revenue_per_listing_policy/m.revenue_per_listing_manual-1)
                    return m.groupby('seed').uplift.mean()
                diff=uplift(a)-uplift(b)
                contrasts.append(dict(condition=condition,group=group,policy=policy,contrast='uplift relative to own manual minus lagged uplift',**ci(diff)))
    pd.DataFrame(contrasts).to_csv(out/'matched_seed_control_contrasts.csv',index=False)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    def draw(ax,records,labels,title,xlabel):
        y=np.arange(len(records));means=np.array([r['mean'] for r in records]);low=np.array([r['lo'] for r in records]);high=np.array([r['hi'] for r in records])
        ax.errorbar(means,y,xerr=np.array([means-low,high-means]),fmt='o',capsize=3)
        ax.set_yticks(y,labels);ax.invert_yaxis();ax.axvline(0,color='gray',lw=1);ax.grid(axis='x',alpha=.2);ax.set_title(title);ax.set_xlabel(xlabel)
    def estimate(condition,scenarios,policy,baseline='manual',maxseed=None,metric='revenue_per_listing_pct'):
        g=paired[paired.condition.eq(condition)&paired.scenario.isin(scenarios)&paired.policy.eq(policy)&paired.baseline.eq(baseline)]
        if maxseed:g=g[g.seed.le(maxseed)]
        return ci(g.groupby('seed')[metric].mean())
    policies=['uniform_valid','activity_only','competition_only','combined']
    draw(axes[0,0],[estimate('lagged',set('ABCDE'),p) for p in policies],policies,'Lagged empirical shape: A-E,5paired seeds','Revenue/listing vs manual (%)')
    offsets=[-6,-3,0,3,6,12]
    draw(axes[0,1],[estimate('lagged' if off==0 else f'input_error_{off:+d}',set('BCD'),'combined',maxseed=3) for off in offsets],
         [f'{off:+d}h' for off in offsets],'Combined: prediction-clock error, BCD3seeds','Revenue/listing vs manual (%)')
    offsets=list(range(0,24,3))
    draw(axes[1,0],[estimate('lagged' if off==0 else f'phase_{off:02}',set('BC'),'combined',maxseed=3) for off in offsets],
         [f'+{off}h' for off in offsets],'Both input and actual phase shift: BC3seeds','Revenue/listing vs manual (%)')
    draw(axes[1,1],[estimate('lagged',{s},'combined','activity_only') for s in 'ABCDEF'],list('ABCDEF'),
         'Incremental competition term:5paired seeds','Combined vs activity-only revenue/listing (%)')
    fig.suptitle('Simulated policy sensitivity;95%t intervals across seeds, NOT Korean causal effects')
    fig.savefig(out/'policy_sensitivity.png',dpi=180);fig.savefig(out/'policy_sensitivity.svg');plt.close(fig)
    # Keep every registered condition; no selection of best shifts.
    key=stats[(stats.metric.eq('revenue_per_listing_pct'))&stats.baseline.isin(['manual','activity_only'])&stats.policy.isin(['activity_only','combined'])]
    (out/'key_results.json').write_text(json.dumps(key.to_dict('records'),indent=2),encoding='utf-8')
    print('Saved',len(stats),'paired summaries and primary table')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);a=ap.parse_args();main(a.name)
