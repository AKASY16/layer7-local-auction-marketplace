package com.layer7.marketplace.product.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.List;

public record ProductImageUploadRequest(
	@NotNull @Size(min = 1, max = 10) List<@NotNull @Valid FileRequest> files
) {
	public record FileRequest(
		@NotNull @Pattern(regexp = "image/(jpeg|png|webp)") String contentType,
		@NotNull @Positive @Max(10 * 1024 * 1024) Long size
	) {
	}
}
