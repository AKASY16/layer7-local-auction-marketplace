package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import java.time.Instant;

public record AuctionCreateResponse(
	Long id,
	Long productId,
	AuctionStatus status,
	boolean finalized,
	long version,
	long startPrice,
	long currentPrice,
	long bidCount,
	AuctionBidResponse leadingBid,
	AuctionBidResponse winningBid,
	Instant startAt,
	Instant endAt,
	Long relistedFromAuctionId,
	Instant serverTime
) {

	public static AuctionCreateResponse from(Auction auction, Instant now) {
		return new AuctionCreateResponse(
			auction.getId(), auction.getProduct().getId(), auction.statusAt(now), auction.isFinalized(),
			auction.getVersion(), auction.getStartPrice(), auction.getCurrentPrice(), 0, null, null,
			auction.getStartAt(), auction.getEndAt(), null, now
		);
	}
}
