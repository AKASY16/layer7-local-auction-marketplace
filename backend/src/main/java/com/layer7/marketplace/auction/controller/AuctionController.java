package com.layer7.marketplace.auction.controller;

import com.layer7.marketplace.auction.dto.AuctionPageResponse;
import com.layer7.marketplace.auction.dto.AuctionSearchCondition;
import com.layer7.marketplace.auction.dto.AuctionSearchStatus;
import com.layer7.marketplace.auction.service.AuctionService;
import com.layer7.marketplace.product.domain.Category;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auctions")
public class AuctionController {

	private final AuctionService auctionService;

	public AuctionController(AuctionService auctionService) {
		this.auctionService = auctionService;
	}

	// 로그인하지 않아도 부를 수 있다 (docs/05-api-spec.md 인증)
	@GetMapping
	public AuctionPageResponse searchAuctions(
		@RequestParam(name = "regionId", required = false) Long regionId,
		@RequestParam(name = "category", required = false) Category category,
		@RequestParam(name = "keyword", required = false)
		@Size(max = 100) String keyword,
		@RequestParam(name = "status", required = false) AuctionSearchStatus status,
		@RequestParam(name = "page", defaultValue = "0")
		@Min(0) int page,
		@RequestParam(name = "size", defaultValue = "20")
		@Min(1) @Max(50) int size
	) {
		return auctionService.searchAuctions(
			new AuctionSearchCondition(regionId, category, keyword, status),
			page,
			size
		);
	}
}
