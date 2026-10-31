"""Pin added experiment without staging/committing/modifying previous artifacts."""
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\v2b1-recheck-20261031')

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def main():
    target=ROOT/'validation/v2_followup/V2_B_1_v1.json'
    if target.exists():raise FileExistsError(target)
    before=json.loads((OUT/'project_before.json').read_text(encoding='utf-8'))
    missing=[];changed=[];added={}
    for name,row in before.items():
        p=ROOT/name
        if not p.exists():missing.append(name)
        elif sha(p)!=row['sha256']:changed.append(name)
    assert not missing and not changed,(missing,changed)
    for folder,dirs,files in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in ('.git','.venv','__pycache__')]
        for name in files:
            p=Path(folder)/name;relative=p.relative_to(ROOT).as_posix()
            if relative not in before:
                assert relative.startswith(('src/v2_followup/','validation/v2_followup/','data/experiments/v2b1-20261031/')),relative
                added[relative]=sha(p)
    reference=json.loads((ROOT/'validation/v2_choice/results/references.json').read_text(encoding='utf-8'))['file_sha256']
    assert all(sha(Path(p))==h for p,h in reference.items())
    data=json.loads((ROOT/'validation/v2_followup/results/evaluation-1.json').read_text(encoding='utf-8'))
    assert data['all_mandatory_pass'] and data['n_worlds']==18
    for modes in data['datasets'].values():
        assert all(r['structure']['all_pass'] and r['invariants']['all_pass'] for r in modes.values())
        assert modes['legacy']['frozen11_exact'] and modes['v1']['frozen11_exact']
        assert modes['v2b1']['reproducible'] and modes['v2b1']['default_vs_audited11_exact']
    manifest=dict(version='v2-b.1-experimental-v1',model='known-surplus-followup-v1',
        verdict='REVISE / DEFER ADOPTION',default='legacy',branch='codex/v2b1-recheck-20261031',
        n_worlds=18,n_modes=3,n_datasets=54,policy='unchanged seller_default hard close',
        assumptions='ASSUMED; last intent / next organic first slot / no same-visit chain or duplicate',
        new_tunable_numeric_coefficients=0,mandatory_pass=True,
        preserved_previous_files=len(before),all_previous_files_exact=True,
        previous_snapshot_path=str(OUT/'project_before.json'),previous_snapshot_sha256=sha(OUT/'project_before.json'),
        previous_source_manifests={n:sha(ROOT/n) for n in ('BASELINE_V4.json','AUDIT_FIX_v1.json',
            'validation/v2_observe/V2_A_v1.json','validation/v2_choice/V2_B_v1.json') if (ROOT/n).exists()},
        empirical_input_sha256=reference,no_V2C_no_tuning_no_push_no_PR=True,
        added_file_sha256=dict(sorted(added.items())),self_hash_excluded=True)
    target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print('previous',len(before),'exact; added pinned',len(added),'input hashes verified',len(reference))
    print(target)

if __name__=='__main__':main()
