package com.layer7.marketplace.product;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.product.dto.ProductCreateRequest;
import com.layer7.marketplace.product.repository.ProductRepository;
import com.layer7.marketplace.product.service.ProductRegistrationService;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.EntityManager;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.transaction.support.TransactionTemplate;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;

class ProductApiTest extends IntegrationTest {

	@Autowired private MockMvc mvc;
	@Autowired private TestFixtures fixtures;
	@Autowired private JwtTokenProvider tokens;
	@Autowired private JdbcTemplate jdbc;
	@Autowired private S3Client storage;
	@Autowired private ProductRepository products;
	@Autowired private EntityManager em;
	@Autowired private TransactionTemplate tx;
	@Autowired private ProductRegistrationService registration;

	private User seller;
	private String token;
	private final HttpClient http = HttpClient.newHttpClient();

	@BeforeEach
	void setUp() {
		// 실제 저장소의 서명 시각과 맞춘 뒤 테스트 안에서 필요한 만큼만 시간을 이동한다.
		clock.fixAt(Instant.now(clock).truncatedTo(ChronoUnit.MICROS));
		seller = fixtures.user();
		token = tokenFor(seller);
	}

	@AfterEach
	void closeHttpClient() {
		http.close();
	}

	@Test
	@DisplayName("실제 SeaweedFS에 PUT한 이미지를 순서대로 등록하고 공개 조회·경매 썸네일로 제공한다")
	void uploadCreateGetAndThumbnail() throws Exception {
		// given
		Upload first = issue("image/png", 3);
		Upload second = issue("image/webp", 4);
		put(first, "png");
		put(second, "webp");

		// when
		String body = create(token, List.of(second.key(), first.key()))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.seller.id").value(seller.getId().intValue()))
			.andExpect(jsonPath("$.region.regionCode").value("11200"))
			.andExpect(jsonPath("$.status").value("ACTIVE"))
			.andExpect(jsonPath("$.images[0].sortOrder").value(0))
			.andExpect(jsonPath("$.images[1].sortOrder").value(1))
			.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
		long productId = ((Number)JsonPath.read(body, "$.id")).longValue();
		String thumbnail = JsonPath.read(body, "$.images[0].url");

		// then
		assertThat(thumbnail).endsWith("/product-images/" + second.key());
		assertThat(http.send(HttpRequest.newBuilder(URI.create(thumbnail)).GET().build(),
			HttpResponse.BodyHandlers.ofString()).body()).isEqualTo("webp");
		jdbc.update("UPDATE users SET region_id = (SELECT id FROM regions WHERE region_code = '11680') WHERE id = ?",
			seller.getId());
		mvc.perform(get("/api/v1/products/{id}", productId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.region.regionCode").value("11200"))
			.andExpect(jsonPath("$.images[0].url").value(thumbnail));
		assertThat(uploadStatus(first.key())).isEqualTo("ATTACHED");
		tx.executeWithoutResult(status -> {
			Product product = products.findById(productId).orElseThrow();
			em.persist(Auction.create(product, 1000, Instant.now(clock).minusSeconds(60),
				Instant.now(clock).plusSeconds(3600)));
		});
		mvc.perform(get("/api/v1/auctions").param("keyword", "이미지-" + seller.getId()))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content[0].product.thumbnailUrl").value(thumbnail));
	}

	@Test
	@DisplayName("같은 업로드 key를 다시 등록하면 거절한다")
	void reusedKey() throws Exception {
		// given
		Upload upload = issue("image/jpeg", 3);
		put(upload, "jpg");
		create(token, List.of(upload.key())).andExpect(status().isCreated());
		// when / then
		invalid(create(token, List.of(upload.key())));
		assertThat(productCount()).isEqualTo(1);
	}

	@ParameterizedTest
	@ValueSource(strings = {"OTHER_OWNER", "EXPIRED", "EXACTLY_24_HOURS", "MISSING", "UNKNOWN", "SIZE", "TYPE", "DUPLICATE", "CASE"})
	@DisplayName("소유자·기한·실제 객체·크기·형식·중복·key 대소문자가 틀리면 전체 거절한다")
	void invalidUploads(String scenario) throws Exception {
		// given
		Upload valid = issue("image/png", 3);
		put(valid, "png");
		Upload invalid = issue("image/png", 3);
		put(invalid, "png");
		String invalidKey = invalid.key();
		switch (scenario) {
			case "OTHER_OWNER" -> jdbc.update("UPDATE image_uploads SET user_id = ? WHERE object_key = ?",
				fixtures.user().getId(), invalid.key());
			case "EXPIRED", "EXACTLY_24_HOURS" -> jdbc.update("UPDATE image_uploads SET created_at = ? WHERE object_key = ?",
				LocalDateTime.ofInstant(Instant.now(clock).minus(Duration.ofHours(24))
					.minusSeconds(scenario.equals("EXPIRED") ? 1 : 0), ZoneOffset.UTC), invalid.key());
			case "MISSING" -> storage.deleteObject(r -> r.bucket("product-images").key(invalid.key()));
			case "UNKNOWN" -> invalidKey = "uploads/unknown";
			case "SIZE" -> storage.putObject(r -> r.bucket("product-images").key(invalid.key()).contentType("image/png"),
				RequestBody.fromString("wrong-size"));
			case "TYPE" -> storage.putObject(r -> r.bucket("product-images").key(invalid.key()).contentType("image/jpeg"),
				RequestBody.fromString("png"));
			case "DUPLICATE" -> invalidKey = valid.key();
			case "CASE" -> invalidKey = invalid.key().toUpperCase();
			default -> throw new IllegalArgumentException(scenario);
		}
		// when / then
		invalid(create(token, List.of(valid.key(), invalidKey)));
		assertThat(productCount()).isZero();
		assertThat(uploadStatus(valid.key())).isEqualTo("PENDING");
	}

	@ParameterizedTest
	@ValueSource(ints = {0, 11})
	@DisplayName("상품 이미지가 0장 또는 11장이면 VALIDATION_ERROR를 반환한다")
	void invalidImageCount(int count) throws Exception {
		// given / when / then
		create(token, Collections.nCopies(count, "uploads/key"))
			.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	@Test
	@DisplayName("같은 key의 동시 등록은 정확히 하나만 성공한다")
	void concurrentAttachment() throws Exception {
		// given
		Upload upload = issue("image/png", 3);
		put(upload, "png");
		CountDownLatch ready = new CountDownLatch(2);
		CountDownLatch start = new CountDownLatch(1);
		// when
		try (var executor = Executors.newFixedThreadPool(2)) {
			var results = new ArrayList<java.util.concurrent.Future<Integer>>();
			for (int i = 0; i < 2; i++) {
				results.add(executor.submit(() -> {
					ready.countDown();
					assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
					return create(token, List.of(upload.key())).andReturn().getResponse().getStatus();
				}));
			}
			assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
			start.countDown();
			// then
			List<Integer> codes = List.of(results.get(0).get(20, TimeUnit.SECONDS), results.get(1).get(20, TimeUnit.SECONDS));
			assertThat(codes).containsExactlyInAnyOrder(201, 400);
		}
		assertThat(productCount()).isEqualTo(1);
	}

	@Test
	@DisplayName("저장 직전 다른 요청이 key를 사용했으면 앞서 처리한 ATTACHED 변경도 롤백한다")
	void rollbackPartialAttachment() throws Exception {
		// given: 사전 검증 뒤 저장 트랜잭션 전에 두 번째 key가 사용된 상황
		List<String> keys = List.of(issue("image/png", 3).key(), issue("image/png", 3).key())
			.stream().sorted().toList();
		jdbc.update("UPDATE image_uploads SET status = 'ATTACHED' WHERE object_key = ?", keys.get(1));
		ProductCreateRequest request = new ProductCreateRequest(Category.DIGITAL, "롤백 확인", "상품 설명",
			ProductCondition.GOOD, "사용감 있음", keys);
		// when / then
		assertThatThrownBy(() -> registration.registerProduct(seller.getId(), request))
			.isInstanceOfSatisfying(BusinessException.class,
				exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.INVALID_UPLOAD));
		assertThat(uploadStatus(keys.get(0))).isEqualTo("PENDING");
		assertThat(productCount()).isZero();
	}

	@Test
	@DisplayName("토큰 없는 쓰기는 UNAUTHORIZED이고 탈퇴한 회원은 등록할 수 없다")
	void authenticationAndWithdrawn() throws Exception {
		// given
		Upload upload = issue("image/png", 3);
		put(upload, "png");
		// when / then
		create(null, List.of(upload.key())).andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
		mvc.perform(post("/api/v1/uploads/product-images").contentType(MediaType.APPLICATION_JSON)
			.content("{\"files\":[{\"contentType\":\"image/png\",\"size\":3}]}"))
			.andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
		fixtures.withdraw(seller.getId());
		create(token, List.of(upload.key())).andExpect(status().isForbidden())
			.andExpect(jsonPath("$.code").value("ACCOUNT_WITHDRAWN"));
		assertThat(uploadStatus(upload.key())).isEqualTo("PENDING");
	}

	@Test
	@DisplayName("없는 상품과 삭제된 상품은 공개 조회할 수 없다")
	void productNotFound() throws Exception {
		// given
		Upload upload = issue("image/png", 3);
		put(upload, "png");
		String body = create(token, List.of(upload.key())).andExpect(status().isCreated())
			.andReturn().getResponse().getContentAsString();
		Number id = JsonPath.read(body, "$.id");
		jdbc.update("UPDATE products SET status = 'DELETED' WHERE id = ?", id.longValue());
		// when / then
		for (long productId : List.of(id.longValue(), Long.MAX_VALUE)) {
			mvc.perform(get("/api/v1/products/{id}", productId)).andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
		}
	}

	private Upload issue(String type, int size) throws Exception {
		String body = mvc.perform(post("/api/v1/uploads/product-images")
			.header(HttpHeaders.AUTHORIZATION, "Bearer " + token).contentType(MediaType.APPLICATION_JSON)
			.content("{\"files\":[{\"contentType\":\"%s\",\"size\":%d}]}".formatted(type, size)))
			.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		return new Upload(JsonPath.read(body, "$.uploads[0].objectKey"), JsonPath.read(body, "$.uploads[0].uploadUrl"), type);
	}

	private void put(Upload upload, String content) throws Exception {
		assertThat(http.send(HttpRequest.newBuilder(URI.create(upload.url())).header("Content-Type", upload.type())
			.PUT(HttpRequest.BodyPublishers.ofString(content)).build(), HttpResponse.BodyHandlers.ofString()).statusCode())
			.isEqualTo(200);
	}

	private ResultActions create(String accessToken, List<String> keys) throws Exception {
		String imageKeys = keys.stream().map(key -> "\"" + key + "\"").collect(java.util.stream.Collectors.joining(","));
		var request = post("/api/v1/products").contentType(MediaType.APPLICATION_JSON)
			.header("Idempotency-Key", "ignored-in-p1")
			.content("""
				{"category":"DIGITAL","title":"이미지-%d","description":"상품 설명",
				"condition":"GOOD","conditionDescription":"사용감 있음","imageKeys":[%s]}
				""".formatted(seller.getId(), imageKeys));
		if (accessToken != null) request.header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken);
		return mvc.perform(request);
	}

	private void invalid(ResultActions result) throws Exception {
		result.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_UPLOAD"));
	}

	private String tokenFor(User user) {
		return tokens.createAccessToken(user.getId()).getTokenValue();
	}

	private String uploadStatus(String key) {
		return jdbc.queryForObject("SELECT status FROM image_uploads WHERE object_key = ?", String.class, key);
	}

	private long productCount() {
		return jdbc.queryForObject("SELECT COUNT(*) FROM products WHERE seller_id = ?", Long.class, seller.getId());
	}

	private record Upload(String key, String url, String type) {
	}
}
