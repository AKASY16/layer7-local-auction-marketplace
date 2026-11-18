package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.user.domain.User;

public record AuctionBidResponse(Long id, long amount, BidderResponse bidder) {

	public static AuctionBidResponse from(Bid bid) {
		if (bid == null) {
			return null;
		}
		User bidder = bid.getBidder();
		return new AuctionBidResponse(bid.getId(), bid.getAmount(),
			new BidderResponse(bidder.getId(), bidder.getNickname()));
	}

	public record BidderResponse(Long id, String nickname) {
	}
}
