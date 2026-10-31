"""Descriptive sold-price quantiles and ECDF, no price/behavior calibration."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_followup/results'

def main():
    rows=[];prices=[]
    for s in 'ABCDEF':
        for seed in (1,2,3):
            for mode in ('legacy','v1','v2b1'):
                p=ROOT/f'data/experiments/v2b1-20261031/evaluation-1/scenario_{s}/seed_{seed}/{mode}'
                f=pd.read_csv(p/'outcomes.csv')
                a=pd.read_csv(p/'auctions.csv')
                f=f.merge(a[['auction_id','category']],on='auction_id',validate='one_to_one')
                sold=f[f.sold.eq(True)].copy().rename(columns={'winning_price':'final_price'})
                sold['scenario']=s;sold['seed']=seed;sold['variant']=mode
                prices.append(sold[['scenario','seed','variant','category','final_price']])
                for c,g in sold.groupby('category'):
                    values=g.final_price
                    rows.append(dict(scenario=s,seed=seed,variant=mode,category=c,n_sold=len(g),
                        mean=values.mean(),log_sd=np.log(values).std(ddof=1),
                        **{f'p{int(q*100)}':values.quantile(q) for q in (.1,.25,.5,.75,.9)}))
    pd.DataFrame(rows).to_csv(RES/'sold_price_quantiles.csv',index=False)
    f=pd.concat(prices);f=f[f.scenario.ne('F')]
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for ax,c in zip(axes.flat,sorted(f.category.unique())):
        for mode in ('legacy','v1','v2b1'):
            v=np.sort(np.log10(f[f.category.eq(c)&f.variant.eq(mode)].final_price.to_numpy()))
            ax.plot(v,np.arange(1,len(v)+1)/len(v),label=mode)
        ax.set_title(c);ax.set_xlabel('log10 sold price (KRW)');ax.set_ylabel('ECDF')
        ax.grid(alpha=.2);ax.legend()
    fig.suptitle('A-E, 3 seeds: descriptive pooled sold-price distributions\nUnequal sold counts; no iid inference or external currency-level matching')
    fig.savefig(RES/'sold_price_ecdf.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
