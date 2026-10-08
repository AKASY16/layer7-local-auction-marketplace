package com.layer7.marketplace.region.controller;

import com.layer7.marketplace.region.dto.RegionPageResponse;
import com.layer7.marketplace.region.service.RegionService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/regions")
public class RegionController {

	private final RegionService regionService;

	public RegionController(RegionService regionService) {
		this.regionService = regionService;
	}

	@GetMapping
	public RegionPageResponse searchRegions(
		@RequestParam(name = "query", defaultValue = "")
		@Size(max = 100) String query,
		@RequestParam(name = "page", defaultValue = "0")
		@Min(0) int page,
		@RequestParam(name = "size", defaultValue = "20")
		@Min(1) @Max(50) int size
	) {
		return regionService.searchRegions(query, page, size);
	}
}
