package com.layer7.marketplace.bid.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record BidCreateRequest(
	@NotNull @Positive Long amount
) {
}
