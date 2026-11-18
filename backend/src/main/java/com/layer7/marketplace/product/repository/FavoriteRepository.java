package com.layer7.marketplace.product.repository;

import com.layer7.marketplace.product.domain.Favorite;
import com.layer7.marketplace.product.domain.ProductStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface FavoriteRepository extends JpaRepository<Favorite, Long> {

	boolean existsByUserIdAndProductId(Long userId, Long productId);

	// 상품 정보를 함께 읽는다. 제외할 상태(삭제된 상품)는 목록에 보이지 않는다
	@Query(
		value = """
			SELECT f FROM Favorite f JOIN FETCH f.product p
			WHERE f.userId = :userId AND p.status <> :excluded
			""",
		countQuery = """
			SELECT COUNT(f) FROM Favorite f JOIN f.product p
			WHERE f.userId = :userId AND p.status <> :excluded
			"""
	)
	Page<Favorite> findMyFavorites(
		@Param("userId") Long userId,
		@Param("excluded") ProductStatus excluded,
		Pageable pageable
	);

	@Modifying
	@Query("DELETE FROM Favorite f WHERE f.userId = :userId AND f.product.id = :productId")
	int deleteByUserIdAndProductId(@Param("userId") Long userId, @Param("productId") Long productId);
}
