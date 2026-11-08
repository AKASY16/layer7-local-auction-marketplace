package com.layer7.marketplace.product.service;

import com.layer7.marketplace.product.domain.ImageUpload;
import com.layer7.marketplace.product.dto.ProductImageUploadRequest;
import com.layer7.marketplace.product.dto.ProductImageUploadResponse;
import com.layer7.marketplace.product.repository.ImageUploadRepository;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import com.layer7.marketplace.product.storage.ProductImageStorage.UploadUrl;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.service.UserService;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ProductImageUploadService {

	private final UserService userService;
	private final ImageUploadRepository uploads;
	private final ProductImageStorage storage;

	public ProductImageUploadService(UserService userService, ImageUploadRepository uploads,
		ProductImageStorage storage) {
		this.userService = userService;
		this.uploads = uploads;
		this.storage = storage;
	}

	@Transactional
	public ProductImageUploadResponse issueUploadUrls(Long userId, ProductImageUploadRequest request) {
		User user = userService.getActiveUserForShare(userId);
		List<UploadUrl> urls = new ArrayList<>();
		for (var file : request.files()) {
			String key = "uploads/" + UUID.randomUUID();
			// 서명은 로컬 연산이므로 트랜잭션 안에서 외부 저장소를 호출하지 않는다.
			urls.add(storage.issueUploadUrl(key, file.contentType()));
			uploads.save(ImageUpload.create(user, key, file.contentType(), file.size()));
		}
		return new ProductImageUploadResponse(List.copyOf(urls));
	}
}
