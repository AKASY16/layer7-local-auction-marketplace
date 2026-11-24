package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.product.dto.ProductResponse;
import java.time.Instant;
import java.util.List;

public record AuctionDetailResponse(
	Long id,
	AuctionStatus status,
	boolean finalized,
	long version,
	long startPrice,
	long currentPrice,
	Long nextBidAmount,
	long bidCount,
	Instant startAt,
	Instant endAt,
	Instant serverTime,
	AuctionBidResponse leadingBid,
	AuctionBidResponse winningBid,
	Long relistedFromAuctionId,
	ProductResponse product,
	List<?> appends
) {

	public static AuctionDetailResponse from(Auction auction, AuctionStatus status, Long nextBidAmount,
		long bidCount, Instant now, ProductResponse product) {
		Auction relistedFrom = auction.getRelistedFrom();
		return new AuctionDetailResponse(
			auction.getId(), status, auction.isFinalized(), auction.getVersion(), auction.getStartPrice(),
			auction.getCurrentPrice(), nextBidAmount, bidCount, auction.getStartAt(), auction.getEndAt(), now,
			AuctionBidResponse.from(auction.getLeadingBid()), AuctionBidResponse.from(auction.getWinningBid()),
			relistedFrom == null ? null : relistedFrom.getId(), product, List.of()
		);
	}
}
