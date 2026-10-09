package com.layer7.marketplace.auth.dto;

import com.layer7.marketplace.user.domain.User;
import java.time.Instant;
import org.springframework.security.oauth2.jwt.Jwt;

public record LoginResponse(
	String accessToken,
	String tokenType,
	Instant expiresAt,
	LoginUserResponse user
) {

	public static LoginResponse from(User user, Jwt jwt) {
		return new LoginResponse(
			jwt.getTokenValue(),
			"Bearer",
			jwt.getExpiresAt(),
			LoginUserResponse.from(user)
		);
	}
}
