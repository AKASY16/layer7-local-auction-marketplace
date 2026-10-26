package com.layer7.marketplace.auction.dto;

import java.util.List;
import org.springframework.data.domain.Page;

// GET /api/v1/auctions 응답. 05 명세의 페이지 공통 형식
public record AuctionPageResponse(
	List<AuctionSummaryResponse> content,
	int page,
	int size,
	long totalElements,
	int totalPages
) {

	public static AuctionPageResponse from(Page<AuctionSummaryResponse> result) {
		return new AuctionPageResponse(
			result.getContent(),
			result.getNumber(),
			result.getSize(),
			result.getTotalElements(),
			result.getTotalPages()
		);
	}
}
