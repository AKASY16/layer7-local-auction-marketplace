package com.layer7.marketplace.auction.controller;

import com.layer7.marketplace.auction.dto.AuctionCreateRequest;
import com.layer7.marketplace.auction.dto.AuctionCreateResponse;
import com.layer7.marketplace.auction.service.AuctionCreationService;
import com.layer7.marketplace.global.security.AuthenticatedUser;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/products/{productId}/auctions")
public class AuctionCreationController {
	private final AuctionCreationService auctionCreationService;

	public AuctionCreationController(AuctionCreationService auctionCreationService) {
		this.auctionCreationService = auctionCreationService;
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public AuctionCreateResponse createAuction(@PathVariable Long productId,
		@AuthenticationPrincipal AuthenticatedUser user, @Valid @RequestBody AuctionCreateRequest request) {
		return auctionCreationService.createAuction(productId, user.userId(), request);
	}
}
