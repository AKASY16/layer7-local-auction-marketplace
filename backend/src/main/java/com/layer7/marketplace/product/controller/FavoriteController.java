package com.layer7.marketplace.product.controller;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.AuthenticatedUser;
import com.layer7.marketplace.product.dto.FavoritePageResponse;
import com.layer7.marketplace.product.dto.FavoriteResponse;
import com.layer7.marketplace.product.service.FavoriteService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// 모두 로그인한 본인의 관심상품만 다룬다 (docs/api/auth-user-product.md "4. Favorite")
// 같은 요청을 반복해도 결과가 같으므로 Idempotency-Key를 받지 않는다 (05 명세)
@RestController
@RequestMapping("/api/v1")
public class FavoriteController {

	private final FavoriteService favoriteService;

	public FavoriteController(FavoriteService favoriteService) {
		this.favoriteService = favoriteService;
	}

	@PutMapping("/products/{productId}/favorite")
	public FavoriteResponse favorite(
		@AuthenticationPrincipal AuthenticatedUser user,
		@PathVariable Long productId
	) {
		return favoriteService.favorite(requireUserId(user), productId);
	}

	@DeleteMapping("/products/{productId}/favorite")
	public FavoriteResponse unfavorite(
		@AuthenticationPrincipal AuthenticatedUser user,
		@PathVariable Long productId
	) {
		return favoriteService.unfavorite(requireUserId(user), productId);
	}

	@GetMapping("/products/{productId}/favorite")
	public FavoriteResponse getFavorite(
		@AuthenticationPrincipal AuthenticatedUser user,
		@PathVariable Long productId
	) {
		return favoriteService.getFavorite(requireUserId(user), productId);
	}

	@GetMapping("/users/me/favorites")
	public FavoritePageResponse getMyFavorites(
		@AuthenticationPrincipal AuthenticatedUser user,
		@RequestParam(name = "page", defaultValue = "0")
		@Min(0) int page,
		@RequestParam(name = "size", defaultValue = "20")
		@Min(1) @Max(50) int size
	) {
		return favoriteService.getMyFavorites(requireUserId(user), page, size);
	}

	private static Long requireUserId(AuthenticatedUser user) {
		if (user == null) {
			throw new BusinessException(ErrorCode.UNAUTHORIZED);
		}
		return user.userId();
	}
}
