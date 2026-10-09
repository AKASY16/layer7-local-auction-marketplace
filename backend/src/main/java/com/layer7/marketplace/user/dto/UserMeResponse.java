package com.layer7.marketplace.user.dto;

import com.layer7.marketplace.region.dto.RegionResponse;
import com.layer7.marketplace.trust.dto.TradingRestrictionResponse;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.domain.UserStatus;

public record UserMeResponse(
	Long id,
	String email,
	String nickname,
	int trustScore,
	UserStatus status,
	RegionResponse region,
	TradingRestrictionResponse tradingRestriction
) {

	public static UserMeResponse from(
		User user,
		TradingRestrictionResponse tradingRestriction
	) {
		return new UserMeResponse(
			user.getId(),
			user.getEmail(),
			user.getNickname(),
			user.getTrustScore(),
			user.getStatus(),
			RegionResponse.from(user.getRegion()),
			tradingRestriction
		);
	}
}
