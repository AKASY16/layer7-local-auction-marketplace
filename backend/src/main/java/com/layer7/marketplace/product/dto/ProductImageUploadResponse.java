package com.layer7.marketplace.product.dto;

import com.layer7.marketplace.product.storage.ProductImageStorage.UploadUrl;
import java.util.List;

public record ProductImageUploadResponse(List<UploadUrl> uploads) {
}
