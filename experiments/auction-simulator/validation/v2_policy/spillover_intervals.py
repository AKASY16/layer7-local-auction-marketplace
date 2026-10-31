"""Seed uncertainty for market decomposition; no auction-row iid inference."""
from pathlib import Path
import pandas as pd
from analyze_policy import interval
ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_policy/results'

def main():
    f=pd.read_csv(RES/'spillovers.csv');f=f[f.family.eq('uptake20')]
    rows=[]
    for scope,scenarios in [('BCD','BCD'),('F','F')]:
        for (policy,group),g in f[f.scenario.isin(list(scenarios))].groupby(['policy','group']):
            seed=g.groupby('seed').sum(numeric_only=True)
            for metric,values in [('revenue_delta_sum',seed.revenue_delta_sum),
                ('outcome_changed_share',seed.outcome_changed_count/seed.n.replace(0,float('nan')))]:
                rows.append(dict(scope=scope,policy=policy,group=group,metric=metric,**interval(values)))
    pd.DataFrame(rows).to_csv(RES/'spillover_seed_uncertainty.csv',index=False)

if __name__=='__main__':main()
