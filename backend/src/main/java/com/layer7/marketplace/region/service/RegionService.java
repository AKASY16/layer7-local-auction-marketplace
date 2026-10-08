package com.layer7.marketplace.region.service;

import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.region.dto.RegionPageResponse;
import com.layer7.marketplace.region.dto.RegionResponse;
import com.layer7.marketplace.region.repository.RegionRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class RegionService {

	private final RegionRepository regionRepository;

	public RegionService(RegionRepository regionRepository) {
		this.regionRepository = regionRepository;
	}

	public RegionPageResponse searchRegions(String query, int page, int size) {
		String keyword = query == null ? "" : query.strip();

		Pageable pageable = PageRequest.of(
			page,
			size,
			Sort.by("sidoName", "sigunguName", "regionCode")
		);

		Page<Region> regions;

		if (keyword.isEmpty()) {
			regions = regionRepository.findAll(pageable);
		} else {
			regions = regionRepository
				.findBySidoNameContainingOrSigunguNameContaining(
					keyword,
					keyword,
					pageable
				);
		}

		return RegionPageResponse.from(regions.map(RegionResponse::from));
	}
}
