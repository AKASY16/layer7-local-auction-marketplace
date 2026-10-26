package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.auction.domain.AuctionStatus;

// GET /api/v1/auctions의 status 쿼리 값. 명세는 논리 상태 READY·OPEN·ENDED만 받으므로 CANCELED 같은 값은 400이 된다
public enum AuctionSearchStatus {
	READY(AuctionStatus.READY),
	OPEN(AuctionStatus.OPEN),
	ENDED(AuctionStatus.ENDED);

	private final AuctionStatus status;

	AuctionSearchStatus(AuctionStatus status) {
		this.status = status;
	}

	public AuctionStatus toAuctionStatus() {
		return status;
	}
}
