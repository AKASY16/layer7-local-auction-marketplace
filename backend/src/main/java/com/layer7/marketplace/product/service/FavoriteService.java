package com.layer7.marketplace.product.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.product.domain.Favorite;
import com.layer7.marketplace.product.domain.ProductStatus;
import com.layer7.marketplace.product.dto.FavoritePageResponse;
import com.layer7.marketplace.product.dto.FavoriteProductResponse;
import com.layer7.marketplace.product.dto.FavoriteResponse;
import com.layer7.marketplace.product.repository.FavoriteInsertRepository;
import com.layer7.marketplace.product.repository.FavoriteRepository;
import com.layer7.marketplace.product.repository.ProductRepository;
import com.layer7.marketplace.user.service.UserService;
import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 관심상품 등록·해제·조회. 같은 요청을 반복해도 결과가 같다 (docs/api/auth-user-product.md "4. Favorite").
 *
 * <p>삭제된 상품은 상품 조회와 같이 없는 상품으로 본다. 판매된 상품과 내가 판매하는 상품도 등록할 수 있다.
 */
@Service
@Transactional(readOnly = true)
public class FavoriteService {

	// 최신순. 같은 시각에 등록한 것은 나중에 등록한 것(id가 큰 것)이 먼저다
	private static final Sort LATEST_FIRST = Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"));

	private final FavoriteRepository favoriteRepository;
	private final FavoriteInsertRepository favoriteInsertRepository;
	private final ProductRepository productRepository;
	private final ProductService productService;
	private final UserService userService;
	private final Clock clock;

	public FavoriteService(
		FavoriteRepository favoriteRepository,
		FavoriteInsertRepository favoriteInsertRepository,
		ProductRepository productRepository,
		ProductService productService,
		UserService userService,
		Clock clock
	) {
		this.favoriteRepository = favoriteRepository;
		this.favoriteInsertRepository = favoriteInsertRepository;
		this.productRepository = productRepository;
		this.productService = productService;
		this.userService = userService;
		this.clock = clock;
	}

	/**
	 * 관심상품으로 등록한다. 이미 등록돼 있으면 처음 등록 시각을 그대로 두고 같은 결과를 돌려준다.
	 *
	 * <p>등록한 사람에게 나중에 타임 경매 시작 알림이 가므로, 탈퇴한 회원은 입찰과 같이 막는다.
	 * 회원 행을 공유 락으로 읽어 등록과 탈퇴가 겹치지 않게 한다.
	 */
	@Transactional
	public FavoriteResponse favorite(Long userId, Long productId) {
		requireProduct(productId);
		userService.getActiveUserForShare(userId);
		favoriteInsertRepository.insertIfAbsent(userId, productId, Instant.now(clock));
		return new FavoriteResponse(productId, true);
	}

	// 관심상품에서 해제한다. 등록돼 있지 않아도 같은 결과를 돌려준다
	@Transactional
	public FavoriteResponse unfavorite(Long userId, Long productId) {
		requireProduct(productId);
		favoriteRepository.deleteByUserIdAndProductId(userId, productId);
		return new FavoriteResponse(productId, false);
	}

	// 상품 상세의 관심상품 버튼 상태
	public FavoriteResponse getFavorite(Long userId, Long productId) {
		requireProduct(productId);
		return new FavoriteResponse(productId, favoriteRepository.existsByUserIdAndProductId(userId, productId));
	}

	public FavoritePageResponse getMyFavorites(Long userId, int page, int size) {
		Page<Favorite> favorites = favoriteRepository.findMyFavorites(
			userId, ProductStatus.DELETED, PageRequest.of(page, size, LATEST_FIRST));
		Map<Long, String> thumbnails = productService.getThumbnailUrls(
			favorites.getContent().stream().map(favorite -> favorite.getProduct().getId()).toList());

		return FavoritePageResponse.from(favorites.map(favorite ->
			FavoriteProductResponse.from(favorite, thumbnails.get(favorite.getProduct().getId()))));
	}

	private void requireProduct(Long productId) {
		productRepository.findById(productId)
			.filter(product -> product.getStatus() != ProductStatus.DELETED)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
	}
}
