package com.layer7.marketplace.notification.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.notification.domain.NotificationType;
import com.layer7.marketplace.notification.dto.NewNotification;
import com.layer7.marketplace.notification.service.NotificationService;
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

class NotificationApiTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-05T03:00:00Z");
	private static final Duration MINUTE = Duration.ofMinutes(1);

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JwtTokenProvider jwtTokenProvider;

	@Autowired
	private NotificationService notificationService;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	private User owner;
	private User other;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		owner = fixtures.user();
		other = fixtures.user();
	}

	@Test
	@DisplayName("내 알림만 최신순으로 응답하고, 같은 시각에 만든 알림은 나중에 만든 것이 먼저다")
	void listsMyNotificationsLatestFirst() {
		// given
		Long oldest = notify(owner, NOW.minus(MINUTE.multipliedBy(2)));
		Long first = notify(owner, NOW);
		Long second = notify(owner, NOW);
		notify(other, NOW.plus(MINUTE));

		// when
		MvcTestResult result = list(owner, "");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{
				  "content": [ { "id": %d }, { "id": %d }, { "id": %d } ],
				  "page": 0, "size": 20, "totalElements": 3, "totalPages": 1
				}
				""".formatted(second, first, oldest));
	}

	@Test
	@DisplayName("알림 항목은 명세 형식으로 응답한다")
	void responseFormat() {
		// given
		Long auctionId = fixtures.auction(other, 10_000, NOW, NOW.plus(Duration.ofHours(1))).getId();
		String dedupeKey = "test:" + UUID.randomUUID();
		notificationService.create(new NewNotification(
			owner.getId(), NotificationType.OUTBID, "다른 입찰자가 현재 최고 입찰자가 되었습니다.",
			null, auctionId, null, dedupeKey));
		Long id = idOf(dedupeKey);

		// when
		MvcTestResult result = list(owner, "");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("""
				{
				  "content": [ {
				    "id": %d,
				    "type": "OUTBID",
				    "message": "다른 입찰자가 현재 최고 입찰자가 되었습니다.",
				    "productId": null,
				    "auctionId": %d,
				    "tradeId": null,
				    "readAt": null,
				    "createdAt": "2026-11-05T03:00:00Z"
				  } ],
				  "page": 0, "size": 20, "totalElements": 1, "totalPages": 1
				}
				""".formatted(id, auctionId));
	}

	@Test
	@DisplayName("unreadOnly=true면 읽지 않은 알림만, page·size로 나눠 응답한다")
	void unreadOnlyAndPaging() {
		// given
		Long read = notify(owner, NOW.minus(MINUTE.multipliedBy(3)));
		notificationService.markRead(owner.getId(), read);
		Long unread1 = notify(owner, NOW.minus(MINUTE.multipliedBy(2)));
		Long unread2 = notify(owner, NOW.minus(MINUTE));
		Long unread3 = notify(owner, NOW);

		// when
		MvcTestResult firstPage = list(owner, "?unreadOnly=true&size=2");
		MvcTestResult secondPage = list(owner, "?unreadOnly=true&size=2&page=1");
		MvcTestResult all = list(owner, "?unreadOnly=false");

		// then
		assertThat(firstPage)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "id": %d }, { "id": %d } ], "page": 0, "size": 2, "totalElements": 3, "totalPages": 2 }
				""".formatted(unread3, unread2));
		assertThat(secondPage)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "content": [ { "id": %d } ], "page": 1, "size": 2, "totalElements": 3, "totalPages": 2 }
				""".formatted(unread1));
		assertThat(all)
			.bodyJson()
			.isLenientlyEqualTo("{ \"totalElements\": 4 }");
	}

	@Test
	@DisplayName("페이지 크기가 50을 넘으면 400 VALIDATION_ERROR로 응답한다")
	void validatesPageSize() {
		// when
		MvcTestResult result = list(owner, "?size=51");

		// then
		assertThat(result)
			.hasStatus(HttpStatus.BAD_REQUEST)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "code": "VALIDATION_ERROR", "fieldErrors": [ { "field": "size", "code": "MAX" } ] }
				""");
	}

	@Test
	@DisplayName("토큰 없이 부르면 세 API 모두 401 UNAUTHORIZED로 응답한다")
	void requiresLogin() {
		// given
		Long id = notify(owner, NOW);

		// when
		MvcTestResult list = mvc.get().uri("/api/v1/notifications").exchange();
		MvcTestResult read = mvc.patch().uri("/api/v1/notifications/{id}/read", id).exchange();
		MvcTestResult readAll = mvc.patch().uri("/api/v1/notifications/read-all").exchange();

		// then
		for (MvcTestResult result : new MvcTestResult[] {list, read, readAll}) {
			assertThat(result)
				.hasStatus(HttpStatus.UNAUTHORIZED)
				.bodyJson()
				.isLenientlyEqualTo("{ \"code\": \"UNAUTHORIZED\" }");
		}
		assertThat(readAt(id)).isNull();
	}

	@Test
	@DisplayName("내 알림을 읽음 처리하면 읽은 시각을 담아 응답하고, 다시 불러도 처음 읽은 시각을 유지한다")
	void markRead() {
		// given
		Long id = notify(owner, NOW.minus(MINUTE));

		// when
		MvcTestResult first = read(owner, id);
		clock.advance(MINUTE);
		MvcTestResult again = read(owner, id);

		// then
		assertThat(first)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("""
				{ "id": %d, "readAt": "2026-11-05T03:00:00Z", "createdAt": "2026-11-05T02:59:00Z" }
				""".formatted(id));
		assertThat(again)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isLenientlyEqualTo("{ \"id\": %d, \"readAt\": \"2026-11-05T03:00:00Z\" }".formatted(id));
		assertThat(readAt(id)).isEqualTo(NOW);
	}

	@Test
	@DisplayName("다른 사람의 알림이나 없는 알림을 읽음 처리하면 404 RESOURCE_NOT_FOUND이고, 그 알림은 그대로다")
	void cannotReadOthersNotification() {
		// given
		Long othersId = notify(other, NOW);

		// when
		MvcTestResult others = read(owner, othersId);
		MvcTestResult missing = read(owner, Long.MAX_VALUE);

		// then
		for (MvcTestResult result : new MvcTestResult[] {others, missing}) {
			assertThat(result)
				.hasStatus(HttpStatus.NOT_FOUND)
				.bodyJson()
				.isLenientlyEqualTo("{ \"code\": \"RESOURCE_NOT_FOUND\" }");
		}
		assertThat(readAt(othersId)).isNull();
	}

	@Test
	@DisplayName("전체 읽음은 내 미읽음 알림만 읽음 처리하고 그 수를 응답한다. 이미 읽은 알림의 읽은 시각은 바꾸지 않는다")
	void markAllRead() {
		// given
		Long alreadyRead = notify(owner, NOW.minus(MINUTE.multipliedBy(2)));
		notificationService.markRead(owner.getId(), alreadyRead);
		notify(owner, NOW.minus(MINUTE));
		notify(owner, NOW);
		Long othersUnread = notify(other, NOW);
		clock.advance(MINUTE);

		// when
		MvcTestResult result = readAll(owner);
		MvcTestResult again = readAll(owner);

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("{ \"updatedCount\": 2 }");
		assertThat(again)
			.bodyJson()
			.isStrictlyEqualTo("{ \"updatedCount\": 0 }");
		assertThat(list(owner, "?unreadOnly=true"))
			.bodyJson()
			.isLenientlyEqualTo("{ \"content\": [], \"totalElements\": 0 }");
		assertThat(readAt(alreadyRead)).isEqualTo(NOW);
		assertThat(readAt(othersUnread)).isNull();
	}

	// 만든 알림의 id. 시각을 정하려고 잠시 시계를 옮겼다가 되돌린다
	private Long notify(User user, Instant createdAt) {
		Instant before = clock.instant();
		clock.fixAt(createdAt);
		String dedupeKey = "test:" + UUID.randomUUID();
		notificationService.create(new NewNotification(
			user.getId(), NotificationType.OUTBID, "테스트 알림", null, null, null, dedupeKey));
		clock.fixAt(before);
		return idOf(dedupeKey);
	}

	private Long idOf(String dedupeKey) {
		return jdbcTemplate.queryForObject("SELECT id FROM notifications WHERE dedupe_key = ?", Long.class, dedupeKey);
	}

	private Instant readAt(Long id) {
		// DATETIME에는 UTC 시각이 그대로 들어 있으므로 시간대 변환 없이 읽는다
		LocalDateTime readAt = jdbcTemplate.queryForObject(
			"SELECT read_at FROM notifications WHERE id = ?", LocalDateTime.class, id);
		return readAt == null ? null : readAt.toInstant(ZoneOffset.UTC);
	}

	private MvcTestResult list(User user, String query) {
		return mvc.get().uri("/api/v1/notifications" + query)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private MvcTestResult read(User user, Long id) {
		return mvc.patch().uri("/api/v1/notifications/{id}/read", id)
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private MvcTestResult readAll(User user) {
		return mvc.patch().uri("/api/v1/notifications/read-all")
			.header(HttpHeaders.AUTHORIZATION, bearer(user))
			.exchange();
	}

	private String bearer(User user) {
		return "Bearer " + jwtTokenProvider.createAccessToken(user.getId()).getTokenValue();
	}
}
