package com.layer7.marketplace.user.dto;

import java.time.Instant;

public record TradingRestrictionResponse(
	String reason,
	Instant endsAt
) {
}
