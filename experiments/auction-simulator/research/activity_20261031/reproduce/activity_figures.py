"""Read-only source-derived figures. Bundled Python, no simulated policy tuning."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'research/activity_20261031/retailrocket_analysis'
OUT=ROOT/'research/activity_20261031/figures';OUT.mkdir(parents=True,exist_ok=True)
p=json.loads((BASE/'profiles.json').read_text(encoding='utf-8'));pr=p['profiles']
fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
for key,label in [('unique_active','Unique active visitor IDs'),('views','View events'),('transactions','Transaction item events')]:
    tr=np.array(pr[key]['train']);ev=np.array(pr[key]['evaluation'])
    axes[0,0].step(range(24),tr.mean(axis=0),where='mid',label=label)
    if key=='unique_active':
        axes[0,1].imshow(tr,aspect='auto',vmin=0,vmax=2,cmap='viridis')
        axes[0,1].set_yticks(range(7),['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
        axes[1,0].step(range(24),tr.mean(axis=0),where='mid',label='Train12weeks')
        axes[1,0].step(range(24),ev.mean(axis=0),where='mid',label='Evaluation7weeks')
        for wk in p['weekly_counts']['unique_active']['evaluation']:
            x=np.array(wk);x=x/x.mean();axes[1,0].step(range(24),x.mean(axis=0),where='mid',color='gray',alpha=.25)
        # Keep step values, no subhour interpolation.
        for off in (0,6,9,12,18):
            x=np.roll(tr.ravel(),off).reshape(7,24)
            axes[1,1].step(range(24),x.mean(axis=0),where='mid',label=f'Phase+{off}h')
axes[0,0].set_title('Different observational units: training shapes')
axes[0,1].set_title('Training weekday x UTC-reference hour, mean1')
axes[1,0].set_title('Chronological generalization; gray=heldout weeks')
axes[1,1].set_title('Fixed phase scenarios, NOT inferred Korean clock')
for ax in axes.ravel():
    ax.set_xlabel('Reference/model hour (source local clock UNKNOWN)');ax.set_xticks(range(0,24,3))
    if ax!=axes[0,1]:ax.set_ylabel('Relative activity (weekly mean1)');ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.suptitle('Retailrocket activity transfer: ASSUMED overseas shape transfer, not measured KST demand')
fig.savefig(OUT/'activity_profiles.png',dpi=180);fig.savefig(OUT/'activity_profiles.svg');plt.close(fig)
diagnostics={}
for key in ('unique_active','views','transactions'):
    x=np.array(pr[key]['train']);ev=np.array(pr[key]['evaluation'])
    ci=np.array(pr[key]['bootstrap_week_ci'])
    diagnostics[key]=dict(train_peak_reference_hour=int(x.mean(axis=0).argmax()),
        evaluation_peak_reference_hour=int(ev.mean(axis=0).argmax()),
        train_min=float(x.min()),train_max=float(x.max()),
        cell_week_bootstrap_median_CI_width=float(np.median(ci[2]-ci[0])),
        cell_week_bootstrap_max_CI_width=float(np.max(ci[2]-ci[0])))
(OUT/'profile_diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
print(json.dumps(diagnostics,indent=2))
