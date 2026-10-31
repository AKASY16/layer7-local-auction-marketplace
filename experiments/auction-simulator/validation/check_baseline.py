"""Freeze and verify the baseline (baseline-v4).

  python validation/check_baseline.py --write    # record hashes of code, config, parameters, data
  python validation/check_baseline.py            # verify files + regenerate all 18 datasets and compare

The manifest (BASELINE_v4.json) lists SHA-256 of every file that defines the
baseline. Verification fails if any listed file changed, or if the current code
does not regenerate byte-identical CSVs. metadata.json is excluded from the data
check because it carries the generation timestamp.
"""
import argparse
import hashlib
import json
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "BASELINE_v4.json"
LABEL = "baseline-v4"
DEFINING = ["src/*.py", "config/*.yaml", "config/scenarios/*.yaml", "calibration/parameters.yaml",
            "calibration/parameter_sources.csv", "calibration/tuned.yaml", "calibration/*.py",
            "calibration/statistical_analysis/*.py", "calibration/statistical_analysis/results/*.json",
            "requirements.txt"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def defining_files():
    out = {}
    for pat in DEFINING:
        for p in sorted(ROOT.glob(pat)):
            out[p.relative_to(ROOT).as_posix()] = sha(p)
    return out


def data_files(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*.csv"))}


def _regen(job):
    scen, seed, out = job
    sys.path.insert(0, str(ROOT / "src"))
    import generate as G
    G.run(Path(scen), seed, Path(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    data_root = ROOT / "data" / "synthetic"
    if a.write:
        m = {"label": LABEL, "note": "Frozen after calibration pass 4. Do not edit these files; experiments write to "
                                     "data/experiments/. Any change to the generator makes a new baseline label.",
             "defining_files": defining_files(), "data_csv": data_files(data_root)}
        MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8")
        print("wrote", MANIFEST, len(m["defining_files"]), "defining files,", len(m["data_csv"]), "data files")
        return
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    now = defining_files()
    changed = sorted(k for k in set(m["defining_files"]) | set(now) if m["defining_files"].get(k) != now.get(k))
    data_now = data_files(data_root)
    data_changed = sorted(k for k in set(m["data_csv"]) | set(data_now) if m["data_csv"].get(k) != data_now.get(k))
    tmp = ROOT / "data" / "_baseline_check"
    shutil.rmtree(tmp, ignore_errors=True)
    base = json.loads(json.dumps(__import__("yaml").safe_load((ROOT / "config" / "baseline.yaml").read_text(encoding="utf-8"))))
    jobs = [(str(ROOT / "config" / "scenarios" / f"scenario_{s}.yaml"), sd, str(tmp / f"scenario_{s}" / f"seed_{sd}"))
            for s in base["scenarios"] for sd in base["seeds"]]
    with ProcessPoolExecutor(a.workers) as ex:
        list(ex.map(_regen, jobs))
    regen = data_files(tmp)
    regen_diff = sorted(k for k in set(m["data_csv"]) | set(regen) if m["data_csv"].get(k) != regen.get(k))
    shutil.rmtree(tmp, ignore_errors=True)
    res = {"label": m["label"], "defining_files_changed": changed, "data_files_changed": data_changed,
           "regenerated_csv_differs": regen_diff, "n_data_files": len(m["data_csv"]),
           "ok": not changed and not data_changed and not regen_diff}
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
