package com.layer7.marketplace.bid.controller;

import com.layer7.marketplace.bid.domain.BidIncrementPolicy;
import com.layer7.marketplace.bid.dto.BidIncrementPolicyResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

// 로그인 없이 조회한다. 화면은 이 표로 시작가·입찰가를 입력 즉시 검증하고, 최종 검증은 서버가 한다
@RestController
public class BidIncrementPolicyController {

	private final BidIncrementPolicy bidIncrementPolicy;

	public BidIncrementPolicyController(BidIncrementPolicy bidIncrementPolicy) {
		this.bidIncrementPolicy = bidIncrementPolicy;
	}

	@GetMapping("/api/v1/bid-increment-policy")
	public BidIncrementPolicyResponse getPolicy() {
		return BidIncrementPolicyResponse.from(bidIncrementPolicy);
	}
}
