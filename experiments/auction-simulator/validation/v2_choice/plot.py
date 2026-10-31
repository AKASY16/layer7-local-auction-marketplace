"""Standalone descriptive comparison figure, not a policy-performance plot."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'validation/v2_choice/results'
d=pd.read_csv(R/'aggregate_metrics.csv')
d=d[d.scope.eq('A_to_E')].set_index('variant').loc[['legacy','primary','age60','age360']]
labels=['Legacy','Primary\nno age cutoff','Age <=60m','Age <=360m']
fig,axes=plt.subplots(2,2,figsize=(10.6,6.6),layout='constrained')
for ax,metric,title in zip(axes.flat,['bidders_mean_pos','repeat_pair_share','sold_rate','log_price_sd_figure'],
    ['Bidders per auction (positive-bid only)','Repeat bidder-auction pair share','Sold fraction (all auctions)','Sold price log SD: figure category']):
    ax.bar(labels,d[metric],color=['#777777','#246694','#72a29a','#b4c7a1'])
    ax.set_title(title,fontsize=10)
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    for i,v in enumerate(d[metric]):ax.annotate(f'{v:.3f}',(i,v),xytext=(0,4),textcoords='offset points',ha='center',fontsize=9)
    ax.set_ylim(0,d[metric].max()*1.2)
fig.suptitle('Fixed A-E worlds: fewer bids do not establish a better behavioral model',fontsize=12)
fig.savefig(R/'comparison.png',dpi=170)
fig.savefig(R/'comparison.svg')
print(R/'comparison.png')
