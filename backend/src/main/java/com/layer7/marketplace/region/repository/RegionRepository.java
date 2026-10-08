package com.layer7.marketplace.region.repository;

import com.layer7.marketplace.region.domain.Region;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RegionRepository extends JpaRepository<Region, Long> {

	Page<Region> findBySidoNameContainingOrSigunguNameContaining(
		String sidoQuery,
		String sigunguQuery,
		Pageable pageable
	);
}
