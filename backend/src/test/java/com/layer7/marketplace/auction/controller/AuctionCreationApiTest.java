package com.layer7.marketplace.auction.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.product.repository.ProductRepository;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

class AuctionCreationApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-18T03:00:00Z");
	private static final Instant END = NOW.plus(Duration.ofHours(1));
	private static final String PATH = "/api/v1/products/{productId}/auctions";

	@Autowired private MockMvc mvc;
	@Autowired private TestFixtures fixtures;
	@Autowired private JwtTokenProvider tokens;
	@Autowired private ProductRepository products;
	@Autowired private JdbcTemplate jdbc;

	private User seller;
	private Product product;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
		product = products.save(Product.create(seller, Category.DIGITAL, "테스트 상품", "상품 설명",
			ProductCondition.GOOD, "사용감 있음"));
	}

	@Test
	@DisplayName("즉시 시작은 최소 기간을 허용하고 상품 지역·카테고리와 OPEN 상태를 저장한다")
	void createImmediately() throws Exception {
		create(product.getId(), seller, request(9_000, null, END))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").isNumber())
			.andExpect(jsonPath("$.productId").value(product.getId().intValue()))
			.andExpect(jsonPath("$.status").value("OPEN"))
			.andExpect(jsonPath("$.finalized").value(false))
			.andExpect(jsonPath("$.version").value(0))
			.andExpect(jsonPath("$.startPrice").value(9_000))
			.andExpect(jsonPath("$.currentPrice").value(9_000))
			.andExpect(jsonPath("$.bidCount").value(0))
			.andExpect(jsonPath("$.leadingBid").value(nullValue()))
			.andExpect(jsonPath("$.winningBid").value(nullValue()))
			.andExpect(jsonPath("$.relistedFromAuctionId").value(nullValue()))
			.andExpect(jsonPath("$.startAt").value(NOW.toString()))
			.andExpect(jsonPath("$.endAt").value(END.toString()))
			.andExpect(jsonPath("$.serverTime").value(NOW.toString()));
		assertThat(jdbc.queryForMap("SELECT status, region_id, category FROM auctions WHERE product_id = ?",
			product.getId()))
			.containsEntry("status", "OPEN")
			.containsEntry("region_id", product.getRegion().getId())
			.containsEntry("category", "DIGITAL");
	}

	@Test
	@DisplayName("최대 예약 시각·진행 기간·시작가의 경계값으로 READY 경매를 생성한다")
	void createScheduled() throws Exception {
		Instant startAt = NOW.plus(Duration.ofDays(7));
		Instant endAt = startAt.plus(Duration.ofDays(7));
		create(product.getId(), seller, request(10_000_000, startAt, endAt))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.status").value("READY"))
			.andExpect(jsonPath("$.startAt").value(startAt.toString()))
			.andExpect(jsonPath("$.endAt").value(endAt.toString()));
		assertThat(jdbc.queryForObject("SELECT status FROM auctions WHERE product_id = ?", String.class,
			product.getId())).isEqualTo("READY");
	}

	@ParameterizedTest
	@CsvSource({",3599", ",604801", "0,3600", "-1,3600", "604801,608401", "7200,3600"})
	@DisplayName("경매 기간 또는 예약 시작 시각이 범위를 벗어나면 거절한다")
	void invalidPeriod(Long startOffset, long endOffset) throws Exception {
		Instant startAt = startOffset == null ? null : NOW.plusSeconds(startOffset);
		create(product.getId(), seller, request(9_000, startAt, NOW.plusSeconds(endOffset)))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("AUCTION_PERIOD_INVALID"));
	}

	@ParameterizedTest
	@CsvSource({"9050,INVALID_PRICE_UNIT", "99,INVALID_PRICE_UNIT", "10000001,AMOUNT_LIMIT_EXCEEDED"})
	@DisplayName("시작가의 가격 단위 위반과 금액 상한 초과를 구분한다")
	void invalidStartPrice(long startPrice, String code) throws Exception {
		create(product.getId(), seller, request(startPrice, null, END))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value(code));
	}

	@Test
	@DisplayName("로그인·소유권·회원 상태·거래 제한을 확인한다")
	void authorization() throws Exception {
		String body = request(9_000, null, END);
		create(product.getId(), null, body).andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
		create(product.getId(), fixtures.user(), body).andExpect(status().isForbidden())
			.andExpect(jsonPath("$.code").value("FORBIDDEN"));
		fixtures.restrictTrading(seller.getId(), NOW.minusSeconds(1), END);
		create(product.getId(), seller, body).andExpect(status().isForbidden())
			.andExpect(jsonPath("$.code").value("USER_RESTRICTED"));
		fixtures.withdraw(seller.getId());
		create(product.getId(), seller, body).andExpect(status().isForbidden())
			.andExpect(jsonPath("$.code").value("ACCOUNT_WITHDRAWN"));
	}

	@Test
	@DisplayName("필수 입력과 판매 가능한 상품 상태를 확인한다")
	void validatesRequestAndProduct() throws Exception {
		create(product.getId(), seller, "{}").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
		String body = request(9_000, null, END);
		create(Long.MAX_VALUE, seller, body).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
		jdbc.update("UPDATE products SET status = 'SOLD' WHERE id = ?", product.getId());
		create(product.getId(), seller, body).andExpect(status().isConflict())
			.andExpect(jsonPath("$.code").value("PRODUCT_NOT_ACTIVE"));
		jdbc.update("UPDATE products SET status = 'DELETED' WHERE id = ?", product.getId());
		create(product.getId(), seller, body).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
	}

	@ParameterizedTest
	@CsvSource({"0,OPEN", "3600,READY"})
	@DisplayName("이미 OPEN 또는 READY 경매가 같은 상품에 있으면 추가 생성을 거절한다")
	void rejectsDuplicate(long startOffset, String state) throws Exception {
		Instant startAt = startOffset == 0 ? null : NOW.plusSeconds(startOffset);
		create(product.getId(), seller, request(9_000, startAt, NOW.plus(Duration.ofHours(2))))
			.andExpect(status().isCreated()).andExpect(jsonPath("$.status").value(state));
		create(product.getId(), seller, request(9_000, null, END)).andExpect(status().isConflict())
			.andExpect(jsonPath("$.code").value("ACTIVE_AUCTION_ALREADY_EXISTS"));
	}

	@Test
	@DisplayName("같은 상품으로 동시에 생성하면 요청 하나만 성공하고 경매도 한 행이다")
	void concurrentCreation() throws Exception {
		CountDownLatch ready = new CountDownLatch(2);
		CountDownLatch start = new CountDownLatch(1);
		Callable<MockHttpServletResponse> create = () -> {
			ready.countDown();
			assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
			return create(product.getId(), seller, request(9_000, null, END)).andReturn().getResponse();
		};
		try (var executor = Executors.newFixedThreadPool(2)) {
			var first = executor.submit(create);
			var second = executor.submit(create);
			assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
			start.countDown();
			var responses = List.of(first.get(20, TimeUnit.SECONDS), second.get(20, TimeUnit.SECONDS));
			assertThat(responses).extracting(MockHttpServletResponse::getStatus).containsExactlyInAnyOrder(201, 409);
			assertThat(responses.stream().filter(response -> response.getStatus() == 409).findFirst().orElseThrow()
				.getContentAsString()).contains("ACTIVE_AUCTION_ALREADY_EXISTS");
		}
		assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM auctions WHERE product_id = ?", Long.class,
			product.getId())).isEqualTo(1L);
	}

	private ResultActions create(long productId, User user, String body) throws Exception {
		var request = post(PATH, productId).contentType(MediaType.APPLICATION_JSON).content(body);
		if (user != null) {
			request.header(HttpHeaders.AUTHORIZATION, "Bearer " + tokens.createAccessToken(user.getId()).getTokenValue());
		}
		return mvc.perform(request);
	}

	private static String request(long startPrice, Instant startAt, Instant endAt) {
		String start = startAt == null ? "null" : "\"" + startAt + "\"";
		return """
			{"startPrice": %d, "startAt": %s, "endAt": "%s"}
			""".formatted(startPrice, start, endAt);
	}
}
