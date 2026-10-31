"""Existing eleven tables plus small counters; no full V2-A trace collection."""
import json
from pathlib import Path
from audit import export as E
from . import ENGINE_VERSION, MODEL


def write_dataset(world, market, destination, seed, scenario, source='seller_default'):
    tables=E.to_tables(world,market,world.cfg,source)
    E.write_tables(tables,destination,world.cfg,seed,scenario,source)
    path=Path(destination)/'metadata.json'
    meta=json.loads(path.read_text(encoding='utf-8'))
    experimental=hasattr(market,'_knowledge')
    meta.update(choice_model=MODEL if experimental else 'legacy', experimental_choice=experimental,
                choice_parameter_class='ASSUMED' if experimental else None,
                max_quote_age_min=getattr(market,'_max_quote_age_min',None),
                choice_diagnostics='counters only; no V2-A full observer',
                choice_assumptions=['myopic last-observed ask surplus','similarity-weighted outside comparison',
                                    'fixed personal valuation known on actual view','own bid feedback known',
                                    'no separate owned-good marginal-utility discount','earlier-known-end tie break'] if experimental else [])
    if experimental:
        meta.update(generator_version=ENGINE_VERSION,engine=ENGINE_VERSION,parent_engine='audit-fix-v1')
    path.write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    counts=dict(getattr(market,'_choice_counts',{}))
    (Path(destination)/'choice_counters.json').write_text(json.dumps(counts,indent=2),encoding='utf-8')
    return tables
