"""Descriptive post-run mechanism accounting, never policy inputs or tuning."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from v2_policy_empirical.activity import Curve

def main(name):
    dest=ROOT/'validation/v2_empirical/results'/f'{name}-diagnostics'
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir()
    rows=[]
    for path in sorted((ROOT/'data/experiments/v2c-retailrocket-20261031'/name).glob('scenario_*/seed_*/completed.json')):
        d=json.loads(path.read_text(encoding='utf-8'))
        for record in d['records']:
            condition=record['condition'];policy=record['policy']
            if condition!='lagged' and condition not in ('flat','old_control','phase_09','input_error_+6','decoupled','global_normalization'):continue
            folder=path.parent/condition
            data=pd.read_csv(folder/f'{policy}.csv')
            trace=json.loads((folder/f'{policy}_top3.json').read_text(encoding='utf-8'))
            selected=[r for r in trace if r['selected']]
            c=Curve(record['settings']['actual'])
            # All experiment origins are the preserved Monday00:00 model origin.
            actual_end_activity=np.array([c.integral(t-60,t)/60 for t in data.end])
            manual_activity=np.array([c.integral(t-60,t)/60 for t in data.manual_end])
            series=(data.category.astype(str)+'|'+data.series.astype(str)).to_numpy()
            same=series[:,None]==series[None,:]
            aids=data.auction_id.to_numpy();start=data.start.to_numpy();end=data.end.to_numpy()
            np.fill_diagonal(same,False)
            close=(np.abs(end[:,None]-end[None,:])<=60)&same
            unknown=(start[None,:]>start[:,None])|((start[None,:]==start[:,None])&(aids[None,:]>aids[:,None]))
            unknown_close=close&unknown
            total=int(close.sum());future=int(unknown_close.sum())
            row=dict(condition=condition,scenario=d['scenario'],seed=d['seed'],policy=policy,
                selected_actual_activity=float(actual_end_activity.mean()),manual_actual_activity=float(manual_activity.mean()),
                duration_hours=float(data.duration_hours.mean()),known_series_supply=float(data.known_series_supply.mean()),
                known_series_near_chosen=float(data.known_series_near_chosen.mean()),realized_series_near=float(close.sum(axis=1).mean()),
                future_registered_near_share=future/total if total else None,
                zero_known_series_near_share=float(data.known_series_near_chosen.eq(0).mean()),
                selected_score_activity=float(np.mean([r['activity'] for r in selected])) if selected else None,
                selected_kernel_conflict=float(np.mean([r['conflict'] for r in selected])) if selected else None,
                zero_selected_kernel_share=float(np.mean([r['conflict']==0 for r in selected])) if selected else None)
            rows.append(row)
    pd.DataFrame(rows).to_csv(dest/'mechanism_accounting.csv',index=False)
    (dest/'README.md').write_text('Descriptive post-run diagnostics only. Future registered listings and actual activity are evaluation outcomes, NEVER recommendation inputs. Similar-series counts use<=60min; policy score uses taxonomy-weighted triangular kernel with strict<60min. No causal interpretation or auction-level IID inference.\n',encoding='utf-8')
    print('Diagnostic markets',len(rows))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--name',required=True);a=ap.parse_args();main(a.name)
