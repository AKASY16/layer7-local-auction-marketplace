package com.layer7.marketplace.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.layer7.marketplace.notification.domain.NotificationType;
import com.layer7.marketplace.notification.dto.NewNotification;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 알림 만들기의 중복 방지. 동시에 만드는 경우는 {@link NotificationCreateConcurrencyTest}가 확인한다.
 */
class NotificationCreateTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-05T03:00:00Z");

	@Autowired
	private NotificationService notificationService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private TransactionTemplate transactionTemplate;

	private User user;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		user = fixtures.user();
	}

	@Test
	@DisplayName("같은 dedupeKey로 두 번 만들면 처음만 만들고, 두 번째는 false를 돌려주며 처음 알림을 바꾸지 않는다")
	void sameKeyCreatesOnce() {
		// given
		String key = newKey();

		// when
		boolean first = notificationService.create(notification(key, "처음 알림"));
		boolean second = notificationService.create(notification(key, "두 번째 알림"));

		// then
		assertThat(first).isTrue();
		assertThat(second).isFalse();
		assertThat(count(key)).isEqualTo(1);
		assertThat(jdbcTemplate.queryForObject(
			"SELECT message FROM notifications WHERE dedupe_key = ?", String.class, key)).isEqualTo("처음 알림");
	}

	@Test
	@DisplayName("호출한 쪽 트랜잭션 안에서 중복이 나도 그 트랜잭션은 이어지고 커밋된다")
	void duplicateKeepsCallerTransaction() {
		// given
		String existing = newKey();
		notificationService.create(notification(existing, "이미 있는 알림"));
		String before = newKey();
		String after = newKey();

		// when
		// JPA로 저장해 중복 오류가 나면 트랜잭션이 롤백 표시돼, 여기서 커밋할 때 실패하고 before·after도 남지 않는다
		Boolean duplicated = transactionTemplate.execute(status -> {
			notificationService.create(notification(before, "앞 알림"));
			boolean created = notificationService.create(notification(existing, "중복 알림"));
			notificationService.create(notification(after, "뒤 알림"));
			return created;
		});

		// then
		assertThat(duplicated).isFalse();
		assertThat(count(before)).isEqualTo(1);
		assertThat(count(after)).isEqualTo(1);
		assertThat(count(existing)).isEqualTo(1);
	}

	@Test
	@DisplayName("호출한 쪽 트랜잭션이 롤백되면 알림도 남지 않는다")
	void rolledBackWithCaller() {
		// given
		String key = newKey();

		// when
		transactionTemplate.executeWithoutResult(status -> {
			notificationService.create(notification(key, "롤백될 알림"));
			status.setRollbackOnly();
		});

		// then
		assertThat(count(key)).isZero();
	}

	@Test
	@DisplayName("없는 경매를 가리키는 알림은 중복으로 넘기지 않고 오류를 던진다")
	void foreignKeyErrorIsNotSwallowed() {
		// given
		String key = newKey();
		NewNotification missingAuction = new NewNotification(
			user.getId(), NotificationType.OUTBID, "없는 경매", null, Long.MAX_VALUE, null, key);

		// when / then
		assertThatThrownBy(() -> notificationService.create(missingAuction))
			.isInstanceOf(DataIntegrityViolationException.class);
		assertThat(count(key)).isZero();
	}

	@Test
	@DisplayName("메시지는 이모지를 포함해 500자까지 저장한다")
	void storesFiveHundredCharacters() {
		// given
		String key = newKey();
		// 이모지는 Java 문자열 길이로는 2지만 MySQL은 1글자로 센다
		String message = "🔔".repeat(500);

		// when
		boolean created = notificationService.create(notification(key, message));

		// then
		assertThat(created).isTrue();
		assertThat(jdbcTemplate.queryForObject(
			"SELECT message FROM notifications WHERE dedupe_key = ?", String.class, key)).isEqualTo(message);
	}

	private NewNotification notification(String dedupeKey, String message) {
		return new NewNotification(user.getId(), NotificationType.OUTBID, message, null, null, null, dedupeKey);
	}

	private static String newKey() {
		return "test:" + UUID.randomUUID();
	}

	private long count(String dedupeKey) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM notifications WHERE dedupe_key = ?", Long.class, dedupeKey);
	}
}
