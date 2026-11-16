package com.layer7.marketplace.product.dto;

import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.product.domain.ProductImage;
import com.layer7.marketplace.product.domain.ProductStatus;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import com.layer7.marketplace.region.dto.RegionResponse;
import com.layer7.marketplace.user.domain.User;
import java.time.Instant;
import java.util.List;

public record ProductResponse(
	Long id, SellerResponse seller, RegionResponse region, Category category,
	String title, String description, ProductCondition condition, String conditionDescription,
	ProductStatus status, List<ImageResponse> images, Instant createdAt, Instant updatedAt
) {

	public static ProductResponse from(Product product, List<ProductImage> images, ProductImageStorage storage) {
		return new ProductResponse(product.getId(), SellerResponse.from(product.getSeller()),
			RegionResponse.from(product.getRegion()), product.getCategory(), product.getTitle(),
			product.getDescription(), product.getCondition(), product.getConditionDescription(),
			product.getStatus(), images.stream().map(image -> ImageResponse.from(image, storage)).toList(),
			product.getCreatedAt(), product.getUpdatedAt());
	}

	public record SellerResponse(Long id, String nickname, int trustScore) {
		static SellerResponse from(User seller) {
			return new SellerResponse(seller.getId(), seller.getNickname(), seller.getTrustScore());
		}
	}

	public record ImageResponse(Long id, String url, int sortOrder) {
		static ImageResponse from(ProductImage image, ProductImageStorage storage) {
			return new ImageResponse(image.getId(), storage.getPublicUrl(image.getObjectKey()), image.getSortOrder());
		}
	}
}
