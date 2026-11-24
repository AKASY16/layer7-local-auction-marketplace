package com.layer7.marketplace.bid.dto;

import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.bid.domain.BidType;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;

// 공개 입찰 이력 한 건. 입찰자는 id와 닉네임만 내보낸다 (docs/api/auction-bidding.md)
public record BidHistoryResponse(Long id, long amount, BidType type, Instant createdAt, BidderResponse bidder) {

	public static BidHistoryResponse from(Bid bid) {
		User bidder = bid.getBidder();
		return new BidHistoryResponse(bid.getId(), bid.getAmount(), bid.getType(), bid.getCreatedAt(),
			new BidderResponse(bidder.getId(), bidder.getNickname()));
	}

	public record BidderResponse(Long id, String nickname) {
	}
}
