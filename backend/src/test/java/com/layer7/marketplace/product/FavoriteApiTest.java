package com.layer7.marketplace.product;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/**
 * 관심상품 API. 동시에 등록하는 경우는 {@code FavoriteConcurrencyTest}가 확인한다.
 */
class FavoriteApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-05T03:00:00Z");
	private static final Duration MINUTE = Duration.ofMinutes(1);

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JwtTokenProvider jwtTokenProvider;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private ProductImageStorage storage;

	private User owner;
	private User other;
	private User seller;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		owner = fixtures.user();
		other = fixtures.user();
		seller = fixtures.user();
	}

	@Test
	@DisplayName("등록 → 중복 등록 → 해제 → 중복 해제가 모두 같은 결과를 내고, 다시 등록해도 처음 등록 시각을 유지한다")
	void favoriteAndUnfavoriteAreIdempotent() {
		// given
		Long productId = product("관심 상품");

		// when
		MvcTestResult first = favorite(owner, productId);
		clock.advance(MINUTE);
		MvcTestResult again = favorite(owner, productId);
		Instant favoritedAt = favoritedAt(owner, productId);
		MvcTestResult whileFavorited = check(owner, productId);
		MvcTestResult removed = unfavorite(owner, productId);
		MvcTestResult removedAgain = unfavorite(owner, productId);
		MvcTestResult afterRemoved = check(owner, productId);

		// then
		for (MvcTestResult result : new MvcTestResult[] {first, again, whileFavorited}) {
			assertThat(result)
				.hasStatus(HttpStatus.OK)
				.bodyJson()
				.isStrictlyEqualTo("{ \"productId\": %d, \"favorited\": true }".formatted(productId));
		}
		for (MvcTestResult result : new MvcTestResult[] {removed, removedAgain, afterRemoved}) {
			assertThat(result)
				.hasStatus(HttpStatus.OK)
				.bodyJson()
				.isStrictlyEqualTo("{ \"productId\": %d, \"favorited\": false }".formatted(productId));
		}
		assertThat(favoritedAt).isEqualTo(NOW);
		assertThat(count(owner, productId)).isZero();
	}

	@Test
	@DisplayName("해제는 내 관심상품만 지운다")
	void unfavoriteOnlyMine() {
		// given
		Long productId = product("함께 등록한 상품");
		favorite(owner, productId);
		favorite(other, productId);

		// when
		unfavorite(owner, productId);

		// then
		assertThat(count(owner, productId)).isZero();
		assertThat(count(other, productId)).isEqualTo(1);
		assertThat(check(other, productId))
			.bodyJson()
			.isStrictlyEqualTo("{ \"productId\": %d, \"favorited\": true }".formatted(productId));
	}

	@Test
	@DisplayName("없는 상품이나 삭제된 상품은 등록·해제·조회 모두 404 RESOURCE_NOT_FOUND이고, 관심상품도 바뀌지 않는다")
	void missingOrDeletedProduct() {
		// given
		Long deleted = product("삭제될 상품");
		favorite(owner, deleted);
		setProductStatus(deleted, "DELETED");

		// when / then
		for (Long productId : new Long[] {Long.MAX_VALUE, deleted}) {
			for (MvcTestResult result : new MvcTestResult[] {
				favorite(owner, productId), unfavorite(owner, productId), check(owner, productId)}) {
				assertThat(result)
					.hasStatus(HttpStatus.NOT_FOUND)
					.bodyJson()
					.isLenientlyEqualTo("{ \"code\": \"RESOURCE_NOT_FOUND\" }");
			}
		}
		assertThat(count(owner, deleted)).isEqualTo(1);
	}

	@Test
	@DisplayName("판매된 상품과 내가 판매하는 상품도 등록할 수 있다")
	void soldAndOwnProduct() {
		// given
		Long sold = product("판매된 상품");
		setProductStatus(sold, "SOLD");
		Long own = product("내 상품");

		// when
		MvcTestResult soldResult = favorite(owner, sold);
		MvcTestResult ownResult = favorite(seller, own);

		// then
		assertThat(soldResult).hasStatus(HttpStatus.OK);
		assertThat(ownResult).hasStatus(HttpStatus.OK);
		assertThat(count(owner, sold)).isEqualTo(1);
		assertThat(count(seller, own)).isEqualTo(1);
	}

	@Test
	@DisplayName("탈퇴한 회원은 등록하면 403 ACCOUNT_WITHDRAWN이고, 해제와 조회는 할 수 있다")
	void withdrawnUserCannotFavorite() {
		// given
		Long kept = product("탈퇴 전에 등록한 상품");
		Long blocked = product("탈퇴 뒤에 등록하려는 상품");
		favorite(owner, kept);
		fixtures.withdraw(owner.getId());

		// when
		MvcTestResult favorited = favorite(owner, blocked);
		MvcTestResult checked = check(owner, kept);
		MvcTestResult removed = unfavorite(owner, kept);

		// then
		assertThat(favorited)
			.hasStatus(HttpStatus.FORBIDDEN)
			.bodyJson()
			.isLenientlyEqualTo("{ \"code\": \"ACCOUNT_WITHDRAWN\" }");
		assertThat(count(owner, blocked)).isZero();
		assertThat(checked).hasStatus(HttpStatus.OK);
		assertThat(removed).hasStatus(HttpStatus.OK);
		assertThat(count(owner, kept)).isZero();
	}

	@Test
	@DisplayName("토큰 없이 부르면 네 API 모두 401 UNAUTHORIZED로 응답하고, 관심상품은 생기지 않는다")
	void requiresLogin() {
		// given
		Long productId = product("비로그인 상품");

		// when
		MvcTestResult put = mvc.put().uri("/api/v1/products/{id}/favorite", productId).exchange();
		MvcTestResult delete = mvc.delete().uri("/api/v1/products/{id}/favorite", productId).exchange();
		MvcTestResult get = mvc.get().uri("/api/v1/products/{id}/favorite", productId).exchange();
		MvcTestResult list = mvc.get().uri("/api/v1/users/me/favorites").exchange();

		// then
		for (MvcTestResult result : new MvcTestResult[] {put, delete, get, list}) {
			assertThat(result)
				.hasStatus(HttpStatus.UNAUTHORIZED)
				.bodyJson()
				.isLenientlyEqualTo("{ \"code\": \"UNAUTHORIZED\" }");
		}
		assertThat(jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM favorites WHERE product_id = ?", Long.class, productId)).isZero();
	}

	@Test
	@DisplayName("목록은 내 관심상품만 최신순으로 응답하고, 같은 시각이면 나중에 등록한 것이 먼저다. 삭제된 상품은 빠진다")
	void listsMyFavoritesLatestFirst() {
		// given
		Long oldest = product("가장 먼저 등록");
		Long first = product("같은 시각 먼저 등록");
		Long second = product("같은 시각 나중 등록");
		Long deleted = product("삭제된 상품");
		Long othersOnly = product("다른 사람만 등록");
		favoriteAt(owner, oldest, NOW.minus(MINUTE.multipliedBy(2)));
		favoriteAt(owner, first, NOW);
		favoriteAt(owner, second, NOW);
		favoriteAt(owner, deleted, NOW.plus(MINUTE));
		setProductStatus(deleted, "DELETED");
		favoriteAt(other, othersOnly, NOW.plus(MINUTE));

		// when
		MvcTestResult result = list(owner, "");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{
				  "content": [ { "productId": %d }, { "productId": %d }, { "productId": %d } ],
				  "page": 0, "size": 20, "totalElements": 3, "totalPages": 1
				}
				""".formatted(second, first, oldest));
	}

	@Test
	@DisplayName("목록 항목은 명세 형식으로 응답하고, 썸네일은 첫 이미지이며 이미지가 없으면 null이다")
	void responseFormat() {
		// given
		Long withImages = product("이미지 있는 상품");
		String thumbnailKey = addImage(withImages, 0);
		addImage(withImages, 1);
		Long withoutImages = product("이미지 없는 상품");
		setProductStatus(withoutImages, "SOLD");
		favoriteAt(owner, withoutImages, NOW.minus(MINUTE));
		favoriteAt(owner, withImages, NOW);

		// when
		MvcTestResult result = list(owner, "");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("""
				{
				  "content": [
				    {
				      "productId": %d,
				      "title": "이미지 있는 상품",
				      "category": "DIGITAL",
				      "status": "ACTIVE",
				      "thumbnailUrl": "%s",
				      "favoritedAt": "2026-11-05T03:00:00Z"
				    },
				    {
				      "productId": %d,
				      "title": "이미지 없는 상품",
				      "category": "DIGITAL",
				      "status": "SOLD",
				      "thumbnailUrl": null,
				      "favoritedAt": "2026-11-05T02:59:00Z"
				    }
				  ],
				  "page": 0, "size": 20, "totalElements": 2, "totalPages": 1
				}
				""".formatted(withImages, storage.getPublicUrl(thumbnailKey), withoutImages));
	}

	@Test
	@DisplayName("page·size로 나눠 응답한다")
	void paging() {
		// given
		Long p1 = product("1");
		Long p2 = product("2");
		Long p3 = product("3");
		favoriteAt(owner, p1, NOW.minus(MINUTE.multipliedBy(2)));
		favoriteAt(owner, p2, NOW.minus(MINUTE));
		favoriteAt(owner, p3, NOW);

		// when
		MvcTestResult firstPage = list(owner, "?size=2");
		MvcTestResult secondPage = list(owner, "?size=2&page=1");

		// then
		assertThat(firstPage)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "productId": %d }, { "productId": %d } ], "page": 0, "size": 2, "totalElements": 3, "totalPages": 2 }
				""".formatted(p3, p2));
		assertThat(secondPage)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "productId": %d } ], "page": 1, "size": 2, "totalElements": 3, "totalPages": 2 }
				""".formatted(p1));
	}

	@Test
	@DisplayName("page가 음수이거나 size가 1~50을 벗어나면 400 VALIDATION_ERROR로 응답한다")
	void validatesPaging() {
		// when / then
		assertThat(list(owner, "?page=-1"))
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "page", "code": "MIN" } ] }
				""");
		assertThat(list(owner, "?size=0"))
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "size", "code": "MIN" } ] }
				""");
		assertThat(list(owner, "?size=51"))
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "size", "code": "MAX" } ] }
				""");
	}

	private Long product(String title) {
		return fixtures.product(seller, title).getId();
	}

	// 등록 시각을 정하려고 잠시 시계를 옮겼다가 되돌린다
	private void favoriteAt(User user, Long productId, Instant favoritedAt) {
		Instant before = clock.instant();
		clock.fixAt(favoritedAt);
		assertThat(favorite(user, productId)).hasStatus(HttpStatus.OK);
		clock.fixAt(before);
	}

	private void setProductStatus(Long productId, String status) {
		jdbcTemplate.update("UPDATE products SET status = ? WHERE id = ?", status, productId);
	}

	private String addImage(Long productId, int sortOrder) {
		String key = "uploads/" + UUID.randomUUID();
		jdbcTemplate.update(
			"INSERT INTO product_images (product_id, object_key, sort_order, created_at) VALUES (?, ?, ?, ?)",
			productId, key, sortOrder, LocalDateTime.ofInstant(NOW, ZoneOffset.UTC));
		return key;
	}

	private long count(User user, Long productId) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM favorites WHERE user_id = ? AND product_id = ?",
			Long.class, user.getId(), productId);
	}

	private Instant favoritedAt(User user, Long productId) {
		// DATETIME에는 UTC 시각이 그대로 들어 있으므로 시간대 변환 없이 읽는다
		return jdbcTemplate.queryForObject(
			"SELECT created_at FROM favorites WHERE user_id = ? AND product_id = ?",
			LocalDateTime.class, user.getId(), productId).toInstant(ZoneOffset.UTC);
	}

	private MvcTestResult favorite(User user, Long productId) {
		return mvc.put().uri("/api/v1/products/{id}/favorite", productId)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private MvcTestResult unfavorite(User user, Long productId) {
		return mvc.delete().uri("/api/v1/products/{id}/favorite", productId)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private MvcTestResult check(User user, Long productId) {
		return mvc.get().uri("/api/v1/products/{id}/favorite", productId)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private MvcTestResult list(User user, String query) {
		return mvc.get().uri("/api/v1/users/me/favorites" + query)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private String bearer(User user) {
		return "Bearer " + jwtTokenProvider.createAccessToken(user.getId()).getTokenValue();
	}
}
