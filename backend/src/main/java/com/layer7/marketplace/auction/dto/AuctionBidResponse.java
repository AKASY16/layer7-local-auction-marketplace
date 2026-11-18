package com.layer7.marketplace.auction.dto;

public record AuctionBidResponse(Long id, long amount, BidderResponse bidder) {

	public record BidderResponse(Long id, String nickname) {
	}
}
