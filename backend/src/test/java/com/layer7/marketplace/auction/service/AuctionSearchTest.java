package com.layer7.marketplace.auction.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.dto.AuctionPageResponse;
import com.layer7.marketplace.auction.dto.AuctionSearchCondition;
import com.layer7.marketplace.auction.dto.AuctionSearchStatus;
import com.layer7.marketplace.auction.dto.AuctionSummaryResponse;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * GET /api/v1/auctions의 검색 조건과 응답 내용 (docs/api/auction-bidding.md).
 *
 * <p>테스트 DB를 다른 테스트와 함께 쓰므로 상품 제목에 테스트마다 고유한 표식을 붙이고, 그 표식을 검색어로 써서 이 테스트가 만든 경매만 본다.
 */
class AuctionSearchTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-10-26T03:00:00Z");
	private static final Duration HOUR = Duration.ofHours(1);

	@Autowired
	private AuctionService auctionService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	private String tag;
	private User seller;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
		tag = "검색" + UUID.randomUUID().toString().substring(0, 8);
		seller = fixtures.user();
	}

	@Test
	@DisplayName("상태 조건은 저장 상태가 아니라 서버 시각 기준 논리 상태로 거른다")
	void filterByLogicalStatus() {
		// given
		Long upcoming = auction(NOW.plus(HOUR), NOW.plus(HOUR.multipliedBy(2)));
		Long startedButStoredReady = auction(NOW.minus(HOUR), NOW.plus(HOUR));
		Long storedOpen = auction(NOW.minus(HOUR), NOW.plus(HOUR));
		Long endedButStoredReady = auction(NOW.minus(HOUR.multipliedBy(2)), NOW.minus(HOUR));
		Long storedEnded = auction(NOW.minus(HOUR.multipliedBy(2)), NOW.minus(HOUR));
		Long canceled = auction(NOW.plus(HOUR), NOW.plus(HOUR.multipliedBy(2)));
		fixtures.storeAuctionStatus(storedOpen, AuctionStatus.OPEN);
		fixtures.storeAuctionStatus(storedEnded, AuctionStatus.ENDED);
		fixtures.storeAuctionStatus(canceled, AuctionStatus.CANCELED);

		// when
		List<Long> ready = ids(search(AuctionSearchStatus.READY));
		List<Long> open = ids(search(AuctionSearchStatus.OPEN));
		List<Long> ended = ids(search(AuctionSearchStatus.ENDED));
		List<Long> all = ids(search(null));

		// then
		assertThat(ready).containsExactly(upcoming);
		assertThat(open).containsExactlyInAnyOrder(startedButStoredReady, storedOpen);
		assertThat(ended).containsExactlyInAnyOrder(endedButStoredReady, storedEnded);
		assertThat(all).containsExactlyInAnyOrder(
			upcoming, startedButStoredReady, storedOpen, endedButStoredReady, storedEnded, canceled);
	}

	@Test
	@DisplayName("시작 시각과 같은 순간부터 OPEN, 마감 시각과 같은 순간부터 ENDED로 본다")
	void statusBoundaries() {
		// given
		Long startsNow = auction(NOW, NOW.plus(HOUR));
		Long endsNow = auction(NOW.minus(HOUR), NOW);

		// when
		List<Long> ready = ids(search(AuctionSearchStatus.READY));
		List<Long> open = ids(search(AuctionSearchStatus.OPEN));
		List<Long> ended = ids(search(AuctionSearchStatus.ENDED));

		// then
		assertThat(ready).isEmpty();
		assertThat(open).containsExactly(startsNow);
		assertThat(ended).containsExactly(endsNow);
	}

	@Test
	@DisplayName("응답의 status는 논리 상태이고, finalized는 저장 상태가 ENDED·CANCELED인지다")
	void statusAndFinalized() {
		// given
		Long endedButStoredReady = auction(NOW.minus(HOUR.multipliedBy(2)), NOW.minus(HOUR));
		Long storedEnded = auction(NOW.minus(HOUR.multipliedBy(2)), NOW.minus(HOUR));
		fixtures.storeAuctionStatus(storedEnded, AuctionStatus.ENDED);

		// when
		List<AuctionSummaryResponse> items = search(null).content();

		// then
		assertThat(item(items, endedButStoredReady))
			.extracting(AuctionSummaryResponse::status, AuctionSummaryResponse::finalized)
			.containsExactly(AuctionStatus.ENDED, false);
		assertThat(item(items, storedEnded))
			.extracting(AuctionSummaryResponse::status, AuctionSummaryResponse::finalized)
			.containsExactly(AuctionStatus.ENDED, true);
	}

	@Test
	@DisplayName("지역·카테고리·검색어 조건을 함께 건다")
	void filterByRegionCategoryKeyword() {
		// given
		User haeundaeSeller = fixtures.user("26350");
		Long seongdongDigital = fixtures.auction(
			seller, tag + " 키보드", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR)).getId();
		fixtures.auction(seller, tag + " 의자", Category.FURNITURE, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		fixtures.auction(haeundaeSeller, tag + " 마우스", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		AuctionSearchCondition condition = new AuctionSearchCondition(regionId("11200"), Category.DIGITAL, tag, null);

		// when
		List<Long> result = ids(auctionService.searchAuctions(condition, 0, 50));

		// then
		assertThat(result).containsExactly(seongdongDigital);
	}

	@Test
	@DisplayName("검색어는 앞뒤 공백을 지우고, %와 _는 와일드카드가 아니라 글자 그대로 찾는다")
	void keywordIsLiteral() {
		// given
		Long literal = fixtures.auction(
			seller, tag + "_50%", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR)).getId();
		fixtures.auction(seller, tag + "x50y", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));
		AuctionSearchCondition condition = new AuctionSearchCondition(null, null, "  " + tag + "_50%  ", null);

		// when
		List<Long> result = ids(auctionService.searchAuctions(condition, 0, 50));

		// then
		assertThat(result).containsExactly(literal);
	}

	@Test
	@DisplayName("최신 등록순으로 정렬하고 등록 시각이 같으면 id가 큰 순이며, 페이지를 나눈다")
	void newestFirstAndPaging() {
		// given
		Long first = auction(NOW.minus(HOUR), NOW.plus(HOUR));
		clock.advance(Duration.ofMinutes(1));
		Long second = auction(NOW.minus(HOUR), NOW.plus(HOUR));
		Long third = auction(NOW.minus(HOUR), NOW.plus(HOUR));
		AuctionSearchCondition condition = new AuctionSearchCondition(null, null, tag, null);

		// when
		AuctionPageResponse firstPage = auctionService.searchAuctions(condition, 0, 2);
		AuctionPageResponse secondPage = auctionService.searchAuctions(condition, 1, 2);

		// then
		assertThat(ids(firstPage)).containsExactly(third, second);
		assertThat(ids(secondPage)).containsExactly(first);
		assertThat(firstPage)
			.extracting(
				AuctionPageResponse::page,
				AuctionPageResponse::size,
				AuctionPageResponse::totalElements,
				AuctionPageResponse::totalPages
			)
			.containsExactly(0, 2, 3L, 2);
	}

	@Test
	@DisplayName("목록 항목에 상품 정보와 경매에 복사된 지역을 담고, 상품 이미지 전이라 thumbnailUrl은 null이다")
	void itemContent() {
		// given
		Auction auction = fixtures.auction(
			seller, tag + " 기계식 키보드", Category.DIGITAL, 10_000, NOW.minus(HOUR), NOW.plus(HOUR));

		// when
		AuctionSummaryResponse item = search(null).content().getFirst();

		// then
		assertThat(item.auctionId()).isEqualTo(auction.getId());
		assertThat(item.status()).isEqualTo(AuctionStatus.OPEN);
		assertThat(item.finalized()).isFalse();
		assertThat(item.currentPrice()).isEqualTo(10_000);
		assertThat(item.startAt()).isEqualTo(NOW.minus(HOUR));
		assertThat(item.endAt()).isEqualTo(NOW.plus(HOUR));
		assertThat(item.product().id()).isEqualTo(auction.getProduct().getId());
		assertThat(item.product().title()).isEqualTo(tag + " 기계식 키보드");
		assertThat(item.product().category()).isEqualTo(Category.DIGITAL);
		assertThat(item.product().condition()).isEqualTo(ProductCondition.GOOD);
		assertThat(item.product().thumbnailUrl()).isNull();
		assertThat(item.product().region().id()).isEqualTo(regionId("11200"));
		assertThat(item.product().region().sigunguName()).isEqualTo("성동구");
	}

	private Long auction(Instant startAt, Instant endAt) {
		return fixtures.auction(seller, tag + " 상품", Category.DIGITAL, 10_000, startAt, endAt).getId();
	}

	private AuctionPageResponse search(AuctionSearchStatus status) {
		return auctionService.searchAuctions(new AuctionSearchCondition(null, null, tag, status), 0, 50);
	}

	private Long regionId(String regionCode) {
		return jdbcTemplate.queryForObject("SELECT id FROM regions WHERE region_code = ?", Long.class, regionCode);
	}

	private static List<Long> ids(AuctionPageResponse page) {
		return page.content().stream().map(AuctionSummaryResponse::auctionId).toList();
	}

	private static AuctionSummaryResponse item(List<AuctionSummaryResponse> items, Long auctionId) {
		return items.stream().filter(item -> item.auctionId().equals(auctionId)).findFirst().orElseThrow();
	}
}
