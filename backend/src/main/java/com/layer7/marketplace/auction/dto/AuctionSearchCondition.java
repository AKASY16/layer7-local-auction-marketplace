package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.product.domain.Category;

// GET /api/v1/auctions의 검색 조건. 값이 null(keyword는 빈 문자열 포함)이면 그 조건으로 거르지 않는다
public record AuctionSearchCondition(
	Long regionId,
	Category category,
	String keyword,
	AuctionSearchStatus status
) {
}
