package com.layer7.marketplace.trust.dto;

import java.time.Instant;

public record TradingRestrictionResponse(
	String reason,
	Instant endsAt
) {
}
