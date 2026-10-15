package com.layer7.marketplace.bid.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

class BidApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-14T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JwtTokenProvider jwtTokenProvider;

	private User seller;
	private User bidder;
	private Auction auction;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
		bidder = fixtures.user();
		auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
	}

	@Test
	@DisplayName("로그인한 회원이 입찰하면 201과 입찰 결과를 명세 형식으로 응답한다")
	void placeBid() {
		// given
		String token = tokenOf(bidder);

		// when
		MvcTestResult result = bid(auction.getId(), token, "{ \"amount\": 10000 }");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.CREATED)
			.bodyJson()
			.isLenientlyEqualTo("""
				{
				  "acceptedBid": { "type": "MANUAL", "amount": 10000, "createdAt": "2026-10-14T03:00:00Z" },
				  "auction": {
				    "id": %d,
				    "status": "OPEN",
				    "version": 1,
				    "currentPrice": 10000,
				    "nextBidAmount": 10500,
				    "bidCount": 1,
				    "leadingBidder": { "id": %d, "nickname": "%s" },
				    "currentUserLeading": true,
				    "endAt": "2026-10-14T04:00:00Z",
				    "serverTime": "2026-10-14T03:00:00Z"
				  },
				  "resolution": "LEADING"
				}
				""".formatted(auction.getId(), bidder.getId(), bidder.getNickname()));
	}

	@Test
	@DisplayName("토큰 없이 입찰하면 401 UNAUTHORIZED로 응답한다")
	void requiresLogin() {
		// when
		MvcTestResult result = bid(auction.getId(), null, "{ \"amount\": 10000 }");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.UNAUTHORIZED)
			.bodyJson()
			.isLenientlyEqualTo("{ \"code\": \"UNAUTHORIZED\" }");
	}

	@Test
	@DisplayName("금액이 없거나 0 이하면 400 VALIDATION_ERROR로 응답한다")
	void validatesAmount() {
		// given
		String token = tokenOf(bidder);

		// when
		MvcTestResult missing = bid(auction.getId(), token, "{}");
		MvcTestResult zero = bid(auction.getId(), token, "{ \"amount\": 0 }");

		// then
		assertThat(missing)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "amount", "code": "NOT_NULL" } ] }
				""");
		assertThat(zero)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "amount", "code": "POSITIVE" } ] }
				""");
	}

	@Test
	@DisplayName("입찰 규칙 위반은 공통 오류 형식으로 응답한다")
	void ruleViolation() {
		// given
		String token = tokenOf(seller);

		// when
		MvcTestResult result = bid(auction.getId(), token, "{ \"amount\": 10000 }");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.FORBIDDEN)
			.bodyJson()
			.isLenientlyEqualTo("""
				{
				  "status": 403,
				  "code": "SELF_BID_FORBIDDEN",
				  "path": "/api/v1/auctions/%d/bids"
				}
				""".formatted(auction.getId()));
	}

	private MvcTestResult bid(Long auctionId, String token, String body) {
		var request = mvc.post()
			.uri("/api/v1/auctions/{auctionId}/bids", auctionId)
			.contentType(MediaType.APPLICATION_JSON)
			.content(body);
		if (token != null) {
			request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + token);
		}
		return request.exchange();
	}

	private String tokenOf(User user) {
		return jwtTokenProvider.createAccessToken(user.getId()).getTokenValue();
	}
}
