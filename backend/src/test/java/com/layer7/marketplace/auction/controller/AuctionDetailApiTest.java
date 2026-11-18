package com.layer7.marketplace.auction.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.service.AuctionService;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

class AuctionDetailApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-18T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired private MockMvc mvc;
	@Autowired private TestFixtures fixtures;
	@Autowired private JwtTokenProvider tokens;
	@Autowired private AuctionService auctions;
	@Autowired private JdbcTemplate jdbc;

	@Test
	@DisplayName("상품 등록부터 경매 생성·입찰·마감·낙찰까지 공개 상세에서 확인한다")
	void registeredProductThroughFinalization() throws Exception {
		// given: 실제 업로드 URL의 서명 시각과 맞춘다.
		Instant now = Instant.now(clock).truncatedTo(ChronoUnit.MICROS);
		clock.fixAt(now);
		User seller = fixtures.user();
		User bidder = fixtures.user();
		String product = registerProductWithImage(seller);
		long productId = idAt(product, "$.id");
		String imageUrl = JsonPath.read(product, "$.images[0].url");
		Instant endAt = now.plus(HOUR);

		String created = mvc.perform(post("/api/v1/products/{id}/auctions", productId)
			.header(HttpHeaders.AUTHORIZATION, bearer(seller)).contentType(MediaType.APPLICATION_JSON)
			.content("""
				{"startPrice":9000,"startAt":null,"endAt":"%s"}
				""".formatted(endAt)))
			.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		long auctionId = idAt(created, "$.id");

		detail(auctionId).andExpect(status().isOk())
			.andExpect(jsonPath("$.id").value(auctionId))
			.andExpect(jsonPath("$.status").value("OPEN"))
			.andExpect(jsonPath("$.finalized").value(false))
			.andExpect(jsonPath("$.version").value(0))
			.andExpect(jsonPath("$.startAt").value(now.toString()))
			.andExpect(jsonPath("$.endAt").value(endAt.toString()))
			.andExpect(jsonPath("$.serverTime").value(now.toString()))
			.andExpect(jsonPath("$.startPrice").value(9_000))
			.andExpect(jsonPath("$.currentPrice").value(9_000))
			.andExpect(jsonPath("$.nextBidAmount").value(9_000))
			.andExpect(jsonPath("$.bidCount").value(0))
			.andExpect(jsonPath("$.leadingBid").value(nullValue()))
			.andExpect(jsonPath("$.winningBid").value(nullValue()))
			.andExpect(jsonPath("$.relistedFromAuctionId").value(nullValue()))
			.andExpect(jsonPath("$.product.id").value(productId))
			.andExpect(jsonPath("$.product.images[0].url").value(imageUrl))
			.andExpect(jsonPath("$.appends").isArray())
			.andExpect(jsonPath("$.appends").isEmpty());

		// when / then: 수동입찰 응답과 상세 응답의 version 및 선두를 비교한다.
		String bid = placeBid(auctionId, bidder, 10_000);
		long bidId = idAt(bid, "$.acceptedBid.id");
		long bidVersion = idAt(bid, "$.auction.version");
		detail(auctionId).andExpect(status().isOk())
			.andExpect(jsonPath("$.version").value(bidVersion))
			.andExpect(jsonPath("$.currentPrice").value(10_000))
			.andExpect(jsonPath("$.nextBidAmount").value(10_500))
			.andExpect(jsonPath("$.bidCount").value(1))
			.andExpect(jsonPath("$.leadingBid.id").value(bidId))
			.andExpect(jsonPath("$.leadingBid.amount").value(10_000))
			.andExpect(jsonPath("$.leadingBid.bidder.id").value(bidder.getId()))
			.andExpect(jsonPath("$.leadingBid.bidder.nickname").value(bidder.getNickname()))
			.andExpect(jsonPath("$.winningBid").value(nullValue()));

		clock.fixAt(endAt);
		detail(auctionId).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("ENDED"))
			.andExpect(jsonPath("$.finalized").value(false))
			.andExpect(jsonPath("$.version").value(bidVersion))
			.andExpect(jsonPath("$.nextBidAmount").value(nullValue()))
			.andExpect(jsonPath("$.leadingBid.id").value(bidId))
			.andExpect(jsonPath("$.winningBid").value(nullValue()));

		assertThat(auctions.closeAuction(auctionId)).isTrue();
		detail(auctionId).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("ENDED"))
			.andExpect(jsonPath("$.finalized").value(true))
			.andExpect(jsonPath("$.version").value(bidVersion + 1))
			.andExpect(jsonPath("$.winningBid.id").value(bidId))
			.andExpect(jsonPath("$.winningBid.amount").value(10_000))
			.andExpect(jsonPath("$.winningBid.bidder.id").value(bidder.getId()))
			.andExpect(jsonPath("$.winningBid.bidder.nickname").value(bidder.getNickname()));
	}

	@Test
	@DisplayName("시작 시각을 지나면 저장 상태 READY인 경매도 OPEN으로 반환하고 유찰을 표시한다")
	void scheduledThroughNoWinner() throws Exception {
		clock.fixAt(NOW);
		Auction auction = fixtures.auction(fixtures.user(), 9_000, NOW.plus(HOUR), NOW.plus(HOUR.multipliedBy(2)));
		long id = auction.getId();
		detail(id).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("READY"))
			.andExpect(jsonPath("$.nextBidAmount").value(nullValue()));

		clock.advance(HOUR);
		detail(id).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("OPEN"))
			.andExpect(jsonPath("$.nextBidAmount").value(9_000))
			.andExpect(jsonPath("$.product.images").isEmpty());
		assertThat(jdbc.queryForObject("SELECT status FROM auctions WHERE id = ?", String.class, id)).isEqualTo("READY");

		clock.advance(HOUR);
		assertThat(auctions.closeAuction(id)).isTrue();
		detail(id).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("ENDED"))
			.andExpect(jsonPath("$.finalized").value(true))
			.andExpect(jsonPath("$.nextBidAmount").value(nullValue()))
			.andExpect(jsonPath("$.winningBid").value(nullValue()));
	}

	@Test
	@DisplayName("상한 가격도 첫 입찰에 허용하고 상한에 도달하면 다음 입찰가가 없다")
	void bidAtAmountLimit() throws Exception {
		clock.fixAt(NOW);
		Auction auction = fixtures.auction(fixtures.user(), 10_000_000, NOW, NOW.plus(HOUR));
		detail(auction.getId()).andExpect(status().isOk())
			.andExpect(jsonPath("$.nextBidAmount").value(10_000_000));
		placeBid(auction.getId(), fixtures.user(), 10_000_000);
		detail(auction.getId()).andExpect(status().isOk())
			.andExpect(jsonPath("$.nextBidAmount").value(nullValue()));
	}

	@Test
	@DisplayName("취소 상태의 상세는 입찰 불가이며 삭제된 상품과 없는 경매는 404다")
	void canceledAndNotFound() throws Exception {
		clock.fixAt(NOW);
		Auction auction = fixtures.auction(fixtures.user(), 9_000, NOW, NOW.plus(HOUR));
		fixtures.storeAuctionStatus(auction.getId(), AuctionStatus.CANCELED);
		detail(auction.getId()).andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("CANCELED"))
			.andExpect(jsonPath("$.finalized").value(true))
			.andExpect(jsonPath("$.nextBidAmount").value(nullValue()));

		jdbc.update("UPDATE products SET status = 'DELETED' WHERE id = ?", auction.getProduct().getId());
		detail(auction.getId()).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
		detail(Long.MAX_VALUE).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
	}

	private String registerProductWithImage(User seller) throws Exception {
		String authorization = bearer(seller);
		String upload = mvc.perform(post("/api/v1/uploads/product-images")
			.header(HttpHeaders.AUTHORIZATION, authorization).contentType(MediaType.APPLICATION_JSON)
			.content("""
				{"files":[{"contentType":"image/png","size":3}]}
				"""))
			.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		String key = JsonPath.read(upload, "$.uploads[0].objectKey");
		String url = JsonPath.read(upload, "$.uploads[0].uploadUrl");
		try (HttpClient http = HttpClient.newHttpClient()) {
			HttpRequest put = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(10))
				.header(HttpHeaders.CONTENT_TYPE, "image/png").PUT(HttpRequest.BodyPublishers.ofString("png")).build();
			assertThat(http.send(put, HttpResponse.BodyHandlers.discarding()).statusCode()).isEqualTo(200);
		}
		return mvc.perform(post("/api/v1/products")
			.header(HttpHeaders.AUTHORIZATION, authorization).contentType(MediaType.APPLICATION_JSON)
			.content("""
				{"category":"DIGITAL","title":"테스트 상품","description":"상품 설명",
				"condition":"GOOD","conditionDescription":"사용감 있음","imageKeys":["%s"]}
				""".formatted(key)))
			.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
	}

	private String placeBid(long id, User bidder, long amount) throws Exception {
		return mvc.perform(post("/api/v1/auctions/{id}/bids", id)
			.header(HttpHeaders.AUTHORIZATION, bearer(bidder)).contentType(MediaType.APPLICATION_JSON)
			.content("{\"amount\":%d}".formatted(amount)))
			.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
	}

	private ResultActions detail(long id) throws Exception {
		return mvc.perform(get("/api/v1/auctions/{id}", id));
	}

	private String bearer(User user) {
		return "Bearer " + tokens.createAccessToken(user.getId()).getTokenValue();
	}

	private static long idAt(String json, String path) {
		return ((Number) JsonPath.read(json, path)).longValue();
	}
}
