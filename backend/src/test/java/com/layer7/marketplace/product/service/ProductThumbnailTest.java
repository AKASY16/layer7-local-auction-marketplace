package com.layer7.marketplace.product.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.entry;

import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.product.domain.ProductImage;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.EntityManager;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.transaction.support.TransactionTemplate;

class ProductThumbnailTest extends IntegrationTest {

	@Autowired
	private ProductService productService;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private EntityManager em;

	@Autowired
	private TransactionTemplate tx;

	@Value("${auction.storage.public-url}")
	private String publicUrl;

	private User seller;

	@BeforeEach
	void setUp() {
		seller = fixtures.user();
	}

	@Test
	@DisplayName("요청한 상품들의 첫 이미지 URL만 반환하고 이미지 없는 상품과 없는 id는 제외한다")
	void firstImagesForRequestedProducts() {
		// given
		String firstKey = objectKey();
		String secondKey = objectKey();
		Long first = productWithImages(firstKey, objectKey());
		Long second = productWithImages(secondKey);
		Long withoutImage = productWithImages();
		productWithImages(objectKey());

		// when
		Map<Long, String> thumbnails = productService.getThumbnailUrls(
			List.of(first, second, withoutImage, Long.MAX_VALUE, first));

		// then
		assertThat(thumbnails).containsOnly(
			entry(first, publicUrl + "/" + firstKey),
			entry(second, publicUrl + "/" + secondKey));
	}

	@Test
	@DisplayName("상품 id 목록이 비어 있으면 빈 썸네일 Map을 반환한다")
	void emptyProductIds() {
		// given
		List<Long> productIds = List.of();

		// when
		Map<Long, String> thumbnails = productService.getThumbnailUrls(productIds);

		// then
		assertThat(thumbnails).isEmpty();
	}

	private Long productWithImages(String... keys) {
		return tx.execute(status -> {
			Product product = Product.create(em.getReference(User.class, seller.getId()), Category.HOBBY_GAME,
				"썸네일 조회 상품", "상품 설명", ProductCondition.GOOD, "사용감 있음");
			em.persist(product);
			for (int index = 0; index < keys.length; index++) {
				em.persist(ProductImage.create(product, keys[index], index));
			}
			return product.getId();
		});
	}

	private String objectKey() {
		return "uploads/" + UUID.randomUUID();
	}
}
