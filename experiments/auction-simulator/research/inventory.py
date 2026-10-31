"""Step 1: inventory every file under the raw data folder (read-only).

Writes research/source_inventory.csv and research/inventory_details.json.
Archives are extracted to a work directory outside the raw folder.

usage: python research/inventory.py --data ~/Desktop/Data --work <extract dir>
"""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def dataset_of(rel):
    s = rel.lower()
    if s.startswith("jank"):
        return "JankShmueli"
    if s.startswith("swoopo"):
        return "Swoopo"
    if s.startswith("maxsold"):
        return "MaxSold"
    if s.startswith("shopgoodwill"):
        return "ShopGoodwill_ebay-sold-comps"
    return "unknown"


def profile_frame(df):
    out = {"rows": int(len(df)), "columns": {}}
    for c in df.columns:
        s = df[c]
        out["columns"][str(c)] = {
            "dtype": str(s.dtype),
            "null": int(s.isna().sum()),
            "n_unique": int(s.nunique(dropna=True)),
            "example": None if s.dropna().empty else str(s.dropna().iloc[0])[:60],
        }
    out["duplicate_rows"] = int(df.duplicated().sum())
    return out


def profile_parquet(path):
    con = duckdb.connect()
    p = str(path).replace("\\", "/")
    desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p}')").fetchall()
    n = con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
    cols = {}
    for name, typ, *_ in desc:
        q = f'SELECT count(*) - count("{name}"), approx_count_distinct("{name}") FROM read_parquet(\'{p}\')'
        nulls, nuniq = con.execute(q).fetchone()
        ex = con.execute(f'SELECT CAST("{name}" AS VARCHAR) FROM read_parquet(\'{p}\') WHERE "{name}" IS NOT NULL LIMIT 1').fetchone()
        cols[name] = {"dtype": typ, "null": int(nulls), "n_unique_approx": int(nuniq),
                      "example": None if ex is None else str(ex[0])[:60]}
    return {"rows": int(n), "columns": cols}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path.home() / "Desktop" / "Data"))
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    data, work = Path(a.data), Path(a.work)
    work.mkdir(parents=True, exist_ok=True)

    rows, details = [], {}
    for path in sorted(data.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(data).as_posix()
        ds = dataset_of(rel)
        rec = {"dataset": ds, "relative_path": rel, "bytes": path.stat().st_size,
               "sha256": sha256(path), "format": path.suffix.lower().lstrip("."),
               "rows": None, "n_columns": None, "role": ""}
        try:
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path, low_memory=False)
                prof = profile_frame(df)
                rec["rows"], rec["n_columns"] = prof["rows"], len(prof["columns"])
                details[rel] = prof
            elif path.suffix.lower() == ".parquet":
                prof = profile_parquet(path)
                rec["rows"], rec["n_columns"] = prof["rows"], len(prof["columns"])
                details[rel] = prof
            elif rel.endswith(".tar.gz"):
                with tarfile.open(path) as tf:
                    members = [m for m in tf.getmembers() if m.isfile()]
                    tf.extractall(work, filter="data")
                rec["role"] = "archive -> " + ", ".join(m.name for m in members)
                for m in members:
                    xp = work / m.name
                    if xp.suffix == ".tsv":
                        df = pd.read_csv(xp, sep="\t", low_memory=False)
                        prof = profile_frame(df)
                        details[f"{rel}::{m.name}"] = prof
                        rows.append({"dataset": ds, "relative_path": f"{rel}::{m.name}", "bytes": xp.stat().st_size,
                                     "sha256": sha256(xp), "format": "tsv", "rows": prof["rows"],
                                     "n_columns": len(prof["columns"]), "role": "extracted"})
        except Exception as e:  # keep going; record the failure
            rec["role"] = f"READ ERROR: {e}"
        rows.append(rec)

    out = ROOT / "research"
    pd.DataFrame(rows).to_csv(out / "source_inventory.csv", index=False, encoding="utf-8")
    (out / "inventory_details.json").write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    print(pd.DataFrame(rows)[["dataset", "relative_path", "rows", "n_columns", "role"]].to_string())


if __name__ == "__main__":
    main()
