package com.layer7.marketplace.bid.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.bid.dto.BidCreateResponse;
import com.layer7.marketplace.bid.dto.BidCreateResponse.AuctionSummary;
import com.layer7.marketplace.bid.dto.BidResolution;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

class BidServiceTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-14T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired
	private BidService bidService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	private User seller;
	private User bidder;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		seller = fixtures.user();
		bidder = fixtures.user();
	}

	@Test
	@DisplayName("Bid가 0건이면 시작가로 입찰할 수 있고, 현재가와 선두가 바뀐다")
	void firstBidAtStartPrice() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		BidCreateResponse response = bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		assertThat(response.resolution()).isEqualTo(BidResolution.LEADING);
		assertThat(response.acceptedBid().amount()).isEqualTo(10_000);
		assertThat(response.acceptedBid().createdAt()).isEqualTo(NOW);

		AuctionSummary summary = response.auction();
		assertThat(summary.status()).isEqualTo(AuctionStatus.OPEN);
		assertThat(summary.currentPrice()).isEqualTo(10_000);
		assertThat(summary.nextBidAmount()).isEqualTo(10_500);
		assertThat(summary.bidCount()).isEqualTo(1);
		assertThat(summary.version()).isEqualTo(1);
		assertThat(summary.leadingBidder().id()).isEqualTo(bidder.getId());
		assertThat(summary.currentUserLeading()).isTrue();
		assertThat(summary.serverTime()).isEqualTo(NOW);

		Map<String, Object> row = auctionRow(auction);
		assertThat(row)
			.containsEntry("current_price", 10_000L)
			.containsEntry("leading_bid_id", response.acceptedBid().id())
			.containsEntry("version", 1L);
	}

	@Test
	@DisplayName("시작 시각이 지난 READY 경매는 입찰하는 자리에서 OPEN으로 바뀐다")
	void opensReadyAuctionOnBid() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		assertThat(auctionRow(auction)).containsEntry("status", "READY");

		// when
		bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		assertThat(auctionRow(auction)).containsEntry("status", "OPEN");
	}

	@Test
	@DisplayName("다른 회원이 더 높게 입찰하면 선두와 현재가가 바뀌고 version이 올라간다")
	void higherBidTakesTheLead() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);
		User challenger = fixtures.user();

		// when
		BidCreateResponse response = bidService.placeManualBid(auction.getId(), challenger.getId(), 10_500);

		// then
		AuctionSummary summary = response.auction();
		assertThat(summary.currentPrice()).isEqualTo(10_500);
		assertThat(summary.nextBidAmount()).isEqualTo(11_000);
		assertThat(summary.bidCount()).isEqualTo(2);
		assertThat(summary.version()).isEqualTo(2);
		assertThat(summary.leadingBidder().id()).isEqualTo(challenger.getId());
	}

	@Test
	@DisplayName("시작 시각 전에는 AUCTION_NOT_OPEN으로 거절한다")
	void rejectsBeforeStart() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.plus(HOUR), NOW.plus(HOUR.multipliedBy(2)));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.AUCTION_NOT_OPEN);
	}

	@Test
	@DisplayName("마감 시각 직전까지는 입찰되고, 마감 시각부터는 AUCTION_ENDED로 거절한다")
	void endAtBoundary() {
		// given
		Instant endAt = NOW.plus(HOUR);
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), endAt);
		User lateBidder = fixtures.user();

		// when
		clock.fixAt(endAt.minusMillis(1));
		bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);
		clock.fixAt(endAt);
		ThrowingCallable lateBid = () -> bidService.placeManualBid(auction.getId(), lateBidder.getId(), 10_500);

		// then
		assertErrorCode(lateBid, ErrorCode.AUCTION_ENDED);
		assertThat(auctionRow(auction)).containsEntry("current_price", 10_000L);
	}

	@Test
	@DisplayName("판매자는 본인 경매에 입찰할 수 없다")
	void rejectsSeller() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), seller.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.SELF_BID_FORBIDDEN);
	}

	@Test
	@DisplayName("현재 선두는 수동입찰로 자기 가격을 올릴 수 없다")
	void rejectsLeadingBidder() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_500);

		// then
		assertErrorCode(bid, ErrorCode.ALREADY_LEADING);
	}

	@Test
	@DisplayName("첫 입찰이 시작가보다 낮으면 BID_AMOUNT_TOO_LOW로 거절한다")
	void rejectsFirstBidBelowStartPrice() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 9_900);

		// then
		assertErrorCode(bid, ErrorCode.BID_AMOUNT_TOO_LOW);
	}

	@Test
	@DisplayName("Bid가 있으면 다음 유효 금액 이상이어야 하고, 거절 메시지에 최소 입찰가를 알려준다")
	void rejectsBidBelowNextAmount() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);
		User challenger = fixtures.user();

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), challenger.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.BID_AMOUNT_TOO_LOW);
		assertThatThrownBy(bid).hasMessage("최소 입찰가는 10,500원입니다.");
	}

	@Test
	@DisplayName("가격 단위에 맞지 않는 금액은 INVALID_PRICE_UNIT으로 거절한다")
	void rejectsInvalidPriceUnit() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_300);

		// then
		assertErrorCode(bid, ErrorCode.INVALID_PRICE_UNIT);
	}

	@Test
	@DisplayName("1,000만 원을 넘는 금액은 AMOUNT_LIMIT_EXCEEDED로 거절한다")
	void rejectsAmountOverLimit() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_020_000);

		// then
		assertErrorCode(bid, ErrorCode.AMOUNT_LIMIT_EXCEEDED);
	}

	@Test
	@DisplayName("현재가가 1,000만 원이면 다음 입찰가가 없어 더 이상 입찰할 수 없다")
	void rejectsWhenPriceReachedLimit() {
		// given
		Auction auction = fixtures.auction(seller, 9_980_000, NOW.minus(HOUR), NOW.plus(HOUR));
		BidCreateResponse topBid = bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000_000);
		User challenger = fixtures.user();

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), challenger.getId(), 10_000_000);

		// then
		assertThat(topBid.auction().nextBidAmount()).isNull();
		assertErrorCode(bid, ErrorCode.AMOUNT_LIMIT_EXCEEDED);
	}

	@Test
	@DisplayName("탈퇴한 회원은 ACCOUNT_WITHDRAWN으로 거절한다")
	void rejectsWithdrawnUser() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		fixtures.withdraw(bidder.getId());

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.ACCOUNT_WITHDRAWN);
	}

	@Test
	@DisplayName("거래 참여 정지 중인 회원은 USER_RESTRICTED로 거절한다")
	void rejectsRestrictedUser() {
		// given
		Auction auction = fixtures.auction(seller, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		fixtures.restrictTrading(bidder.getId(), NOW.minus(HOUR), NOW.plus(Duration.ofDays(7)));

		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(auction.getId(), bidder.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.USER_RESTRICTED);
	}

	@Test
	@DisplayName("없는 경매에는 RESOURCE_NOT_FOUND로 응답한다")
	void rejectsUnknownAuction() {
		// when
		ThrowingCallable bid = () -> bidService.placeManualBid(Long.MAX_VALUE, bidder.getId(), 10_000);

		// then
		assertErrorCode(bid, ErrorCode.RESOURCE_NOT_FOUND);
	}

	private Map<String, Object> auctionRow(Auction auction) {
		return jdbcTemplate.queryForMap(
			"SELECT status, current_price, leading_bid_id, version FROM auctions WHERE id = ?",
			auction.getId()
		);
	}

	private static void assertErrorCode(ThrowingCallable call, ErrorCode errorCode) {
		assertThatThrownBy(call)
			.isInstanceOf(BusinessException.class)
			.extracting("errorCode")
			.isEqualTo(errorCode);
	}
}
