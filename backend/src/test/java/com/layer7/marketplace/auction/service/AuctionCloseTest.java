package com.layer7.marketplace.auction.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.dto.AuctionSearchCondition;
import com.layer7.marketplace.auction.dto.AuctionSummaryResponse;
import com.layer7.marketplace.auction.scheduler.AuctionCloseScheduler;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * 경매 종료·낙찰 확정(#47)과 종료 Scheduler (docs/backend/scheduler.md, docs/backend/auction-state.md).
 *
 * <p>종료 대상 조회와 Scheduler는 DB에 있는 모든 경매를 본다. 다른 테스트가 남긴 경매(2026년 기준)가 마감 지난 대상으로 섞이지 않도록
 * 이 테스트는 그보다 이른 2001년 시각을 쓴다.
 */
class AuctionCloseTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2001-03-01T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired
	private AuctionService auctionService;

	@Autowired
	private AuctionCloseScheduler auctionCloseScheduler;

	@Autowired
	private BidService bidService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	private User seller;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
	}

	@Test
	@DisplayName("마감이 지난 경매를 종료하면 ENDED로 저장되고 선두 입찰이 낙찰로 확정된다")
	void closeWithLeadingBid() {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_500);
		clock.fixAt(endAt);

		// when
		boolean closed = auctionService.closeAuction(auction.getId());

		// then
		assertThat(closed).isTrue();
		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("status")).isEqualTo("ENDED");
		assertThat(row.get("winning_bid_id")).isNotNull().isEqualTo(row.get("leading_bid_id"));
		assertThat(row.get("current_price")).isEqualTo(10_500L);
	}

	@Test
	@DisplayName("입찰 없이 마감된 경매는 유찰로 종료한다")
	void closeWithoutBid() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW);

		// when
		boolean closed = auctionService.closeAuction(auction.getId());

		// then
		assertThat(closed).isTrue();
		Map<String, Object> row = auctionRow(auction);
		assertThat(row.get("status")).isEqualTo("ENDED");
		assertThat(row.get("winning_bid_id")).isNull();
		assertThat(row.get("leading_bid_id")).isNull();
	}

	@Test
	@DisplayName("마감 시각 직전에는 종료하지 않는다")
	void notClosedBeforeEndAt() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plusMillis(1));

		// when
		boolean closed = auctionService.closeAuction(auction.getId());

		// then
		assertThat(closed).isFalse();
		assertThat(auctionRow(auction).get("status")).isEqualTo("READY");
	}

	@Test
	@DisplayName("이미 종료한 경매를 다시 종료해도 아무것도 바뀌지 않는다")
	void closeTwice() {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		clock.fixAt(endAt);
		auctionService.closeAuction(auction.getId());
		Map<String, Object> afterFirstClose = auctionRow(auction);

		// when
		boolean closedAgain = auctionService.closeAuction(auction.getId());

		// then
		// version까지 같으면 두 번째 처리가 행을 고치지 않은 것이다
		assertThat(closedAgain).isFalse();
		assertThat(auctionRow(auction)).isEqualTo(afterFirstClose);
	}

	@Test
	@DisplayName("취소된 경매는 마감이 지나도 종료하지 않는다")
	void canceledIsNotClosed() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW);
		fixtures.storeAuctionStatus(auction.getId(), AuctionStatus.CANCELED);

		// when
		boolean closed = auctionService.closeAuction(auction.getId());

		// then
		assertThat(closed).isFalse();
		assertThat(auctionRow(auction).get("status")).isEqualTo("CANCELED");
	}

	@Test
	@DisplayName("종료 대상은 마감이 지난 READY·OPEN 경매이고, 마감 시각이 이른 순으로 고른다")
	void findAuctionIdsToClose() {
		// given
		Long endedLater = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.minusSeconds(1)).getId();
		Long endedEarlier = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.minusSeconds(2)).getId();
		Long storedOpen = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW).getId();
		fixtures.storeAuctionStatus(storedOpen, AuctionStatus.OPEN);
		Long notYetEnded = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plusSeconds(1)).getId();
		Long storedEnded = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.minusSeconds(3)).getId();
		fixtures.storeAuctionStatus(storedEnded, AuctionStatus.ENDED);
		Long canceled = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.minusSeconds(3)).getId();
		fixtures.storeAuctionStatus(canceled, AuctionStatus.CANCELED);

		// when
		List<Long> auctionIds = auctionService.findAuctionIdsToClose(100);

		// then
		assertThat(auctionIds)
			.containsSubsequence(endedEarlier, endedLater, storedOpen)
			.doesNotContain(notYetEnded, storedEnded, canceled);
	}

	@Test
	@DisplayName("Scheduler가 돌기 전에는 ENDED·확정 전으로, 돈 뒤에는 확정된 낙찰로 목록에 보인다")
	void schedulerFinalizesEndedAuctions() {
		// given
		String title = "종료" + UUID.randomUUID().toString().substring(0, 8);
		Instant endAt = NOW.plus(HOUR);
		Auction sold = fixtures.auction(seller, title + "-낙찰", Category.DIGITAL, 10_000, NOW.minus(HOUR), endAt);
		Auction unsold = fixtures.auction(seller, title + "-유찰", Category.DIGITAL, 10_000, NOW.minus(HOUR), endAt);
		bidService.placeManualBid(sold.getId(), fixtures.user().getId(), 10_000);
		clock.fixAt(endAt);
		assertThat(summary(title, sold).finalized()).isFalse();
		assertThat(summary(title, sold).status()).isEqualTo(AuctionStatus.ENDED);

		// when
		auctionCloseScheduler.closeEndedAuctions();

		// then
		assertThat(summary(title, sold).finalized()).isTrue();
		assertThat(summary(title, unsold).finalized()).isTrue();
		assertThat(auctionRow(sold).get("winning_bid_id")).isNotNull();
		assertThat(auctionRow(unsold).get("winning_bid_id")).isNull();
	}

	private AuctionSummaryResponse summary(String keyword, Auction auction) {
		return auctionService.searchAuctions(new AuctionSearchCondition(null, null, keyword, null), 0, 20)
			.content().stream()
			.filter(item -> item.auctionId().equals(auction.getId()))
			.findFirst()
			.orElseThrow();
	}

	private Map<String, Object> auctionRow(Auction auction) {
		return jdbcTemplate.queryForMap(
			"SELECT status, current_price, leading_bid_id, winning_bid_id, version FROM auctions WHERE id = ?",
			auction.getId());
	}
}
