package com.layer7.marketplace.auction.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
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
 * 동시성 테스트 계획(docs/backend/concurrency-testing.md)의 C08: 마감 경계에서 입찰과 종료 처리가 겹칠 때, 그리고 같은 경매를 동시에 종료할 때.
 *
 * <p>테스트 메서드에는 @Transactional을 두지 않는다. 입찰과 종료가 각자의 트랜잭션으로 실제로 동시에 실행된다.
 * 결과가 락을 잡는 순서에 따라 달라지지 않도록, 테스트가 회원 행이나 경매 행 락을 쥐고 각 worker가 멈추는 지점을 정한 뒤 시계를 마감 시각으로 넘긴다.
 */
class AuctionCloseConcurrencyTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-03T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);
	private static final long TIMEOUT_SECONDS = 10;

	// 동시에 쓰는 DB 커넥션 수는 테스트 1 + worker 최대 5개로, 커넥션 풀(기본 10개)보다 적게 둔다
	private static final int LATE_BIDDERS = 3;
	private static final int CLOSERS = 5;

	@Autowired
	private AuctionService auctionService;

	@Autowired
	private BidService bidService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private TransactionTemplate transactionTemplate;

	private User seller;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
	}

	@Test
	@DisplayName("C08: 마감 직전에 경매 락을 잡은 입찰은 성립하고, 락을 기다린 종료 처리가 그 입찰을 낙찰로 확정한다")
	void bidBeforeCloseWins() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		User lastBidder = fixtures.user();
		clock.fixAt(endAt.minusMillis(1));

		// when
		// 입찰은 경매 락을 잡고 마감 직전 시각으로 판정을 마친 뒤, 테스트가 잠근 자기 회원 행 앞에서 멈춘다.
		// 종료 처리는 그 경매 락을 기다린다. 이 상태에서 시계를 마감 시각으로 넘기고 회원 행 락을 푼다
		ExecutorService executor = Executors.newFixedThreadPool(2);
		BidOutcome bidOutcome;
		boolean closed;
		try {
			List<Future<?>> workers = transactionTemplate.execute(status -> {
				jdbcTemplate.queryForObject(
					"SELECT id FROM users WHERE id = ? FOR UPDATE", Long.class, lastBidder.getId());
				Future<BidOutcome> bid = executor.submit(bid(auction, lastBidder, 10_500));
				awaitWaitingQueries("for share", 1);

				Future<Boolean> close = executor.submit(() -> auctionService.closeAuction(auction.getId()));
				awaitWaitingQueries("for update", 1);

				clock.fixAt(endAt);
				return List.of(bid, close);
			});

			bidOutcome = (BidOutcome) workers.get(0).get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			closed = (Boolean) workers.get(1).get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
		} finally {
			shutdown(executor);
		}

		// then
		// 종료 처리가 락을 잡기 전에 시각을 읽으면 마감 전으로 판정해 종료하지 않으므로 여기서 실패한다
		assertThat(bidOutcome.errorCode()).isNull();
		assertThat(closed).isTrue();

		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("status")).isEqualTo("ENDED");
		assertThat(row.get("current_price")).isEqualTo(10_500L);
		assertThat(winningBidderId(auction)).isEqualTo(lastBidder.getId());
		assertClosedConsistently(auction);
	}

	@Test
	@DisplayName("C08: 종료 처리와 입찰이 함께 경매 락을 기다리는 사이 마감이 지나면, 입찰은 모두 거절되고 기존 선두가 낙찰된다")
	void bidsAfterEndAtRejected() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		User leader = fixtures.user();
		bidService.placeManualBid(auction.getId(), leader.getId(), 10_000);
		List<User> lateBidders = new ArrayList<>();
		for (int i = 0; i < LATE_BIDDERS; i++) {
			lateBidders.add(fixtures.user());
		}
		clock.fixAt(endAt.minusMillis(1));

		// when
		// 테스트가 경매 행 락을 쥔 채 종료 처리와 늦은 입찰을 모두 그 락 앞에 세운 뒤, 시계를 마감 시각으로 넘기고 락을 푼다.
		// 누가 먼저 락을 잡든 판정 시각은 마감 이후라서 결과는 하나다
		ExecutorService executor = Executors.newFixedThreadPool(LATE_BIDDERS + 1);
		List<BidOutcome> bidOutcomes = new ArrayList<>();
		boolean closed;
		try {
			List<Future<BidOutcome>> bids = new ArrayList<>();
			Future<Boolean> close = transactionTemplate.execute(status -> {
				jdbcTemplate.queryForObject(
					"SELECT id FROM auctions WHERE id = ? FOR UPDATE", Long.class, auction.getId());

				Future<Boolean> closing = executor.submit(() -> auctionService.closeAuction(auction.getId()));
				// 시각을 락보다 먼저 읽는 버그가 있으면 마감 판정을 통과해 받아들여지도록, 모두 유효한 더 높은 금액으로 넣는다
				for (int i = 0; i < LATE_BIDDERS; i++) {
					bids.add(executor.submit(bid(auction, lateBidders.get(i), 10_500 + i * 500L)));
				}
				awaitWaitingQueries("for update", LATE_BIDDERS + 1);

				clock.fixAt(endAt);
				return closing;
			});

			closed = close.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			for (Future<BidOutcome> bid : bids) {
				bidOutcomes.add(bid.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
		} finally {
			shutdown(executor);
		}

		// then
		assertThat(closed).isTrue();
		assertThat(bidOutcomes)
			.extracting(BidOutcome::errorCode)
			.containsOnly(ErrorCode.AUCTION_ENDED);

		assertThat(countBids(auction)).isEqualTo(1);
		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("status")).isEqualTo("ENDED");
		assertThat(row.get("current_price")).isEqualTo(10_000L);
		assertThat(winningBidderId(auction)).isEqualTo(leader.getId());
		assertClosedConsistently(auction);
	}

	@Test
	@DisplayName("C08: 같은 경매를 여러 곳에서 동시에 종료해도 한 번만 종료되고 낙찰 결과는 같다")
	void closeAtOnce() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		clock.fixAt(endAt.plusSeconds(1));
		long versionBefore = (Long) auctionRow(auction).get("version");

		// when
		List<Boolean> results = runAtOnce(CLOSERS, () -> auctionService.closeAuction(auction.getId()));

		// then
		// 락이 없으면 여러 worker가 함께 종료를 시도해 낙관적 락(version) 충돌 예외로 실패한다
		assertThat(results).containsOnlyOnce(true);
		assertThat(results).filteredOn(closed -> !closed).hasSize(CLOSERS - 1);

		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("status")).isEqualTo("ENDED");
		assertThat(row.get("version")).isEqualTo(versionBefore + 1);
		assertClosedConsistently(auction);
	}

	// 종료된 경매의 불변조건(docs/backend/concurrency-testing.md C08):
	// 낙찰은 선두 입찰이고, 현재가는 그 금액이며, 종료 판정 이후(마감 시각 이후)에 받아들인 입찰이 없다
	private void assertClosedConsistently(Auction auction) {
		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("winning_bid_id")).isEqualTo(row.get("leading_bid_id"));
		if (row.get("winning_bid_id") != null) {
			Long winningAmount = jdbcTemplate.queryForObject(
				"SELECT amount FROM bids WHERE id = ?", Long.class, row.get("winning_bid_id"));
			assertThat(row.get("current_price")).isEqualTo(winningAmount);
		}
		assertThat(jdbcTemplate.queryForObject(
			"""
			SELECT COUNT(*) FROM bids b JOIN auctions a ON a.id = b.auction_id
			WHERE b.auction_id = ? AND b.created_at >= a.end_at
			""",
			Long.class, auction.getId())).isZero();
	}

	private <T> List<T> runAtOnce(int count, Callable<T> task) throws Exception {
		ExecutorService executor = Executors.newFixedThreadPool(count);
		CountDownLatch ready = new CountDownLatch(count);
		CountDownLatch start = new CountDownLatch(1);
		try {
			List<Future<T>> futures = new ArrayList<>();
			for (int i = 0; i < count; i++) {
				futures.add(executor.submit(() -> {
					ready.countDown();
					if (!start.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
						throw new IllegalStateException("동시 실행 시작 대기 시간이 초과됐습니다.");
					}
					return task.call();
				}));
			}
			assertThat(ready.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)).isTrue();
			start.countDown();

			List<T> results = new ArrayList<>();
			for (Future<T> future : futures) {
				results.add(future.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
			return results;
		} finally {
			start.countDown();
			shutdown(executor);
		}
	}

	// 중간에 실패해 빠져나와도 worker 스레드가 다음 테스트까지 남지 않게 정리한다
	private static void shutdown(ExecutorService executor) throws InterruptedException {
		executor.shutdownNow();
		executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS);
	}

	// 다른 커넥션에서 잠금 쿼리(FOR UPDATE / FOR SHARE)가 count개 실행 중일 때까지 기다린다.
	// 락을 기다리는 worker가 락 대기 제한(3초) 안에 풀려나도록 한 번에 1초까지만 기다린다
	private void awaitWaitingQueries(String lockClause, int count) {
		long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
		while (countWaitingQueries(lockClause) < count) {
			if (System.nanoTime() > deadline) {
				throw new AssertionError("잠금 대기 중인 쿼리가 %d개가 되지 않음: %s".formatted(count, lockClause));
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
	private int countWaitingQueries(String lockClause) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM performance_schema.processlist WHERE ID <> CONNECTION_ID() AND INFO LIKE ?",
			Integer.class, "%" + lockClause + "%");
	}

	// 거절은 결과로 모으고, 그 밖의 예외(락 대기 시간 초과 등)는 그대로 던져 테스트를 실패시킨다
	private Callable<BidOutcome> bid(Auction auction, User bidder, long amount) {
		return () -> {
			try {
				bidService.placeManualBid(auction.getId(), bidder.getId(), amount);
				return new BidOutcome(null);
			} catch (BusinessException e) {
				return new BidOutcome(e.getErrorCode());
			}
		};
	}

	private long countBids(Auction auction) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM bids WHERE auction_id = ?", Long.class, auction.getId());
	}

	private Map<String, Object> auctionRow(Auction auction) {
		return jdbcTemplate.queryForMap(
			"SELECT status, current_price, leading_bid_id, winning_bid_id, version FROM auctions WHERE id = ?",
			auction.getId());
	}

	private Long winningBidderId(Auction auction) {
		return jdbcTemplate.queryForObject(
			"SELECT b.bidder_id FROM auctions a JOIN bids b ON b.id = a.winning_bid_id WHERE a.id = ?",
			Long.class, auction.getId());
	}

	// errorCode가 null이면 받아들여진 입찰
	private record BidOutcome(ErrorCode errorCode) {
	}
}
