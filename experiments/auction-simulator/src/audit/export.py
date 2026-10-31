"""Reuse the baseline serializer with explicit schemas for empty tables only."""
import copy
import json
from pathlib import Path

import pandas as pd

import config as C
import generate as G
from audit import ENGINE_VERSION

EMPTY_SCHEMAS = {
    'visits': ['event_time', 'buyer_id', 'auction_id', 'event_type', 'cause', 'visit_id'],
    'bids': ['bid_id', 'auction_id', 'buyer_id', 'bid_time', 'bid_amount', 'bid_type', 'price_after',
             'visit_id', 'bid_time_min', 'leader_after_is_bidder'],
    'hidden/decisions': ['time', 'buyer_id', 'auction_id', 'decision', 'visit_id'],
    'hidden/valuations': ['buyer_id', 'auction_id', 'wtp_krw'],
}


def to_tables(world, market, cfg, source):
    view = copy.copy(market)
    if not len(market.events):
        view.events = pd.DataFrame(columns=EMPTY_SCHEMAS['visits'])
    result = G.to_tables(world, view, cfg, source)
    for name, columns in EMPTY_SCHEMAS.items():
        if result[name].empty:
            if name == 'visits':
                columns = ['event_id'] + columns
            result[name] = pd.DataFrame(columns=columns)
    return result


def write_tables(tables, destination, cfg, seed, scenario, source):
    out = Path(destination).resolve()
    allowed = (C.ROOT / 'data/experiments').resolve()
    if out == allowed or not out.is_relative_to(allowed):
        raise ValueError('Audit output must be a NEW directory under data/experiments/')
    # No overwrite, including an earlier audit run. Pick an explicit new name.
    out.mkdir(parents=True, exist_ok=False)
    G.write_tables(tables, out, cfg, seed, scenario, source)
    path = out / 'metadata.json'
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta.update(generator_version=ENGINE_VERSION, engine=ENGINE_VERSION, parent_baseline='baseline-v4',
                audit_changes=['buyer_active_interval', 'open_auction_thickness', 'empty_csv_schemas'])
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
