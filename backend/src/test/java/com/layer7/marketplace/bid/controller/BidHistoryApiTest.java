package com.layer7.marketplace.bid.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

class BidHistoryApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-14T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);
	private static final Duration MINUTE = Duration.ofMinutes(1);

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private BidService bidService;

	@Autowired
	private JdbcTemplate jdbc;

	private User seller;
	private User first;
	private User second;
	private Auction auction;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
		first = fixtures.user();
		second = fixtures.user();
		auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
	}

	@Test
	@DisplayName("로그인 없이 조회하면 입찰을 최신순으로, 저장된 금액·시각과 입찰자 id·닉네임만 담아 응답한다")
	void returnsLatestFirstWithoutLogin() {
		// given: 1분 간격으로 3건 입찰
		bidService.placeManualBid(auction.getId(), first.getId(), 10_000);
		clock.advance(MINUTE);
		bidService.placeManualBid(auction.getId(), second.getId(), 10_500);
		clock.advance(MINUTE);
		bidService.placeManualBid(auction.getId(), first.getId(), 11_000);
		List<Map<String, Object>> stored = jdbc.queryForList(
			"SELECT id, amount, created_at FROM bids WHERE auction_id = ? ORDER BY id DESC", auction.getId());

		// when
		MvcTestResult result = history(auction.getId(), "");

		// then: 이메일·비밀번호 해시 같은 필드가 없도록 전체 형식을 그대로 비교한다
		assertThat(stored).hasSize(3);
		assertThat(stored).extracting(row -> ((Number) row.get("amount")).longValue())
			.containsExactly(11_000L, 10_500L, 10_000L);
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("""
				{
				  "content": [
				    { "id": %d, "amount": 11000, "type": "MANUAL", "createdAt": "2026-10-14T03:02:00Z",
				      "bidder": { "id": %d, "nickname": "%s" } },
				    { "id": %d, "amount": 10500, "type": "MANUAL", "createdAt": "2026-10-14T03:01:00Z",
				      "bidder": { "id": %d, "nickname": "%s" } },
				    { "id": %d, "amount": 10000, "type": "MANUAL", "createdAt": "2026-10-14T03:00:00Z",
				      "bidder": { "id": %d, "nickname": "%s" } }
				  ],
				  "page": 0,
				  "size": 20,
				  "totalElements": 3,
				  "totalPages": 1
				}
				""".formatted(
				idAt(stored, 0), first.getId(), first.getNickname(),
				idAt(stored, 1), second.getId(), second.getNickname(),
				idAt(stored, 2), first.getId(), first.getNickname()));
	}

	@Test
	@DisplayName("다른 경매의 입찰은 섞이지 않고, 입찰이 없는 경매는 빈 목록으로 응답한다")
	void excludesOtherAuctions() {
		// given
		Auction other = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		Auction empty = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		bidService.placeManualBid(auction.getId(), first.getId(), 10_000);
		bidService.placeManualBid(other.getId(), second.getId(), 20_000);

		// when
		MvcTestResult mine = history(auction.getId(), "");
		MvcTestResult none = history(empty.getId(), "");

		// then
		assertThat(mine)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "amount": 10000, "bidder": { "id": %d } } ], "totalElements": 1 }
				""".formatted(first.getId()));
		assertThat(none)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("""
				{ "content": [], "page": 0, "size": 20, "totalElements": 0, "totalPages": 0 }
				""");
	}

	@Test
	@DisplayName("page·size로 나누어 조회하면 해당 페이지의 입찰과 전체 개수·페이지 수를 응답한다")
	void paginates() {
		// given
		bidService.placeManualBid(auction.getId(), first.getId(), 10_000);
		bidService.placeManualBid(auction.getId(), second.getId(), 10_500);
		bidService.placeManualBid(auction.getId(), first.getId(), 11_000);

		// when
		MvcTestResult result = history(auction.getId(), "?page=1&size=2");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "amount": 10000 } ], "page": 1, "size": 2, "totalElements": 3, "totalPages": 2 }
				""");
	}

	@Test
	@DisplayName("없는 경매의 입찰 이력을 조회하면 404 RESOURCE_NOT_FOUND로 응답한다")
	void unknownAuction() {
		// when
		MvcTestResult result = history(Long.MAX_VALUE, "");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.NOT_FOUND)
			.bodyJson()
			.isLenientlyEqualTo("{ \"code\": \"RESOURCE_NOT_FOUND\" }");
	}

	@ParameterizedTest
	@CsvSource({
		"?page=-1, page, MIN",
		"?size=0, size, MIN",
		"?size=51, size, MAX"
	})
	@DisplayName("page가 음수이거나 size가 1~50을 벗어나면 400 VALIDATION_ERROR로 응답한다")
	void invalidPage(String query, String field, String code) {
		// when
		MvcTestResult result = history(auction.getId(), query);

		// then
		assertThat(result)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "%s", "code": "%s" } ] }
				""".formatted(field, code));
	}

	private MvcTestResult history(Long auctionId, String query) {
		return mvc.get().uri("/api/v1/auctions/" + auctionId + "/bids" + query).exchange();
	}

	private static long idAt(List<Map<String, Object>> rows, int index) {
		return ((Number) rows.get(index).get("id")).longValue();
	}
}
