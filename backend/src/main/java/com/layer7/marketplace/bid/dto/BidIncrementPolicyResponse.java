package com.layer7.marketplace.bid.dto;

import com.layer7.marketplace.bid.domain.BidIncrementPolicy;
import java.util.List;

// GET /api/v1/bid-increment-policy 응답 (docs/api/auction-bidding.md)
public record BidIncrementPolicyResponse(long minAmount, long maxAmount, List<BandResponse> bands) {

	public static BidIncrementPolicyResponse from(BidIncrementPolicy policy) {
		return new BidIncrementPolicyResponse(policy.minAmount(), policy.maxAmount(),
			policy.bands().stream().map(band -> new BandResponse(band.from(), band.to(), band.unit())).toList());
	}

	public record BandResponse(long from, long to, long unit) {
	}
}
