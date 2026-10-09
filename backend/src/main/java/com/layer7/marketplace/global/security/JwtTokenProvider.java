package com.layer7.marketplace.global.security;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.nimbusds.jose.jwk.source.ImmutableSecret;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Component;

@Component
public class JwtTokenProvider {

	private static final String ISSUER = "layer7-marketplace";

	private static final Duration ACCESS_TOKEN_LIFETIME =
		Duration.ofMinutes(30);

	private final JwtEncoder jwtEncoder;
	private final NimbusJwtDecoder jwtDecoder;
	private final Clock clock;

	public JwtTokenProvider(
		@Value("${auction.jwt.secret}") String secret,
		Clock clock
	) {
		byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);

		if (keyBytes.length < 32) {
			throw new IllegalArgumentException(
				"JWT 서명 키는 최소 32바이트여야 합니다."
			);
		}

		SecretKeySpec key = new SecretKeySpec(keyBytes, "HmacSHA256");

		this.jwtEncoder = new NimbusJwtEncoder(
			new ImmutableSecret<>(key)
		);

		this.jwtDecoder = NimbusJwtDecoder.withSecretKey(key)
			.macAlgorithm(MacAlgorithm.HS256)
			.build();

		JwtTimestampValidator timestampValidator =
			new JwtTimestampValidator(Duration.ZERO);
		timestampValidator.setClock(clock);
		timestampValidator.setAllowEmptyExpiryClaim(false);

		this.jwtDecoder.setJwtValidator(
			new DelegatingOAuth2TokenValidator<>(
				timestampValidator,
				new JwtIssuerValidator(ISSUER)
			)
		);

		this.clock = clock;
	}

	public Jwt createAccessToken(Long userId) {
		Instant now = Instant.now(clock);
		Instant expiresAt = now.plus(ACCESS_TOKEN_LIFETIME);

		JwtClaimsSet claims = JwtClaimsSet.builder()
			.issuer(ISSUER)
			.subject(userId.toString())
			.issuedAt(now)
			.expiresAt(expiresAt)
			.build();

		JwsHeader header = JwsHeader.with(MacAlgorithm.HS256)
			.type("JWT")
			.build();

		return jwtEncoder.encode(
			JwtEncoderParameters.from(header, claims)
		);
	}

	public Long parseUserId(String token) {
		try {
			Jwt jwt = jwtDecoder.decode(token);

			Instant expiresAt = jwt.getExpiresAt();

			if (expiresAt == null
				|| !Instant.now(clock).isBefore(expiresAt)) {
				throw new BusinessException(ErrorCode.INVALID_TOKEN);
			}

			long userId = Long.parseLong(jwt.getSubject());

			if (userId <= 0) {
				throw new BusinessException(ErrorCode.INVALID_TOKEN);
			}

			return userId;
		} catch (JwtException | IllegalArgumentException exception) {
			throw new BusinessException(ErrorCode.INVALID_TOKEN);
		}
	}
}
