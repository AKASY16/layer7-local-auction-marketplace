"""Verify previous artifacts, fixed execution sources and new result checksums."""
import hashlib
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\v2c-policy-evaluation-20261031')
RES=ROOT/'validation/v2_policy/results'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(1048576),b''):h.update(x)
    return h.hexdigest()

def preserve():
    before=json.loads((OUT/'project_before.json').read_text(encoding='utf-8'))
    changed=[];missing=[]
    for name,r in before.items():
        p=ROOT/name
        if not p.exists():missing.append(name)
        elif sha(p)!=r['sha256']:changed.append(name)
    assert not changed and not missing,(changed,missing)
    result=dict(all_old_files_exact=True,n_preserved=len(before),changed=changed,missing=missing,
        excludes=['.git','.venv','__pycache__'],snapshot_sha256=sha(OUT/'project_before.json'))
    (RES/'preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (OUT/'preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return before,result

def main():
    before,preservation=preserve()
    data=json.loads((RES/'evaluation-2.json').read_text(encoding='utf-8'))
    flat=[r for cases in data['datasets'].values() for r in cases.values()]
    assert len(flat)==729 and sum(r['repeat_tested'] for r in flat)==343
    assert sum(r['instrumented_RNG_heap'] for r in flat)==12
    assert all(r['invariants']['all_pass'] and (not r['repeat_tested'] or r['reproduced']) for r in flat)
    assert all(sha(ROOT/n)==h for n,h in data['sources'].items())
    for key,cases in data['datasets'].items():
        for policy,r in cases.items():
            p=ROOT/'data/experiments/v2c-20261031/evaluation-2'/key/policy
            assert json.loads((p/'record.json').read_text(encoding='utf-8'))==r
            assert all(sha(p/n)==h for n,h in r['output_sha256'].items())
    spec=json.loads((RES/'specification_source.json').read_text(encoding='utf-8'))
    assert sha(Path(spec['original_path']))==sha(Path(spec['copy_path']))==spec['sha256']
    print('PASS729 market checksums,343repeats,12RNG/heap pairs; previous',len(before),'files exact')

if __name__=='__main__':main()
