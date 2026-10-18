package com.layer7.marketplace.bid.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.bid.domain.BidIncrementPolicy;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 동시성 테스트 계획(docs/backend/concurrency-testing.md)의 C02와, 이슈 #30의 마감 경계 입찰.
 *
 * <p>테스트 메서드에는 @Transactional을 두지 않는다. 각 worker가 BidService의 독립 트랜잭션으로 실제로 동시에 입찰한다.
 * 마감 경계는 결과가 락을 잡는 순서에 따라 달라지지 않도록, 테스트가 회원 행 락을 쥐고 입찰이 멈추는 지점을 정한다.
 */
class BidConcurrencyTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-18T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);
	private static final long TIMEOUT_SECONDS = 10;

	// 동시에 쓰는 DB 커넥션 수: C02는 입찰 10개, 마감 경계는 테스트 1 + first 1 + 대기 입찰 5.
	// 커넥션 풀(기본 10개)보다 많아지면 입찰이 커넥션을 기다리느라 동시에 실행되지 않고, 마감 경계는 대기 확인에서 실패한다
	private static final int CHALLENGERS = 10;
	private static final int LATE_BIDDERS = 5;

	@Autowired
	private BidService bidService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private TransactionTemplate transactionTemplate;

	@Autowired
	private BidIncrementPolicy bidIncrementPolicy;

	private User seller;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
	}

	@Test
	@DisplayName("C02: 현재가 10,000원에서 여러 명이 10,500원을 동시에 입찰하면 1건만 성공한다")
	void sameAmountAtOnce() throws Exception {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		List<Callable<BidOutcome>> bids = users(CHALLENGERS).stream()
			.map(challenger -> bid(auction, challenger, 10_500))
			.toList();

		// when
		List<BidOutcome> outcomes = runAtOnce(bids);

		// then
		List<BidOutcome> accepted = outcomes.stream().filter(BidOutcome::accepted).toList();
		assertThat(accepted).hasSize(1);
		assertThat(outcomes)
			.filteredOn(outcome -> !outcome.accepted())
			.extracting(BidOutcome::errorCode)
			.containsOnly(ErrorCode.BID_AMOUNT_TOO_LOW);

		assertThat(countBidsWithAmount(auction, 10_500)).isEqualTo(1);
		assertThat(auctionRow(auction)).containsEntry("current_price", 10_500L);
		assertThat(leadingBidderId(auction)).isEqualTo(accepted.getFirst().bidderId());
		assertCommonInvariants(auction);
	}

	@Test
	@DisplayName("마감 경계: 마감 전에 락을 잡은 입찰은 성립하고, 락을 기다리는 사이 마감이 지난 입찰은 AUCTION_ENDED로 거절된다")
	void bidsAcrossEndAt() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		User first = fixtures.user();
		List<User> lateBidders = users(LATE_BIDDERS);
		clock.fixAt(endAt.minusMillis(1));

		// when
		// first는 경매 락을 잡고 마감 직전 시각으로 판정을 마친 뒤, 테스트가 잠근 자기 회원 행 앞에서 멈춘다.
		// 나머지는 first가 쥔 경매 락을 기다린다. 이 상태에서 시계를 마감 시각으로 넘기고 회원 행 락을 푼다
		ExecutorService executor = Executors.newFixedThreadPool(LATE_BIDDERS + 1);
		BidOutcome firstOutcome;
		List<BidOutcome> lateOutcomes = new ArrayList<>();
		try {
			List<Future<BidOutcome>> lateBids = new ArrayList<>();
			Future<BidOutcome> firstBid = transactionTemplate.execute(status -> {
				jdbcTemplate.queryForObject("SELECT id FROM users WHERE id = ? FOR UPDATE", Long.class, first.getId());
				Future<BidOutcome> bid = executor.submit(bid(auction, first, 10_000));
				awaitWaitingQueries("for share", 1);

				// 늦은 입찰은 모두 first보다 높은 유효 금액으로 넣는다.
				// 시각을 락보다 먼저 읽는 버그가 있으면 금액 부족이 아니라 마감 판정을 통과해 받아들여지므로 테스트가 실패한다
				for (int i = 0; i < LATE_BIDDERS; i++) {
					lateBids.add(executor.submit(bid(auction, lateBidders.get(i), 10_500 + i * 500L)));
				}
				awaitWaitingQueries("for update", LATE_BIDDERS);

				clock.fixAt(endAt);
				return bid;
			});

			firstOutcome = firstBid.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			for (Future<BidOutcome> lateBid : lateBids) {
				lateOutcomes.add(lateBid.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
		} finally {
			shutdown(executor);
		}

		// then
		// 실패하면 어떤 오류로 거절됐는지 보이도록 errorCode로 확인한다
		assertThat(firstOutcome.errorCode()).isNull();
		assertThat(lateOutcomes)
			.extracting(BidOutcome::errorCode)
			.containsOnly(ErrorCode.AUCTION_ENDED);

		// 저장은 마감 시각이 지난 뒤에 일어났어도, 생성 시각은 받아들인 판정 시각으로 남는다
		assertThat(countBids(auction)).isEqualTo(1);
		assertThat(jdbcTemplate.queryForObject(
			"SELECT created_at FROM bids WHERE auction_id = ?", LocalDateTime.class, auction.getId()))
			.isEqualTo(LocalDateTime.ofInstant(endAt.minusMillis(1), ZoneOffset.UTC));
		assertCommonInvariants(auction);
	}

	// 공통 불변조건(docs/backend/concurrency-testing.md) 중 수동입찰만 있는 지금 검사할 수 있는 것.
	// AutoBid·Trade·winningBid 항목은 그 기능을 만들 때 더하고, 종료 이후 생성된 Bid가 없는지는 마감 경계 테스트에서 따로 본다
	private void assertCommonInvariants(Auction auction) {
		List<Map<String, Object>> bids = jdbcTemplate.queryForList(
			"SELECT id, amount FROM bids WHERE auction_id = ? ORDER BY id", auction.getId());
		Map<String, Object> row = auctionRow(auction);
		long currentPrice = (Long) row.get("current_price");

		assertThat(bidIncrementPolicy.isValidAmount(currentPrice)).isTrue();

		// Bid 금액은 id 순으로 엄격히 증가한다. 그래서 같은 경매에 같은 금액도 없다
		List<Long> amounts = bids.stream().map(bid -> (Long) bid.get("amount")).toList();
		assertThat(amounts).isSortedAccordingTo(Comparator.naturalOrder()).doesNotHaveDuplicates();

		// leadingBid는 최고 금액 Bid이고, 현재가는 그 금액이다
		if (!bids.isEmpty()) {
			Map<String, Object> highest = bids.getLast();
			assertThat(row.get("leading_bid_id")).isEqualTo(highest.get("id"));
			assertThat(currentPrice).isEqualTo(highest.get("amount"));
		}
	}

	private List<BidOutcome> runAtOnce(List<Callable<BidOutcome>> bids) throws Exception {
		ExecutorService executor = Executors.newFixedThreadPool(bids.size());
		CountDownLatch ready = new CountDownLatch(bids.size());
		CountDownLatch start = new CountDownLatch(1);
		try {
			List<Future<BidOutcome>> futures = new ArrayList<>();
			for (Callable<BidOutcome> bid : bids) {
				futures.add(executor.submit(() -> {
					ready.countDown();
					if (!start.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
						throw new IllegalStateException("동시 입찰 시작 대기 시간이 초과됐습니다.");
					}
					return bid.call();
				}));
			}
			assertThat(ready.await(TIMEOUT_SECONDS, TimeUnit.SECONDS)).isTrue();
			start.countDown();

			List<BidOutcome> outcomes = new ArrayList<>();
			for (Future<BidOutcome> future : futures) {
				outcomes.add(future.get(TIMEOUT_SECONDS, TimeUnit.SECONDS));
			}
			return outcomes;
		} finally {
			start.countDown();
			shutdown(executor);
		}
	}

	// 중간에 실패해 빠져나와도 입찰 스레드가 다음 테스트까지 남지 않게 정리한다
	private static void shutdown(ExecutorService executor) throws InterruptedException {
		executor.shutdownNow();
		executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS);
	}

	// 다른 커넥션에서 잠금 쿼리(FOR UPDATE / FOR SHARE)가 count개 실행 중일 때까지 기다린다.
	// first는 두 번의 확인 동안 계속 락을 기다리므로, 락 대기 제한(3초) 안에 끝나도록 한 번에 1초까지만 기다린다
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
				return new BidOutcome(bidder.getId(), null);
			} catch (BusinessException e) {
				return new BidOutcome(bidder.getId(), e.getErrorCode());
			}
		};
	}

	private List<User> users(int count) {
		return IntStream.range(0, count).mapToObj(i -> fixtures.user()).toList();
	}

	private long countBids(Auction auction) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM bids WHERE auction_id = ?", Long.class, auction.getId());
	}

	private long countBidsWithAmount(Auction auction, long amount) {
		return jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM bids WHERE auction_id = ? AND amount = ?", Long.class, auction.getId(), amount);
	}

	private Map<String, Object> auctionRow(Auction auction) {
		return jdbcTemplate.queryForMap(
			"SELECT current_price, leading_bid_id FROM auctions WHERE id = ?", auction.getId());
	}

	private Long leadingBidderId(Auction auction) {
		return jdbcTemplate.queryForObject(
			"SELECT b.bidder_id FROM auctions a JOIN bids b ON b.id = a.leading_bid_id WHERE a.id = ?",
			Long.class, auction.getId());
	}

	// errorCode가 null이면 받아들여진 입찰
	private record BidOutcome(Long bidderId, ErrorCode errorCode) {

		boolean accepted() {
			return errorCode == null;
		}
	}
}
