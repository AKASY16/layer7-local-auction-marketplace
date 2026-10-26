package com.layer7.marketplace.auction.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

class AuctionApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-26T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("로그인하지 않아도 경매 목록을 명세 형식으로 응답한다")
	void searchWithoutLogin() {
		// given
		clock.fixAt(NOW);
		String tag = "목록" + UUID.randomUUID().toString().substring(0, 8);
		User seller = fixtures.user();
		Auction auction = fixtures.auction(
			seller, tag + " 기계식 키보드", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		Long regionId = jdbcTemplate.queryForObject(
			"SELECT id FROM regions WHERE region_code = '11200'", Long.class);

		// when
		MvcTestResult result = mvc.get()
			.uri("/api/v1/auctions")
			.param("keyword", tag)
			.param("status", "OPEN")
			.exchange();

		// then
		assertThat(result)
			.hasStatusOk()
			.bodyJson()
			.isLenientlyEqualTo("""
				{
				  "content": [
				    {
				      "auctionId": %d,
				      "status": "OPEN",
				      "finalized": false,
				      "currentPrice": 10000,
				      "startAt": "2026-10-26T02:00:00Z",
				      "endAt": "2026-10-26T04:00:00Z",
				      "product": {
				        "id": %d,
				        "title": "%s 기계식 키보드",
				        "category": "DIGITAL",
				        "condition": "GOOD",
				        "thumbnailUrl": null,
				        "region": { "id": %d, "sigunguName": "성동구" }
				      }
				    }
				  ],
				  "page": 0,
				  "size": 20,
				  "totalElements": 1,
				  "totalPages": 1
				}
				""".formatted(auction.getId(), auction.getProduct().getId(), tag, regionId));
	}

	@Test
	@DisplayName("status에 READY·OPEN·ENDED가 아닌 값(CANCELED 포함)을 주면 400 VALIDATION_ERROR로 응답한다")
	void rejectsUnknownStatus() {
		// when
		MvcTestResult canceled = mvc.get().uri("/api/v1/auctions").param("status", "CANCELED").exchange();
		MvcTestResult unknown = mvc.get().uri("/api/v1/auctions").param("status", "SOMETHING").exchange();

		// then
		assertThat(canceled)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("{ \"code\": \"VALIDATION_ERROR\" }");
		assertThat(unknown)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("{ \"code\": \"VALIDATION_ERROR\" }");
	}

	@Test
	@DisplayName("페이지 크기가 50을 넘거나 검색어가 100자를 넘으면 400 VALIDATION_ERROR로 응답한다")
	void validatesPageAndKeyword() {
		// when
		MvcTestResult tooLarge = mvc.get().uri("/api/v1/auctions").param("size", "51").exchange();
		MvcTestResult tooLong = mvc.get().uri("/api/v1/auctions").param("keyword", "가".repeat(101)).exchange();

		// then
		assertThat(tooLarge)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "size", "code": "MAX" } ] }
				""");
		assertThat(tooLong)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "keyword", "code": "SIZE" } ] }
				""");
	}
}
