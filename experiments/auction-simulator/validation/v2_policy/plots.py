"""Standalone scientific plots; descriptive simulation evidence, never real uplift."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_policy/results'
COLORS={'conservative':'#2459a6','activity':'#c66b17'}

def save(fig,name):
    fig.savefig(RES/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(RES/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

def main():
    u=pd.read_csv(RES/'seed_uncertainty.csv')
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    policies=['uniform_valid','fixed48h','conservative','activity']
    for ax,metric,label,scale in zip(axes,['revenue_percent','sold_rate','bidders_mean'],
        ['Revenue change (%)','Sale-rate change (pp)','Bidders/listing change'],[1,100,1]):
        q=u[u.family.eq('nominal')&u.scope.eq('large_ABCDE')&u.metric.eq(metric)].set_index('policy').loc[policies]
        ax.errorbar(q['mean']*scale,range(4),xerr=np.vstack([(q['mean']-q.low)*scale,(q.high-q['mean'])*scale]),fmt='o',capsize=4)
        ax.set_yticks(range(4),policies);ax.axvline(0,color='black',lw=.8);ax.grid(alpha=.2);ax.set_xlabel(label)
    fig.suptitle('Nominal A-E: paired independent seed summaries (n=5, t95% intervals)\nSimulation assumptions only; no empirical-reference uncertainty or real-market causality')
    save(fig,'nominal_policy_comparison')
    families=['nominal_matched3','activity_weak','activity_flat','activity_day','activity_night']
    labels=['Evening base','Weaker peak','Flat','Day peak','Night peak']
    fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
    for ax,metric,label,scale in zip(axes,['revenue_percent','sold_rate','bidders_mean'],
        ['Revenue change (%)','Sale-rate change (pp)','Bidders/listing change'],[1,100,1]):
        for j,policy in enumerate(COLORS):
            q=u[u.scope.eq('large_ABCDE')&u.policy.eq(policy)&u.metric.eq(metric)].set_index('family').loc[families]
            y=np.arange(5)+(j-.5)*.18
            ax.errorbar(q['mean']*scale,y,xerr=np.vstack([(q['mean']-q.low)*scale,(q.high-q['mean'])*scale]),
                fmt='o',capsize=3,color=COLORS[policy],label=policy)
        ax.set_yticks(range(5),labels);ax.axvline(0,color='black',lw=.8);ax.grid(alpha=.2);ax.set_xlabel(label)
    axes[0].legend(loc='best')
    fig.suptitle('Activity misspecification: fixed evening recommendation prior, matched seeds1-3\nOnly actual ASSUMED activity changes; unchanged buyer traits and candidate streams')
    save(fig,'activity_sensitivity')
    raw=json.loads((RES/'evaluation-2.json').read_text(encoding='utf-8'))['datasets']
    fig,ax=plt.subplots(figsize=(9,3.8),layout='constrained')
    for family,label in [('nominal','base evening'),('activity_weak','weak'),('activity_flat','flat'),('activity_day','day'),('activity_night','night')]:
        r=raw[f'{family}/scenario_B/seed_1']['manual']
        ax.plot(range(24),r['actual_ASSUMED_profile'],label=label)
    ax.set_xticks(range(0,24,3));ax.set_xlabel('KST hour');ax.set_ylabel('Relative activity, mean1')
    ax.legend(ncol=5,loc='upper center',bbox_to_anchor=(.5,-.2));ax.grid(alpha=.2)
    ax.set_title('ASSUMED scenarioB activity curves: these are not observed Korean users')
    save(fig,'assumed_activity_profiles')
    spill=pd.read_csv(RES/'spillovers.csv')
    spill=spill[spill.family.eq('uptake20')&spill.policy.isin(COLORS)&spill.group.isin(['adopted','not_adopted'])]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ax,scenarios,title in zip(axes,['BCD','F'],['Large scenarios BCD','Cold start F']):
        q=spill[spill.scenario.isin(list(scenarios))]
        for j,pol in enumerate(COLORS):
            x=q[q.policy.eq(pol)].groupby(['seed','group']).revenue_delta_sum.sum().unstack()
            n=q[q.policy.eq(pol)].groupby('seed').n.sum()
            adopted=x.adopted/n;other=x.not_adopted/n;total=adopted+other
            vals=[adopted.mean(),other.mean(),total.mean()]
            ax.bar(np.arange(3)+(j-.5)*.3,vals,.3,label=pol,color=COLORS[pol])
        ax.axhline(0,color='black',lw=.8);ax.set_xticks(range(3),['Adopters','Other auctions','Whole market']);ax.grid(axis='y',alpha=.2)
        ax.set_title(title);ax.set_ylabel('Revenue delta contribution / ALL listings (KRW)')
    axes[0].legend()
    fig.suptitle('20% uptake: market gain = adopter gain + spillover\nMean seed contributions (n=3); no real causal interpretation')
    save(fig,'partial_uptake_spillover')

if __name__=='__main__':main()
