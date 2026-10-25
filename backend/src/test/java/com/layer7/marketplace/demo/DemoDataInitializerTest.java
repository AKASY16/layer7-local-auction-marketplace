package com.layer7.marketplace.demo;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.auth.service.AuthService;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.support.IntegrationTest;
import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 시연 데이터와 docs/demo.md의 입찰 시연 순서를 확인한다.
 *
 * <p>테스트 컨텍스트는 demo 프로필이 아니라 DemoDataInitializer가 등록되지 않으므로 직접 만든다.
 * 테스트 DB는 다른 테스트와 함께 쓰여 경매 id가 1~5가 아니므로 상품 이름으로 찾는다.
 */
class DemoDataInitializerTest extends IntegrationTest {

	@Autowired
	private ApplicationContext context;

	@Autowired
	private AuthService authService;

	@Autowired
	private BidService bidService;

	@Autowired
	private EntityManager em;

	@Autowired
	private TransactionTemplate tx;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("demo 프로필이 아니면 시연 데이터 생성기가 등록되지 않는다")
	void notRegisteredWithoutDemoProfile() {
		// when
		var initializers = context.getBeansOfType(DemoDataInitializer.class);

		// then
		assertThat(initializers).isEmpty();
	}

	@Test
	@DisplayName("다시 실행해도 시연 데이터를 중복으로 만들지 않는다")
	void createsOnlyOnce() {
		// when
		initializer().run(null);
		initializer().run(null);

		// then
		assertThat(count("SELECT COUNT(*) FROM users WHERE email LIKE 'demo-%@example.com'")).isEqualTo(4);
		assertThat(count(
			"""
			SELECT COUNT(*) FROM auctions a
			JOIN products p ON p.id = a.product_id
			JOIN users u ON u.id = p.seller_id
			WHERE u.email = ?
			""",
			DemoDataInitializer.SELLER_EMAIL
		)).isEqualTo(5);
	}

	@Test
	@DisplayName("demo.http의 순서대로 입찰하면 각 단계가 docs/demo.md에 적은 결과를 낸다")
	void demoScenario() {
		// given
		initializer().run(null);
		Long seller = userId(DemoDataInitializer.SELLER_EMAIL);
		Long bidder1 = userId(DemoDataInitializer.BIDDER1_EMAIL);
		Long bidder2 = userId(DemoDataInitializer.BIDDER2_EMAIL);
		Long keyboard = auctionId("몬스타기어 닌자87 기계식 키보드");
		Long endedCase = auctionId("아이패드 프로 키보드 케이스");
		Long upcomingMouse = auctionId("로지텍 MX Master 3S 마우스");

		assertThat(currentPrice(keyboard)).isEqualTo(85_000);
		assertThat(leaderNickname(keyboard)).isEqualTo("테크러버");

		// when
		bidService.placeManualBid(keyboard, bidder1, 86_000);
		ErrorCode sameAmount = errorCodeOf(() -> bidService.placeManualBid(keyboard, bidder2, 86_000));
		ErrorCode bySeller = errorCodeOf(() -> bidService.placeManualBid(keyboard, seller, 87_000));
		ErrorCode onEnded = errorCodeOf(() -> bidService.placeManualBid(endedCase, bidder2, 60_000));
		ErrorCode onUpcoming = errorCodeOf(() -> bidService.placeManualBid(upcomingMouse, bidder2, 50_000));

		// then
		assertThat(currentPrice(keyboard)).isEqualTo(86_000);
		assertThat(leaderNickname(keyboard)).isEqualTo("익산사는개발자");
		assertThat(sameAmount).isEqualTo(ErrorCode.BID_AMOUNT_TOO_LOW);
		assertThat(bySeller).isEqualTo(ErrorCode.SELF_BID_FORBIDDEN);
		assertThat(onEnded).isEqualTo(ErrorCode.AUCTION_ENDED);
		assertThat(onUpcoming).isEqualTo(ErrorCode.AUCTION_NOT_OPEN);
	}

	private DemoDataInitializer initializer() {
		return new DemoDataInitializer(authService, bidService, em, tx, clock);
	}

	// 성공하면 null, 거절되면 그 ErrorCode
	private static ErrorCode errorCodeOf(Runnable bid) {
		try {
			bid.run();
			return null;
		} catch (BusinessException e) {
			return e.getErrorCode();
		}
	}

	private long count(String sql, Object... args) {
		return jdbcTemplate.queryForObject(sql, Long.class, args);
	}

	private Long userId(String email) {
		return jdbcTemplate.queryForObject("SELECT id FROM users WHERE email = ?", Long.class, email);
	}

	private Long auctionId(String title) {
		return jdbcTemplate.queryForObject(
			"SELECT a.id FROM auctions a JOIN products p ON p.id = a.product_id WHERE p.title = ?",
			Long.class, title);
	}

	private long currentPrice(Long auctionId) {
		return jdbcTemplate.queryForObject("SELECT current_price FROM auctions WHERE id = ?", Long.class, auctionId);
	}

	private String leaderNickname(Long auctionId) {
		return jdbcTemplate.queryForObject(
			"""
			SELECT u.nickname FROM auctions a
			JOIN bids b ON b.id = a.leading_bid_id
			JOIN users u ON u.id = b.bidder_id
			WHERE a.id = ?
			""",
			String.class, auctionId);
	}
}
