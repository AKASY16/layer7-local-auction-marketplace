package com.layer7.marketplace.product.dto;

import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.ProductCondition;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record ProductCreateRequest(
	@NotNull Category category,
	@NotBlank @Size(max = 120) String title,
	@NotBlank @Size(max = 10000) String description,
	@NotNull ProductCondition condition,
	@NotBlank @Size(max = 500) String conditionDescription,
	@NotNull @Size(min = 1, max = 10) List<@NotBlank @Size(max = 512) String> imageKeys
) {
}
