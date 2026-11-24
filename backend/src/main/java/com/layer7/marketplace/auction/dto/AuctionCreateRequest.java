package com.layer7.marketplace.auction.dto;

import jakarta.validation.constraints.NotNull;
import java.time.Instant;

public record AuctionCreateRequest(
	@NotNull Long startPrice,
	Instant startAt,
	@NotNull Instant endAt
) {
}
