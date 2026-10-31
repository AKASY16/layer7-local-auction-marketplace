# Retailrocket / Simonsohn V2-C revalidation

Primary experiment: `main-2`. `smoke-2` passed before its dispatch. `main-1` was
interrupted because the inherited uniform control did not apply the shared night
constraint. Its partial outputs and setup-v1 sources remain available and are
excluded from primary results. No performance-based tuning was performed.

Use the project virtualenv with `-B -X utf8` to avoid touching old bytecode:

```powershell
& '.\.venv\Scripts\python.exe' -B -X utf8 validation/v2_empirical/test_empirical.py
& '.\.venv\Scripts\python.exe' -B -X utf8 validation/v2_empirical/run.py --name NEW_NAME --smoke --workers 1
& '.\.venv\Scripts\python.exe' -B -X utf8 validation/v2_empirical/analyze.py --name NEW_NAME --out validation/v2_empirical/results/NEW_ANALYSIS
& '.\.venv\Scripts\python.exe' -B -X utf8 validation/v2_empirical/run.py --name NEW_MAIN --workers 6
```

Use a fresh name and output directory. Existing completed cells are immutable.
`--resume` requires the exact same registered source hashes; interrupted partial
cell directories are preserved and need a fresh experiment name instead of
overwriting. Paths in these commands are relative to the simulator root.

The sources are registered before dispatch. The per-world JSON includes every
profile, condition, seed, metric, check and schedule/state hash. Per-cell CSVs
include unsold-zero outcomes and public supply contexts. TOP3 audit files contain
the candidates actually shown, point-in-time contributors and seller selection.
The raw Retailrocket visitor IDs are not supplied to the auction recommender.

Inference uses paired seeds. Scenario means are formed within a seed before a
confidence interval. The19 source weeks,500 auctions or multiple policies are
not additional independent simulation seeds. Neither the ecommerce profiles nor
the simulator validate actual Korean auction uplift.

The old-policy bridge in the main runner uses each world's old profile. Original
V2-C used a universal korea_evening prior, so scenario A's flat blend makes that
bridge a different prior diagnostic. The supplementary exact-prior bridge must
be used for a like-for-like old-policy comparison; do not label the main bridge
as original V2-C reproduction for A.
