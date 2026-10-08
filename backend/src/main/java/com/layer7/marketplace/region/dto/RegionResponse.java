package com.layer7.marketplace.region.dto;

import com.layer7.marketplace.region.domain.Region;

public record RegionResponse(
	Long id,
	String regionCode,
	String sidoName,
	String sigunguName
) {

	public static RegionResponse from(Region region) {
		return new RegionResponse(
			region.getId(),
			region.getRegionCode(),
			region.getSidoName(),
			region.getSigunguName()
		);
	}
}
