package com.layer7.marketplace.product.domain;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.EntityManager;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

class ProductTest extends IntegrationTest {

	@Autowired
	private EntityManager em;

	@Autowired
	private TransactionTemplate tx;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("상품은 판매자의 현재 지역을 그대로 가져오고 판매 중(ACTIVE)으로 시작한다")
	void createProduct() {
		// given
		String longDescription = "사용하던 키보드 판매합니다. ".repeat(50);

		// when
		Long id = tx.execute(status -> {
			User seller = User.create(
					UUID.randomUUID() + "@example.com", "password-hash",
					"seller-" + UUID.randomUUID().toString().substring(0, 8), findRegion("11200"));
			em.persist(seller);
			Product product = Product.create(
					seller, Category.DIGITAL, "중고 키보드", longDescription,
					ProductCondition.GOOD, "키캡에 약간의 사용감이 있고 정상 작동합니다.");
			em.persist(product);
			return product.getId();
		});

		// then
		tx.executeWithoutResult(status -> {
			Product found = em.find(Product.class, id);
			assertThat(found.getRegion().getRegionCode()).isEqualTo("11200");
			assertThat(found.getRegion().getId()).isEqualTo(found.getSeller().getRegion().getId());
			assertThat(found.getStatus()).isEqualTo(ProductStatus.ACTIVE);
			assertThat(found.getDescription()).isEqualTo(longDescription);
		});
		Map<String, Object> row = jdbcTemplate.queryForMap(
				"SELECT category, condition_code, status FROM products WHERE id = ?", id);
		assertThat(row)
				.containsEntry("category", "DIGITAL")
				.containsEntry("condition_code", "GOOD")
				.containsEntry("status", "ACTIVE");
	}

	private Region findRegion(String regionCode) {
		return em.createQuery("SELECT r FROM Region r WHERE r.regionCode = :code", Region.class)
				.setParameter("code", regionCode)
				.getSingleResult();
	}
}
