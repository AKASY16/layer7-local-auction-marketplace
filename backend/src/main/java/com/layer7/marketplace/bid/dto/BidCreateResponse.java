package com.layer7.marketplace.bid.dto;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.bid.domain.BidType;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;

// POST /api/v1/auctions/{auctionId}/bids 응답 (docs/api/auction-bidding.md)
public record BidCreateResponse(
	AcceptedBid acceptedBid,
	AuctionSummary auction,
	BidResolution resolution
) {

	// AutoBid가 없는 지금은 요청자의 Bid가 성립하면 요청자가 곧 선두다
	public static BidCreateResponse leading(Bid bid, Auction auction, Long nextBidAmount, long bidCount, Instant now) {
		User bidder = bid.getBidder();

		return new BidCreateResponse(
			AcceptedBid.from(bid),
			AuctionSummary.from(auction, bidder, bidder.getId(), nextBidAmount, bidCount, now),
			BidResolution.LEADING
		);
	}

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

		public static AuctionSummary from(
			Auction auction,
			User leadingBidder,
			Long currentUserId,
			Long nextBidAmount,
			long bidCount,
			Instant now
		) {
			return new AuctionSummary(
				auction.getId(),
				auction.statusAt(now),
				auction.getVersion(),
				auction.getCurrentPrice(),
				nextBidAmount,
				bidCount,
				LeadingBidder.from(leadingBidder),
				leadingBidder.getId().equals(currentUserId),
				auction.getEndAt(),
				now
			);
		}
	}

	public record LeadingBidder(
		Long id,
		String nickname
	) {

		public static LeadingBidder from(User user) {
			return new LeadingBidder(user.getId(), user.getNickname());
		}
	}
}
