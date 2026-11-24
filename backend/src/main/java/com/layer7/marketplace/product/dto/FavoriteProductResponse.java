package com.layer7.marketplace.product.dto;

import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Favorite;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductStatus;
import java.time.Instant;

// GET /api/v1/users/me/favorites 목록 항목. 이미지가 없는 상품은 thumbnailUrl이 null이다
public record FavoriteProductResponse(
	Long productId,
	String title,
	Category category,
	ProductStatus status,
	String thumbnailUrl,
	Instant favoritedAt
) {

	public static FavoriteProductResponse from(Favorite favorite, String thumbnailUrl) {
		Product product = favorite.getProduct();
		return new FavoriteProductResponse(product.getId(), product.getTitle(), product.getCategory(),
			product.getStatus(), thumbnailUrl, favorite.getCreatedAt());
	}
}
