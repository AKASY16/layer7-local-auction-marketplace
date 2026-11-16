package com.layer7.marketplace.product.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductImage;
import com.layer7.marketplace.product.dto.ProductCreateRequest;
import com.layer7.marketplace.product.dto.ProductResponse;
import com.layer7.marketplace.product.repository.ImageUploadRepository;
import com.layer7.marketplace.product.repository.ProductImageRepository;
import com.layer7.marketplace.product.repository.ProductRepository;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.service.UserService;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ProductRegistrationService {

	private final UserService users;
	private final ImageUploadRepository uploads;
	private final ProductRepository products;
	private final ProductImageRepository images;
	private final ProductImageStorage storage;
	private final Clock clock;

	public ProductRegistrationService(UserService users, ImageUploadRepository uploads,
		ProductRepository products, ProductImageRepository images, ProductImageStorage storage, Clock clock) {
		this.users = users;
		this.uploads = uploads;
		this.products = products;
		this.images = images;
		this.storage = storage;
		this.clock = clock;
	}

	@Transactional
	public ProductResponse registerProduct(Long userId, ProductCreateRequest request) {
		User seller = users.getActiveUserForShare(userId);
		Instant now = Instant.now(clock);
		// 겹치는 key 묶음의 동시 요청도 같은 순서로 UPDATE해 데드락을 피한다.
		for (String key : request.imageKeys().stream().sorted().toList()) {
			if (uploads.attachPending(key, userId, now.minus(Duration.ofHours(24)), now) != 1) {
				throw new BusinessException(ErrorCode.INVALID_UPLOAD);
			}
		}
		Product product = products.save(Product.create(seller, request.category(), request.title(),
			request.description(), request.condition(), request.conditionDescription()));
		List<ProductImage> attached = new ArrayList<>();
		for (int index = 0; index < request.imageKeys().size(); index++) {
			attached.add(images.save(ProductImage.create(product, request.imageKeys().get(index), index)));
		}
		return ProductResponse.from(product, attached, storage);
	}
}
