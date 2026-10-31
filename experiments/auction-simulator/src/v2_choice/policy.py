"""Pure comparison of already-observed quotes; no access to Market or future state."""
def compare(now, focal_id, known, free_budget, leading, won, similarity, max_age_min=None):
    focal = known[focal_id]
    if focal['seen_at'] > now:
        raise ValueError('Future focal information')
    own_surplus = focal['wtp'] - focal['ask']
    counters = {'comparisons': 0, 'eligible_alternatives': 0, 'expired': 0,
                'aged_out': 0, 'leading_excluded': 0, 'won_excluded': 0,
                'quote_age_sum_min': 0., 'max_quote_age_min': 0.}
    best = (own_surplus, -focal['seen_end'], -focal_id)
    best_id = focal_id
    for aid in sorted(known):
        if aid == focal_id:
            continue
        row = known[aid]
        if row['seen_at'] > now:
            raise ValueError('Future alternative information')
        if aid in won:
            counters['won_excluded'] += 1
            continue
        if aid in leading:
            counters['leading_excluded'] += 1
            continue
        if row['seen_end'] <= now:
            counters['expired'] += 1
            continue
        age = now - row['seen_at']
        if max_age_min is not None and age > max_age_min:
            counters['aged_out'] += 1
            continue
        if row['ask'] > free_budget or row['wtp'] <= row['ask']:
            continue
        s = similarity(focal_id, aid)
        if not 0 <= s <= 1:
            raise ValueError('Similarity must lie in [0,1]')
        if s == 0:
            continue
        counters['comparisons'] += 1
        counters['eligible_alternatives'] += 1
        counters['quote_age_sum_min'] += age
        counters['max_quote_age_min'] = max(counters['max_quote_age_min'], age)
        score = s * (row['wtp'] - row['ask'])
        rank = (score, -row['seen_end'], -aid)
        if rank > best:
            best, best_id = rank, aid
    if own_surplus <= 0:
        reason = 'choice_no_positive_surplus'
    elif best_id != focal_id:
        reason = 'choice_better_known_alternative'
    else:
        reason = 'choice_allow'
    return {'allow': reason == 'choice_allow', 'reason': reason, 'best_id': best_id,
            'own_surplus': own_surplus, 'best_score': best[0], 'counters': counters}
