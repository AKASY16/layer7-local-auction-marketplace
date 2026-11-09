package com.layer7.marketplace.product.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.product.domain.ImageUpload;
import com.layer7.marketplace.product.domain.ImageUploadStatus;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductStatus;
import com.layer7.marketplace.product.dto.ProductCreateRequest;
import com.layer7.marketplace.product.dto.ProductResponse;
import com.layer7.marketplace.product.repository.ImageUploadRepository;
import com.layer7.marketplace.product.repository.ProductImageRepository;
import com.layer7.marketplace.product.repository.ProductRepository;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ProductService {

	private final ImageUploadRepository uploads;
	private final ProductRepository products;
	private final ProductImageRepository images;
	private final ProductImageStorage storage;
	private final ProductRegistrationService registration;
	private final Clock clock;

	public ProductService(ImageUploadRepository uploads, ProductRepository products, ProductImageRepository images,
		ProductImageStorage storage, ProductRegistrationService registration, Clock clock) {
		this.uploads = uploads;
		this.products = products;
		this.images = images;
		this.storage = storage;
		this.registration = registration;
		this.clock = clock;
	}

	// HEAD 중 DB 트랜잭션이나 락을 유지하지 않는다. 쓰기 트랜잭션은 별도 서비스에서 시작한다.
	@Transactional(propagation = Propagation.NOT_SUPPORTED)
	public ProductResponse createProduct(Long userId, ProductCreateRequest request) {
		List<String> keys = request.imageKeys();
		if (new HashSet<>(keys).size() != keys.size()) {
			throw new BusinessException(ErrorCode.INVALID_UPLOAD);
		}
		List<ImageUpload> pending = uploads.findByObjectKeyIn(keys);
		Instant now = Instant.now(clock);
		if (pending.size() != keys.size()) {
			throw new BusinessException(ErrorCode.INVALID_UPLOAD);
		}
		for (ImageUpload upload : pending) {
			if (!keys.contains(upload.getObjectKey()) || !upload.getUser().getId().equals(userId)
				|| upload.getStatus() != ImageUploadStatus.PENDING || upload.getCreatedAt().isAfter(now)
				|| !upload.getCreatedAt().isAfter(now.minus(Duration.ofHours(24)))) {
				throw new BusinessException(ErrorCode.INVALID_UPLOAD);
			}
			storage.verifyObject(upload.getObjectKey(), upload.getContentType(), upload.getSize());
		}
		return registration.registerProduct(userId, request);
	}

	public ProductResponse getProduct(Long productId) {
		Product product = products.findById(productId)
			.filter(found -> found.getStatus() != ProductStatus.DELETED)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
		return ProductResponse.from(product, images.findByProductIdOrderBySortOrder(productId), storage);
	}
}
