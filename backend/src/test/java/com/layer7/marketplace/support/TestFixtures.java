package com.layer7.marketplace.support;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.EntityManager;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 통합 테스트에서 회원·상품·경매 같은 테스트 데이터를 만든다. 만든 엔티티는 트랜잭션이 끝난 상태로 돌려주므로 id만 쓴다.
 *
 * <p>통합 테스트는 DB를 함께 쓰므로 UNIQUE 컬럼(이메일, 닉네임)은 매번 다른 값을 쓴다.
 */
@Component
public class TestFixtures {

	private static final String DEFAULT_REGION_CODE = "11200";

	private final EntityManager em;
	private final TransactionTemplate tx;
	private final JdbcTemplate jdbcTemplate;

	public TestFixtures(EntityManager em, TransactionTemplate tx, JdbcTemplate jdbcTemplate) {
		this.em = em;
		this.tx = tx;
		this.jdbcTemplate = jdbcTemplate;
	}

	public User user() {
		return tx.execute(status -> {
			String suffix = UUID.randomUUID().toString().substring(0, 8);
			User user = User.create(suffix + "@example.com", "password-hash", "user-" + suffix, region());
			em.persist(user);
			return user;
		});
	}

	// seller의 상품으로 READY 경매를 만든다. 시작 시각이 지났으면 첫 입찰에서 OPEN으로 바뀐다
	public Auction auction(User seller, long startPrice, Instant startAt, Instant endAt) {
		return tx.execute(status -> {
			Product product = Product.create(
				em.getReference(User.class, seller.getId()),
				Category.DIGITAL,
				"테스트 상품",
				"테스트 상품 설명",
				ProductCondition.GOOD,
				"사용감 적음"
			);
			em.persist(product);

			Auction auction = Auction.create(product, startPrice, startAt, endAt);
			em.persist(auction);
			return auction;
		});
	}

	// 회원탈퇴 기능이 아직 없어 상태만 바꾼다
	public void withdraw(Long userId) {
		jdbcTemplate.update("UPDATE users SET status = 'WITHDRAWN' WHERE id = ?", userId);
	}

	public void restrictTrading(Long userId, Instant startsAt, Instant endsAt) {
		jdbcTemplate.update(
			"""
			INSERT INTO user_restrictions (user_id, type, reason, source, starts_at, ends_at, created_at)
			VALUES (?, 'TRADING', 'ADMIN_ACTION', 'ADMIN', ?, ?, ?)
			""",
			userId, utc(startsAt), utc(endsAt), utc(startsAt)
		);
	}

	private Region region() {
		return em.createQuery("SELECT r FROM Region r WHERE r.regionCode = :code", Region.class)
			.setParameter("code", DEFAULT_REGION_CODE)
			.getSingleResult();
	}

	// DATETIME 컬럼에는 UTC 시각을 그대로 넣는다 (서버 시간대와 무관하게)
	private static LocalDateTime utc(Instant instant) {
		return LocalDateTime.ofInstant(instant, ZoneOffset.UTC);
	}
}
