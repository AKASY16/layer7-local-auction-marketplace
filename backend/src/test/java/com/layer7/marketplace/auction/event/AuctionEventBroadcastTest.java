package com.layer7.marketplace.auction.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.service.AuctionService;
import com.layer7.marketplace.bid.dto.BidCreateResponse;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.StompTestClient;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 공개 경매 소식(/topic/auctions/{auctionId})이 커밋 뒤에만, 바뀐 상태의 version과 함께 나가는지 (docs/api/realtime.md).
 *
 * <p>실제 STOMP 연결로 구독하고 서비스를 호출한다. 소식은 별도 스레드에서 나가므로 받을 때까지 기다린다.
 */
class AuctionEventBroadcastTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-04T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);
	private static final long RECEIVE_SECONDS = 5;
	// 오지 않아야 할 소식은 이 시간 동안 기다려도 없는지로 본다
	private static final long SILENCE_MILLIS = 500;

	@Autowired
	private BidService bidService;

	@Autowired
	private AuctionService auctionService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private TransactionTemplate transactionTemplate;

	@Autowired
	private ApplicationEventPublisher eventPublisher;

	@Autowired
	private SimpMessagingTemplate messagingTemplate;

	private StompTestClient client;
	private User seller;

	@BeforeEach
	void setUp() throws Exception {
		clock.fixAt(NOW);
		seller = fixtures.user();
		client = StompTestClient.connect(port, null);
	}

	@AfterEach
	void closeClient() {
		client.close();
	}

	@Test
	@DisplayName("입찰이 성립하면 구독자에게 가격 변경 소식이 가고, version은 입찰 응답·DB의 version과 같다")
	void priceChangedAfterBid() throws Exception {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		User bidder = fixtures.user();
		BlockingQueue<Map<String, Object>> messages = subscribe(auction);

		// when
		BidCreateResponse response = bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		Map<String, Object> message = messages.poll(RECEIVE_SECONDS, TimeUnit.SECONDS);
		assertThat(message).isNotNull();
		assertThat(message.get("type")).isEqualTo("AUCTION_PRICE_CHANGED");
		assertThat(number(message, "auctionId")).isEqualTo(auction.getId());
		assertThat(number(message, "version"))
			.isEqualTo(response.auction().version())
			.isEqualTo(storedVersion(auction));
		assertThat(message.get("occurredAt")).isEqualTo(NOW.toString());

		Map<?, ?> data = (Map<?, ?>) message.get("data");
		assertThat(((Number) data.get("currentPrice")).longValue()).isEqualTo(10_000L);
		assertThat(((Number) data.get("nextBidAmount")).longValue()).isEqualTo(response.auction().nextBidAmount());
		assertThat(((Number) data.get("bidCount")).longValue()).isEqualTo(1L);
		Map<?, ?> leadingBidder = (Map<?, ?>) data.get("leadingBidder");
		assertThat(((Number) leadingBidder.get("id")).longValue()).isEqualTo(bidder.getId());
		assertThat(leadingBidder.get("nickname")).isEqualTo(bidder.getNickname());
	}

	@Test
	@DisplayName("거절된 입찰은 소식을 보내지 않는다")
	void noEventForRejectedBid() throws Exception {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		BlockingQueue<Map<String, Object>> messages = subscribe(auction);

		// when
		assertThatThrownBy(() -> bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 9_000))
			.isInstanceOf(BusinessException.class);

		// then
		assertThat(messages.poll(SILENCE_MILLIS, TimeUnit.MILLISECONDS)).isNull();
	}

	@Test
	@DisplayName("이벤트를 만든 트랜잭션이 롤백되면 소식을 보내지 않는다")
	void noEventWhenRolledBack() throws Exception {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		BlockingQueue<Map<String, Object>> messages = subscribe(auction);

		// when
		transactionTemplate.executeWithoutResult(status -> {
			eventPublisher.publishEvent(
				new AuctionPriceChangedEvent(auction.getId(), 99, NOW, 10_000, 10_500L, 1, seller.getId(), "롤백"));
			status.setRollbackOnly();
		});

		// then
		assertThat(messages.poll(SILENCE_MILLIS, TimeUnit.MILLISECONDS)).isNull();
	}

	@Test
	@DisplayName("종료 처리가 낙찰을 확정하면 ENDED·finalized 소식이 가고, version은 DB의 version과 같다")
	void statusChangedAfterClose() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		// 소식은 별도 스레드에서 늦게 도착할 수 있으므로, 먼저 구독하고 입찰 소식을 받은 뒤에 종료한다
		BlockingQueue<Map<String, Object>> messages = subscribe(auction);
		bidService.placeManualBid(auction.getId(), fixtures.user().getId(), 10_000);
		assertThat(messages.poll(RECEIVE_SECONDS, TimeUnit.SECONDS))
			.containsEntry("type", "AUCTION_PRICE_CHANGED");
		clock.fixAt(endAt);

		// when
		auctionService.closeAuction(auction.getId());

		// then
		Map<String, Object> message = messages.poll(RECEIVE_SECONDS, TimeUnit.SECONDS);
		assertThat(message).isNotNull();
		assertThat(message.get("type")).isEqualTo("AUCTION_STATUS_CHANGED");
		assertThat(number(message, "version")).isEqualTo(storedVersion(auction));

		Map<?, ?> data = (Map<?, ?>) message.get("data");
		assertThat(data.get("status")).isEqualTo("ENDED");
		assertThat(data.get("finalized")).isEqualTo(true);
		assertThat(((Number) data.get("winningBidId")).longValue()).isEqualTo(winningBidId(auction));
		assertThat(data.get("endAt")).isEqualTo(endAt.toString());
	}

	@Test
	@DisplayName("이미 종료된 경매를 다시 종료하면 소식을 보내지 않는다")
	void noEventWhenAlreadyClosed() throws Exception {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		BlockingQueue<Map<String, Object>> messages = subscribe(auction);
		clock.fixAt(endAt);
		auctionService.closeAuction(auction.getId());
		assertThat(messages.poll(RECEIVE_SECONDS, TimeUnit.SECONDS))
			.containsEntry("type", "AUCTION_STATUS_CHANGED");

		// when
		auctionService.closeAuction(auction.getId());

		// then
		assertThat(messages.poll(SILENCE_MILLIS, TimeUnit.MILLISECONDS)).isNull();
	}

	private BlockingQueue<Map<String, Object>> subscribe(Auction auction) throws InterruptedException {
		String destination = "/topic/auctions/" + auction.getId();
		return client.subscribe(destination, probe -> messagingTemplate.convertAndSend(destination, (Object) probe));
	}

	private static long number(Map<String, Object> message, String key) {
		return ((Number) message.get(key)).longValue();
	}

	private long storedVersion(Auction auction) {
		return jdbcTemplate.queryForObject("SELECT version FROM auctions WHERE id = ?", Long.class, auction.getId());
	}

	private long winningBidId(Auction auction) {
		return jdbcTemplate.queryForObject(
			"SELECT winning_bid_id FROM auctions WHERE id = ?", Long.class, auction.getId());
	}
}
