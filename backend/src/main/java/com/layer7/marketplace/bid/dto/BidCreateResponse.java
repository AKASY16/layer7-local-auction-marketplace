package com.layer7.marketplace.bid.dto;

import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.bid.domain.BidType;
import java.time.Instant;

// POST /api/v1/auctions/{auctionId}/bids 응답 (docs/api/auction-bidding.md)
public record BidCreateResponse(
	AcceptedBid acceptedBid,
	AuctionSummary auction,
	BidResolution resolution
) {

	public record AcceptedBid(
		Long id,
		BidType type,
		long amount,
		Instant createdAt
	) {

		public static AcceptedBid from(Bid bid) {
			return new AcceptedBid(bid.getId(), bid.getType(), bid.getAmount(), bid.getCreatedAt());
		}
	}

	public record AuctionSummary(
		Long id,
		AuctionStatus status,
		long version,
		long currentPrice,
		// 금액 상한에 도달해 더 입찰할 수 없으면 null
		Long nextBidAmount,
		long bidCount,
		LeadingBidder leadingBidder,
		boolean currentUserLeading,
		Instant endAt,
		Instant serverTime
	) {
	}

	public record LeadingBidder(
		Long id,
		String nickname
	) {
	}
}
