package com.layer7.marketplace.bid.dto;

import com.layer7.marketplace.bid.domain.Bid;
import java.util.List;
import org.springframework.data.domain.Page;

// GET /api/v1/auctions/{auctionId}/bids 응답. 05 명세의 페이지 공통 형식
public record BidHistoryPageResponse(
	List<BidHistoryResponse> content,
	int page,
	int size,
	long totalElements,
	int totalPages
) {

	public static BidHistoryPageResponse from(Page<Bid> result) {
		return new BidHistoryPageResponse(
			result.getContent().stream().map(BidHistoryResponse::from).toList(),
			result.getNumber(),
			result.getSize(),
			result.getTotalElements(),
			result.getTotalPages()
		);
	}
}
