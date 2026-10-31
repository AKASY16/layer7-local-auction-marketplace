"""Load baseline + scenario YAML and the calibrated parameter table."""
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_yaml(p):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load(scenario_path=None, baseline_path=None, overrides=None):
    base = load_yaml(baseline_path or ROOT / "config" / "baseline.yaml")
    scen = load_yaml(scenario_path) if scenario_path else {}
    cfg = deep_merge(base, scen)
    cfg = deep_merge(cfg, overrides or {})
    ptab = load_yaml(ROOT / cfg["parameters_file"])
    params = {k: v["value"] for k, v in ptab["params"].items()}
    params.update(cfg.get("param_overrides") or {})
    cfg["params"] = params
    cfg["parameters_version"] = ptab.get("version")
    return cfg
