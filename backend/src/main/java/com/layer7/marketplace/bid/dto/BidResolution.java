package com.layer7.marketplace.bid.dto;

// 입찰 요청 뒤 최종 선두가 누구인지. AutoBid가 없는 지금은 항상 LEADING이다
public enum BidResolution {
	LEADING,
	OUTBID_BY_AUTO_BID
}
