"""Verify every pre-existing file, allowing only the two authorized relocations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BEFORE=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\v2c-retailrocket-20261031')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def main(out):
    if out.exists():raise FileExistsError(out)
    before=json.loads((BEFORE/'project_before.json').read_text(encoding='utf-8'))
    moved=json.loads((BEFORE/'relocation.json').read_text(encoding='utf-8'))
    mapping={r['original_path']:r['destination'] for r in moved}
    missing=[];changed=[]
    for rel,meta in before.items():
        p=ROOT/mapping.get(rel,rel)
        if not p.exists():missing.append(rel)
        elif p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:changed.append(rel)
    allowed=['research/activity_20261031/','src/v2_policy_empirical/','validation/v2_empirical/',
             'data/experiments/v2c-retailrocket-20261031/','data/external/activity_profiles/retailrocket/',
             'research/papers/simonsohn_2010_revalidation/']
    new={};unexpected=[]
    for folder,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in ('.git','.venv','__pycache__')]
        for name in names:
            p=Path(folder)/name;rel=p.relative_to(ROOT).as_posix()
            if rel in before or rel in mapping.values() or p.resolve()==out.resolve():continue
            if not any(rel.startswith(prefix) for prefix in allowed):unexpected.append(rel)
            new[rel]=dict(bytes=p.stat().st_size,sha256=sha(p))
    result=dict(original_files=len(before),unchanged_at_original_path=len(before)-len(mapping),
        authorized_relocations=moved,missing_original=missing,changed_original=changed,
        unexpected_new_paths=unexpected,new_files=new,all_preserved=not missing and not changed and not unexpected,
        no_push_PR_deployment=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    assert result['all_preserved'],{k:result[k] for k in ('missing_original','changed_original','unexpected_new_paths')}
    print('PRESERVED',len(before),'files; moved',len(mapping),'byte-identical files; new',len(new))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();main(a.out)
