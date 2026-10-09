package com.layer7.marketplace.user.dto;

import com.layer7.marketplace.region.dto.RegionResponse;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.domain.UserStatus;

public record UserResponse(
	Long id,
	String email,
	String nickname,
	int trustScore,
	UserStatus status,
	RegionResponse region
) {

	public static UserResponse from(User user) {
		return new UserResponse(
			user.getId(),
			user.getEmail(),
			user.getNickname(),
			user.getTrustScore(),
			user.getStatus(),
			RegionResponse.from(user.getRegion())
		);
	}
}
