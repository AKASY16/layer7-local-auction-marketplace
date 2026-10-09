package com.layer7.marketplace.product.domain;

import com.layer7.marketplace.global.time.BaseTimeEntity;
import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "products")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "seller_id", nullable = false)
	private User seller;

	// 등록 시점 판매자 지역의 스냅숏. 판매자가 나중에 지역을 바꿔도 상품 지역은 그대로다 (docs/api/auth-user-product.md)
	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "region_id", nullable = false)
	private Region region;

	@Enumerated(EnumType.STRING)
	@Column(name = "category", nullable = false, length = 50)
	private Category category;

	@Column(name = "title", nullable = false, length = 120)
	private String title;

	@Column(name = "description", nullable = false, columnDefinition = "TEXT")
	private String description;

	// CONDITION은 MySQL 예약어라 컬럼 이름은 condition_code
	@Enumerated(EnumType.STRING)
	@Column(name = "condition_code", nullable = false, length = 30)
	private ProductCondition condition;

	@Column(name = "condition_description", nullable = false, length = 500)
	private String conditionDescription;

	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false, length = 20)
	private ProductStatus status;

	public static Product create(
		User seller,
		Category category,
		String title,
		String description,
		ProductCondition condition,
		String conditionDescription
	) {
		Product product = new Product();
		product.seller = seller;
		product.region = seller.getRegion();
		product.category = category;
		product.title = title;
		product.description = description;
		product.condition = condition;
		product.conditionDescription = conditionDescription;
		product.status = ProductStatus.ACTIVE;
		return product;
	}
}
