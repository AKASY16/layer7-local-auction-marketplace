package com.layer7.marketplace.auth.dto;

import com.layer7.marketplace.user.domain.User;

public record LoginUserResponse(
	Long id,
	String nickname,
	int trustScore
) {

	public static LoginUserResponse from(User user) {
		return new LoginUserResponse(
			user.getId(),
			user.getNickname(),
			user.getTrustScore()
		);
	}
}
