package com.layer7.marketplace.product.controller;

import com.layer7.marketplace.global.security.AuthenticatedUser;
import com.layer7.marketplace.product.dto.ProductCreateRequest;
import com.layer7.marketplace.product.dto.ProductResponse;
import com.layer7.marketplace.product.service.ProductService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/products")
public class ProductController {

	private final ProductService service;

	public ProductController(ProductService service) {
		this.service = service;
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public ProductResponse createProduct(@AuthenticationPrincipal AuthenticatedUser user,
		@Valid @RequestBody ProductCreateRequest request) {
		return service.createProduct(user.userId(), request);
	}

	@GetMapping("/{productId}")
	public ProductResponse getProduct(@PathVariable Long productId) {
		return service.getProduct(productId);
	}
}
