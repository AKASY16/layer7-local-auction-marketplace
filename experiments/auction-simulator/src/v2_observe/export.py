"""Keep all eleven audit CSVs intact; add separate, explicit diagnostic schemas."""
import json
from pathlib import Path

import pandas as pd

from audit import export as audit_export
from . import ENGINE_VERSION, PARENT_ENGINE
from .metrics import WINDOW_HOURS, CATALOG_FIELDS

COMMON = ['trace_id', 'time_min', 'engine_log_length']
SCHEMAS = {
    'participation': COMMON + ['buyer_id', 'stage', 'N_near_end_count', 'participation_multiplier',
                             'attention_multiplier', 'window_hours', 'candidate_index', 'accepted', 'observation_id'],
    'market_context': COMMON + ['auction_id', 'scope', 'observation_id', 'M_similarity_weighted',
                              'M_positive_similarity_count', 'M_catalog_proxy_count', 'scheduled_end_min', 'live_end_min'] +
                      [f'T_{clock}_{h}h_{suffix}' for h in WINDOW_HOURS for clock in ('live', 'scheduled')
                       for suffix in ('weighted', 'catalog_proxy_count')],
    'awareness_events': COMMON + ['observation_id', 'visit_id', 'view_order', 'known_before_current_view',
                                 'known_count_before', 'previous_seen_min', 'previous_minimum_acceptable',
                                 'previous_seen_live_end_min', 'buyer_id', 'auction_id', 'first_seen_min',
                                 'last_seen_min', 'mode', 'observed_price', 'minimum_acceptable',
                                 'seen_scheduled_end_min', 'seen_live_end_min', 'known_count_after'],
    'purchase_state': COMMON + ['buyer_id', 'auction_id', 'stage', 'observation_id', 'budget', 'spent',
                               'committed', 'uncommitted_budget', 'leading_auction_ids', 'won_auction_ids'],
    'decision_context': COMMON + ['observation_id', 'buyer_id', 'auction_id', 'visit_id', 'mode', 'view_order',
                                 'cached_wtp_before', 'minimum_acceptable_before', 'cached_wtp_after', 'wtp_status',
                                 'cached_quote_surplus_after_legacy', 'legacy_decisions', 'submitted_bids'],
    'known_alternatives': ['buyer_id', 'auction_id', 'first_seen_min', 'last_seen_min', 'mode', 'observed_price',
                           'minimum_acceptable', 'seen_scheduled_end_min', 'seen_live_end_min'],
}
JSON_COLUMNS = ('leading_auction_ids', 'won_auction_ids', 'legacy_decisions')


def diagnostic_tables(market):
    o = market.observer
    records = dict(o.records) if o is not None else {}
    records['known_alternatives'] = o.awareness.final_rows() if o is not None else []
    result = {}
    for name, columns in SCHEMAS.items():
        rows = records.get(name, [])
        frame = pd.DataFrame(rows, columns=columns)
        for column in JSON_COLUMNS:
            if column in frame:
                frame[column] = frame[column].map(lambda x: json.dumps(x, separators=(',', ':')))
        result[name] = frame
    return result


def write_dataset(world, market, destination, seed, scenario, source='seller_default'):
    # audit writer rejects frozen paths, existing dirs, and escapes/symlinks.
    tables = audit_export.to_tables(world, market, world.cfg, source)
    audit_export.write_tables(tables, destination, world.cfg, seed, scenario, source)
    destination = Path(destination).resolve()
    diagnostics = diagnostic_tables(market)
    path = destination / 'diagnostics'
    path.mkdir()
    for name, frame in diagnostics.items():
        frame.to_csv(path / (name + '.csv'), index=False, encoding='utf-8')
    metadata_path = destination / 'metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata.update(generator_version=ENGINE_VERSION, engine=ENGINE_VERSION, parent_engine=PARENT_ENGINE,
                    observer_enabled=market.observer is not None,
                    diagnostic_schema_version='v2a-1', diagnostic_files=list(SCHEMAS),
                    diagnostic_row_counts={k: len(v) for k, v in diagnostics.items()},
                    diagnostic_time={'unit': 'minutes since World.origin', 'origin': world.origin.isoformat(),
                                     'timezone': 'World.origin UTC offset; no inferred DST relabeling',
                                     'engine_log_length': 'existing log append position; not heap pop sequence',
                                     'trace_id': 'observer emission order; never engine queue sequence'},
                    diagnostic_definitions={
                        'N': 'Legacy near-ending category participation signal, not M/T',
                        'M': 'Currently listed/open other auctions; weighted by unchanged legacy similarity',
                        'T': 'Subset of same M with end gap <= h; live and scheduled end gaps separate',
                        'T_windows_hours': list(WINDOW_HOURS),
                        'catalog_proxy': {'fields': list(CATALOG_FIELDS), 'verified_SKU': False,
                                          'note': 'Synthetic attribute match; missing identity is unknown, not zero'},
                        'registration': 'After actual LIST, before its alerts; later same-time LISTs excluded',
                        'A': 'Actual views only; quotes/ends frozen at last view; no automatic refresh',
                        'Q': 'Detached spent/committed/leading/won snapshots; no inferred desired quantity',
                        'cached_wtp': 'Only read existing cache; absent remains missing, no wtp() call',
                        'quote_surplus': 'Cached WTP minus observed minimum; post-legacy diagnostic, not expected surplus'},
                    latent_diagnostic_files=['purchase_state', 'decision_context'],
                    diagnostic_note='Internal observational traces, not a bidder policy or training-ready public inputs. '
                                    'No penalty, WTP adjustment, choice rule, or additional random draw is applied.')
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return tables, diagnostics
