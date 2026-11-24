package com.layer7.marketplace.bid.controller;

import com.layer7.marketplace.bid.dto.BidCreateRequest;
import com.layer7.marketplace.bid.dto.BidCreateResponse;
import com.layer7.marketplace.bid.dto.BidHistoryPageResponse;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.AuthenticatedUser;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auctions/{auctionId}/bids")
public class BidController {

	private final BidService bidService;

	public BidController(BidService bidService) {
		this.bidService = bidService;
	}

	// 로그인하지 않아도 부를 수 있다 (SecurityConfig, docs/api/auction-bidding.md)
	@GetMapping
	public BidHistoryPageResponse getBidHistory(
		@PathVariable Long auctionId,
		@RequestParam(name = "page", defaultValue = "0")
		@Min(0) int page,
		@RequestParam(name = "size", defaultValue = "20")
		@Min(1) @Max(50) int size
	) {
		return bidService.getBidHistory(auctionId, page, size);
	}

	// Idempotency-Key 헤더는 보내도 되지만, 중복 요청 처리는 다음 스프린트에서 붙인다
	@PostMapping
	public ResponseEntity<BidCreateResponse> placeBid(
		@PathVariable Long auctionId,
		@AuthenticationPrincipal AuthenticatedUser user,
		@Valid @RequestBody BidCreateRequest request
	) {
		if (user == null) {
			throw new BusinessException(ErrorCode.UNAUTHORIZED);
		}

		BidCreateResponse response = bidService.placeManualBid(auctionId, user.userId(), request.amount());

		return ResponseEntity.status(HttpStatus.CREATED).body(response);
	}
}
