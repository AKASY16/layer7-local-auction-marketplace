package com.layer7.marketplace.product.dto;

import java.util.List;
import org.springframework.data.domain.Page;

// GET /api/v1/users/me/favorites 응답. 05 명세의 페이지 공통 형식
public record FavoritePageResponse(
	List<FavoriteProductResponse> content,
	int page,
	int size,
	long totalElements,
	int totalPages
) {

	public static FavoritePageResponse from(Page<FavoriteProductResponse> result) {
		return new FavoritePageResponse(
			result.getContent(),
			result.getNumber(),
			result.getSize(),
			result.getTotalElements(),
			result.getTotalPages()
		);
	}
}
