package com.layer7.marketplace.product.repository;

import com.layer7.marketplace.product.domain.Product;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductRepository extends JpaRepository<Product, Long> {
}
