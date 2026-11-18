package com.layer7.marketplace.product.dto;

// 관심상품 등록·해제·여부 조회 응답 (docs/api/auth-user-product.md "4. Favorite")
public record FavoriteResponse(Long productId, boolean favorited) {
}
