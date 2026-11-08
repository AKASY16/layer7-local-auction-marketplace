package com.layer7.marketplace.product.controller;

import com.layer7.marketplace.global.security.AuthenticatedUser;
import com.layer7.marketplace.product.dto.ProductImageUploadRequest;
import com.layer7.marketplace.product.dto.ProductImageUploadResponse;
import com.layer7.marketplace.product.service.ProductImageUploadService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/uploads/product-images")
public class ProductImageUploadController {

	private final ProductImageUploadService service;

	public ProductImageUploadController(ProductImageUploadService service) {
		this.service = service;
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public ProductImageUploadResponse issueUploadUrls(@AuthenticationPrincipal AuthenticatedUser user,
		@Valid @RequestBody ProductImageUploadRequest request) {
		return service.issueUploadUrls(user.userId(), request);
	}
}
