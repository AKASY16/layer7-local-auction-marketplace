package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.event.AuctionClosedEvent;
import com.layer7.marketplace.auction.event.AuctionPriceChangedEvent;
import java.time.Instant;

// /topic/auctions/{auctionId}로 보내는 공통 envelope (docs/api/realtime.md "공개 Auction Topic")
public record AuctionEventMessage(
	String type,
	Instant occurredAt,
	Long auctionId,
	long version,
	Object data
) {

	public static AuctionEventMessage from(AuctionPriceChangedEvent event) {
		return new AuctionEventMessage(
			"AUCTION_PRICE_CHANGED",
			event.occurredAt(),
			event.auctionId(),
			event.version(),
			new PriceChangedData(
				event.currentPrice(),
				event.nextBidAmount(),
				event.bidCount(),
				new LeadingBidder(event.leadingBidderId(), event.leadingBidderNickname())
			)
		);
	}

	public static AuctionEventMessage from(AuctionClosedEvent event) {
		return new AuctionEventMessage(
			"AUCTION_STATUS_CHANGED",
			event.occurredAt(),
			event.auctionId(),
			event.version(),
			new StatusChangedData(AuctionStatus.ENDED, true, event.winningBidId(), event.endAt())
		);
	}

	public record PriceChangedData(long currentPrice, Long nextBidAmount, long bidCount, LeadingBidder leadingBidder) {
	}

	public record LeadingBidder(Long id, String nickname) {
	}

	public record StatusChangedData(AuctionStatus status, boolean finalized, Long winningBidId, Instant endAt) {
	}
}
