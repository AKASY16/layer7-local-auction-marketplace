package com.layer7.marketplace.demo;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auth.dto.SignupRequest;
import com.layer7.marketplace.auth.service.AuthService;
import com.layer7.marketplace.bid.service.BidService;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.EntityManager;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * demo 프로필로 서버를 켜면 시연용 계정·상품·경매·입찰 기록을 만든다. 이미 있으면 다시 만들지 않는다.
 *
 * <p>시각은 실행 시점 기준이라, 시연 직전에 시연용 MySQL을 새로 띄우고 서버를 켠다 (docs/demo.md).
 * 새 DB에서 켜면 경매 id는 만든 순서대로 1~5다.
 */
@Slf4j
@Component
@Profile("demo")
public class DemoDataInitializer implements ApplicationRunner {

	// 시연 계정 공통 비밀번호. 시연용 DB에서만 쓰는 개발용 값이다
	static final String PASSWORD = "layer7-demo";
	static final String SELLER_EMAIL = "demo-seller@example.com";
	static final String BIDDER1_EMAIL = "demo-bidder1@example.com";
	static final String BIDDER2_EMAIL = "demo-bidder2@example.com";
	static final String BIDDER3_EMAIL = "demo-bidder3@example.com";

	// 목업과 같은 지역: 전북특별자치도 익산시
	private static final String REGION_CODE = "52140";

	private final AuthService authService;
	private final BidService bidService;
	private final EntityManager em;
	private final TransactionTemplate tx;
	private final Clock clock;

	public DemoDataInitializer(
		AuthService authService,
		BidService bidService,
		EntityManager em,
		TransactionTemplate tx,
		Clock clock
	) {
		this.authService = authService;
		this.bidService = bidService;
		this.em = em;
		this.tx = tx;
		this.clock = clock;
	}

	@Override
	public void run(ApplicationArguments args) {
		if (alreadyCreated()) {
			log.info("시연 데이터가 이미 있어 새로 만들지 않습니다");
			return;
		}

		DemoAuctions auctions = create();
		log.info(
			"시연 데이터를 만들었습니다. 경매 id: 키보드={}, 커피머신={}, 의자={} (진행 중), 키보드 케이스={} (마감), 마우스={} (시작 전)",
			auctions.keyboard(),
			auctions.coffeeMachine(),
			auctions.chair(),
			auctions.endedCase(),
			auctions.upcomingMouse()
		);
	}

	DemoAuctions create() {
		Long regionId = regionId();
		Long seller = signup(SELLER_EMAIL, "김레이어", regionId);
		Long bidder1 = signup(BIDDER1_EMAIL, "익산사는개발자", regionId);
		Long bidder2 = signup(BIDDER2_EMAIL, "키보드좋아", regionId);
		Long bidder3 = signup(BIDDER3_EMAIL, "테크러버", regionId);

		Instant now = Instant.now(clock);
		Instant started = now.minus(Duration.ofHours(1));
		Instant closing = now.plus(Duration.ofDays(1));

		Long keyboard = auction(
			seller, Category.DIGITAL, "몬스타기어 닌자87 기계식 키보드",
			"1년 정도 사용한 닌자87입니다. 전체적으로 깨끗하고 모든 키 정상 작동합니다. 구성품(본체, 케이블, 키캡 리무버) 포함입니다.",
			ProductCondition.GOOD, "생활기스 적음, 1년 사용",
			70_000, started, closing
		);
		Long coffeeMachine = auction(
			seller, Category.HOME_APPLIANCE, "드롱기 아이코나 커피머신",
			"2년 사용했고 작동은 정상입니다. 구성품 모두 포함입니다.",
			ProductCondition.GOOD, "작동 정상, 구성품 포함, 2년 사용",
			35_000, started, closing
		);
		Long chair = auction(
			seller, Category.FURNITURE, "시디즈 T50 사무용 의자",
			"정품이고 매우 양호한 상태입니다. 직접 가져가셔야 합니다.",
			ProductCondition.LIKE_NEW, "정품, 매우 양호",
			100_000, started, closing
		);
		Long endedCase = auction(
			seller, Category.DIGITAL, "아이패드 프로 키보드 케이스",
			"12.9인치용 정품 케이스입니다.",
			ProductCondition.FAIR, "사용감 있음",
			60_000, now.minus(Duration.ofDays(2)), now.minus(Duration.ofHours(1))
		);
		Long upcomingMouse = auction(
			seller, Category.DIGITAL, "로지텍 MX Master 3S 마우스",
			"3개월 사용했습니다. 박스와 동글 포함입니다.",
			ProductCondition.LIKE_NEW, "3개월 사용, 박스 포함",
			50_000, now.plus(Duration.ofDays(1)), now.plus(Duration.ofDays(3))
		);

		// 입찰 기록. 금액은 가격 단위표에 맞춘다 (5만~10만 원은 1,000원, 1만~5만 원은 500원, 10만~50만 원은 5,000원 단위)
		bid(keyboard, bidder2, 70_000);
		bid(keyboard, bidder3, 75_000);
		bid(keyboard, bidder2, 80_000);
		bid(keyboard, bidder3, 85_000);

		bid(coffeeMachine, bidder1, 35_000);
		bid(coffeeMachine, bidder2, 38_000);
		bid(coffeeMachine, bidder3, 40_000);
		bid(coffeeMachine, bidder1, 42_000);

		bid(chair, bidder3, 100_000);
		bid(chair, bidder1, 110_000);
		bid(chair, bidder2, 120_000);

		return new DemoAuctions(keyboard, coffeeMachine, chair, endedCase, upcomingMouse);
	}

	private boolean alreadyCreated() {
		Long count = tx.execute(status -> em.createQuery(
				"SELECT COUNT(u) FROM User u WHERE u.email = :email", Long.class)
			.setParameter("email", SELLER_EMAIL)
			.getSingleResult());
		return count != null && count > 0;
	}

	private Long regionId() {
		return tx.execute(status -> em.createQuery(
				"SELECT r.id FROM Region r WHERE r.regionCode = :code", Long.class)
			.setParameter("code", REGION_CODE)
			.getSingleResult());
	}

	private Long signup(String email, String nickname, Long regionId) {
		return authService.signup(new SignupRequest(email, PASSWORD, nickname, regionId)).id();
	}

	private Long auction(
		Long sellerId,
		Category category,
		String title,
		String description,
		ProductCondition condition,
		String conditionDescription,
		long startPrice,
		Instant startAt,
		Instant endAt
	) {
		return tx.execute(status -> {
			Product product = Product.create(
				em.getReference(User.class, sellerId),
				category,
				title,
				description,
				condition,
				conditionDescription
			);
			em.persist(product);

			Auction auction = Auction.create(product, startPrice, startAt, endAt);
			em.persist(auction);
			return auction.getId();
		});
	}

	private void bid(Long auctionId, Long bidderId, long amount) {
		bidService.placeManualBid(auctionId, bidderId, amount);
	}

	record DemoAuctions(Long keyboard, Long coffeeMachine, Long chair, Long endedCase, Long upcomingMouse) {
	}
}
