package com.layer7.marketplace.notification.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.notification.domain.NotificationType;
import com.layer7.marketplace.notification.dto.NewNotification;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 같은 dedupeKey의 알림을 여러 트랜잭션이 동시에 만들 때 하나만 남는지 확인한다.
 *
 * <p>테스트 메서드에는 @Transactional을 두지 않는다. 각 생성이 자기 트랜잭션으로 실제로 동시에 실행된다.
 * 앞의 두 테스트는 결과가 실행 순서에 따라 달라지지 않도록, 테스트가 먼저 넣고 커밋하지 않은 채 다른 쪽을 그 뒤에 세운 다음 커밋하거나 롤백한다.
 */
class NotificationCreateConcurrencyTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-05T03:00:00Z");
	private static final long TIMEOUT_SECONDS = 10;

	// 동시에 쓰는 DB 커넥션 수를 커넥션 풀(기본 10개)보다 적게 둔다
	private static final int CREATORS = 5;

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
	@DisplayName("먼저 넣은 트랜잭션이 커밋하면, 그 뒤에서 기다리던 생성은 새로 만들지 않고 false를 돌려준다")
	void waitingCreatorSeesCommittedDuplicate() throws Exception {
		// given
		String key = newKey();
		ExecutorService executor = Executors.newSingleThreadExecutor();

		// when
		boolean first;
		boolean second;
		try {
			List<Object> results = transactionTemplate.execute(status -> {
				boolean created = notificationService.create(notification(key));
				Future<Boolean> other = executor.submit(() -> notificationService.create(notification(key)));
				awaitWaitingInsert();
				return List.of(created, other);
			});
			first = (Boolean) results.get(0);
			second = (Boolean) ((Future<?>) results.get(1)).get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
		} finally {
			shutdown(executor);
		}

		// then
		// JPA로 저장하고 중복 오류를 잡는 방식이면 기다리던 쪽의 트랜잭션이 롤백 표시돼 커밋에서 예외로 실패한다
		assertThat(first).isTrue();
		assertThat(second).isFalse();
		assertThat(count(key)).isEqualTo(1);
	}

	@Test
	@DisplayName("먼저 넣은 트랜잭션이 롤백하면, 그 뒤에서 기다리던 생성이 새로 만들어 true를 돌려준다")
	void waitingCreatorCreatesAfterRollback() throws Exception {
		// given
		String key = newKey();
		ExecutorService executor = Executors.newSingleThreadExecutor();

		// when
		boolean second;
		try {
			Future<Boolean> waiting = transactionTemplate.execute(status -> {
				notificationService.create(notification(key));
				Future<Boolean> other = executor.submit(() -> notificationService.create(notification(key)));
				awaitWaitingInsert();
				status.setRollbackOnly();
				return other;
			});
			second = waiting.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
		} finally {
			shutdown(executor);
		}

		// then
		assertThat(second).isTrue();
		assertThat(count(key)).isEqualTo(1);
	}

	@Test
	@DisplayName("같은 키로 여러 곳에서 한꺼번에 만들어도 하나만 true이고 알림은 하나다")
	void createAtOnce() throws Exception {
		// given
		String key = newKey();
		ExecutorService executor = Executors.newFixedThreadPool(CREATORS);
		CountDownLatch ready = new CountDownLatch(CREATORS);
		CountDownLatch start = new CountDownLatch(1);

		// when
		List<Boolean> results = new ArrayList<>();
		try {
			List<Future<Boolean>> futures = new ArrayList<>();
			for (int i = 0; i < CREATORS; i++) {
				futures.add(executor.submit(() -> {
					ready.countDown();
					if (!start.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
						throw new IllegalStateException("동시 실행 시작 대기 시간이 초과됐습니다.");
					}
					return notificationService.create(notification(key));
				}));
			}
			assertThat(ready.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)).isTrue();
			start.countDown();
			for (Future<Boolean> future : futures) {
				results.add(future.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
		} finally {
			start.countDown();
			shutdown(executor);
		}

		// then
		assertThat(results).containsOnlyOnce(true);
		assertThat(results).filteredOn(created -> !created).hasSize(CREATORS - 1);
		assertThat(count(key)).isEqualTo(1);
	}

	private NewNotification notification(String dedupeKey) {
		return new NewNotification(user.getId(), NotificationType.OUTBID, "동시 생성 알림", null, null, null, dedupeKey);
	}

	private static String newKey() {
		return "test:" + UUID.randomUUID();
	}

	private long count(String dedupeKey) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM notifications WHERE dedupe_key = ?", Long.class, dedupeKey);
	}

	// 다른 커넥션의 알림 INSERT가 이 트랜잭션의 락을 기다리기 시작할 때까지 기다린다.
	// 락 대기 제한(3초) 안에 풀어 주도록 1초까지만 기다린다
	private void awaitWaitingInsert() {
		long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
		while (countWaitingInserts() < 1) {
			if (System.nanoTime() > deadline) {
				throw new AssertionError("락을 기다리는 알림 INSERT가 없습니다.");
			}
			// TransactionTemplate 콜백 안에서 부르므로 InterruptedException을 밖으로 던질 수 없다
			try {
				Thread.sleep(10);
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				throw new IllegalStateException(e);
			}
		}
	}

	// 커넥션이 모두 같은 DB 사용자라서 PROCESS 권한 없이도 서로의 실행 중인 쿼리가 보인다
	private int countWaitingInserts() {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM performance_schema.processlist WHERE ID <> CONNECTION_ID() AND INFO LIKE ?",
			Integer.class, "%INSERT INTO notifications%");
	}

	// 중간에 실패해 빠져나와도 worker 스레드가 다음 테스트까지 남지 않게 정리한다
	private static void shutdown(ExecutorService executor) throws InterruptedException {
		executor.shutdownNow();
		executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS);
	}
}
