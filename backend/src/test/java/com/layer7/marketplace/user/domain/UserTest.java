package com.layer7.marketplace.user.domain;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.support.IntegrationTest;
import jakarta.persistence.EntityManager;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

class UserTest extends IntegrationTest {

	@Autowired
	private EntityManager em;

	@Autowired
	private TransactionTemplate tx;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("새 회원은 ACTIVE 상태와 신뢰점수 0으로 저장되고 가입 시각이 기록된다")
	void createActiveUser() {
		// given
		Instant now = Instant.parse("2026-10-10T01:00:00Z");
		clock.fixAt(now);

		// when
		Long id = tx.execute(status -> {
			User user = User.create(uniqueEmail(), "password-hash", uniqueNickname(), findRegion("11200"));
			em.persist(user);
			return user.getId();
		});

		// then
		tx.executeWithoutResult(status -> {
			User found = em.find(User.class, id);
			assertThat(found.isActive()).isTrue();
			assertThat(found.getTrustScore()).isZero();
			assertThat(found.getRegion().getRegionCode()).isEqualTo("11200");
			assertThat(found.getCreatedAt()).isEqualTo(now);
		});
		Map<String, Object> row = jdbcTemplate.queryForMap("SELECT status, trust_score FROM users WHERE id = ?", id);
		assertThat(row).containsEntry("status", "ACTIVE").containsEntry("trust_score", 0);
	}

	@Test
	@DisplayName("신뢰점수는 원자 UPDATE로만 바뀌고, 옛 값을 들고 있던 엔티티를 저장해도 덮어쓰지 않는다")
	void trustScoreIsNotOverwritten() {
		// given
		User stale = tx.execute(status -> {
			User user = User.create(uniqueEmail(), "password-hash", uniqueNickname(), findRegion("11200"));
			em.persist(user);
			return user;
		});
		jdbcTemplate.update("UPDATE users SET trust_score = trust_score + 5 WHERE id = ?", stale.getId());

		// when
		tx.executeWithoutResult(status -> em.merge(stale));

		// then
		Integer trustScore = jdbcTemplate.queryForObject(
				"SELECT trust_score FROM users WHERE id = ?", Integer.class, stale.getId());
		assertThat(trustScore).isEqualTo(5);
	}

	private Region findRegion(String regionCode) {
		return em.createQuery("SELECT r FROM Region r WHERE r.regionCode = :code", Region.class)
				.setParameter("code", regionCode)
				.getSingleResult();
	}

	// 통합 테스트는 DB를 함께 쓰므로 UNIQUE 컬럼은 테스트마다 다른 값을 쓴다
	private static String uniqueEmail() {
		return UUID.randomUUID() + "@example.com";
	}

	private static String uniqueNickname() {
		return "user-" + UUID.randomUUID().toString().substring(0, 8);
	}
}
