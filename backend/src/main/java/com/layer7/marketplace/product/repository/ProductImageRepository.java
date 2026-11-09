package com.layer7.marketplace.product.repository;

import com.layer7.marketplace.product.domain.ProductImage;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductImageRepository extends JpaRepository<ProductImage, Long> {

	List<ProductImage> findByProductIdOrderBySortOrder(Long productId);

	List<ProductImage> findByProductIdInAndSortOrder(Collection<Long> productIds, int sortOrder);
}
