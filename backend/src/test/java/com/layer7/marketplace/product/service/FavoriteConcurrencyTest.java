package com.layer7.marketplace.product.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.product.dto.FavoriteResponse;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 같은 회원이 같은 상품을 여러 요청에서 동시에 관심상품으로 등록할 때 행이 하나만 남고, 모든 요청이 등록됨으로 끝나는지 확인한다.
 *
 * <p>테스트 메서드에는 @Transactional을 두지 않는다. 각 등록이 자기 트랜잭션으로 실제로 동시에 실행된다.
 */
class FavoriteConcurrencyTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-05T03:00:00Z");
	private static final long TIMEOUT_SECONDS = 10;

	// 동시에 쓰는 DB 커넥션 수를 커넥션 풀(기본 10개)보다 적게 둔다
	private static final int REQUESTS = 5;

	@Autowired
	private FavoriteService favoriteService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private TransactionTemplate transactionTemplate;

	private User user;
	private Long productId;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		user = fixtures.user();
		productId = fixtures.product(fixtures.user(), "동시 등록 상품").getId();
	}

	@Test
	@DisplayName("먼저 등록한 트랜잭션이 커밋하면, 그 뒤에서 기다리던 등록은 오류 없이 등록됨으로 끝난다")
	void waitingRequestSeesCommittedFavorite() throws Exception {
		// given
		ExecutorService executor = Executors.newSingleThreadExecutor();

		// when
		FavoriteResponse waiting;
		try {
			Future<FavoriteResponse> other = transactionTemplate.execute(status -> {
				favoriteService.favorite(user.getId(), productId);
				Future<FavoriteResponse> submitted = executor.submit(() -> favoriteService.favorite(user.getId(), productId));
				awaitWaitingInsert();
				return submitted;
			});
			waiting = other.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
		} finally {
			shutdown(executor);
		}

		// then
		// JPA로 저장하고 중복 오류를 잡는 방식이면 기다리던 쪽 트랜잭션이 롤백 표시돼 커밋에서 예외로 실패한다
		assertThat(waiting).isEqualTo(new FavoriteResponse(productId, true));
		assertThat(count()).isEqualTo(1);
	}

	@RepeatedTest(3)
	@DisplayName("여러 요청이 한꺼번에 등록해도 모두 등록됨으로 끝나고 행은 하나다")
	void favoriteAtOnce() throws Exception {
		// given
		ExecutorService executor = Executors.newFixedThreadPool(REQUESTS);
		CountDownLatch ready = new CountDownLatch(REQUESTS);
		CountDownLatch start = new CountDownLatch(1);

		// when
		List<FavoriteResponse> results = new ArrayList<>();
		try {
			List<Future<FavoriteResponse>> futures = new ArrayList<>();
			for (int i = 0; i < REQUESTS; i++) {
				futures.add(executor.submit(() -> {
					ready.countDown();
					if (!start.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
						throw new IllegalStateException("동시 실행 시작 대기 시간이 초과됐습니다.");
					}
					return favoriteService.favorite(user.getId(), productId);
				}));
			}
			assertThat(ready.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)).isTrue();
			start.countDown();
			for (Future<FavoriteResponse> future : futures) {
				results.add(future.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
		} finally {
			start.countDown();
			shutdown(executor);
		}

		// then
		assertThat(results).hasSize(REQUESTS).containsOnly(new FavoriteResponse(productId, true));
		assertThat(count()).isEqualTo(1);
	}

	private long count() {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM favorites WHERE user_id = ? AND product_id = ?", Long.class, user.getId(), productId);
	}

	// 다른 커넥션의 관심상품 INSERT가 이 트랜잭션의 락을 기다리기 시작할 때까지 기다린다.
	// 락 대기 제한(3초) 안에 풀어 주도록 1초까지만 기다린다
	private void awaitWaitingInsert() {
		long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
		while (countWaitingInserts() < 1) {
			if (System.nanoTime() > deadline) {
				throw new AssertionError("락을 기다리는 관심상품 INSERT가 없습니다.");
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
			Integer.class, "%INSERT INTO favorites%");
	}

	// 중간에 실패해 빠져나와도 worker 스레드가 다음 테스트까지 남지 않게 정리한다
	private static void shutdown(ExecutorService executor) throws InterruptedException {
		executor.shutdownNow();
		executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS);
	}
}
