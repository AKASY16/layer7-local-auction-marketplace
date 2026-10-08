package com.layer7.marketplace.region.dto;

import java.util.List;
import org.springframework.data.domain.Page;

public record RegionPageResponse(
	List<RegionResponse> content,
	int page,
	int size,
	long totalElements,
	int totalPages
) {

	public static RegionPageResponse from(Page<RegionResponse> result) {
		return new RegionPageResponse(
			result.getContent(),
			result.getNumber(),
			result.getSize(),
			result.getTotalElements(),
			result.getTotalPages()
		);
	}
}
