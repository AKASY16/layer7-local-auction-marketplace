package com.layer7.marketplace.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.support.IntegrationTest;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

class LoginApiTest extends IntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Value("${auction.jwt.secret}")
	private String jwtSecret;

	@Test
	@DisplayName("로그인하면 해당 회원의 JWT를 발급하고 만료 시간은 30분이다")
	void loginSuccessfully() throws Exception {
		// given
		String email = uniqueEmail();
		String nickname = uniqueNickname();
		Long userId = createMember(email, nickname);

		Instant now = Instant.parse("2026-10-09T03:00:00Z");
		clock.fixAt(now);

		// when
		ResultActions result = login(email, "test-password");

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.tokenType").value("Bearer"))
			.andExpect(jsonPath("$.expiresAt")
				.value(now.plus(Duration.ofMinutes(30)).toString()))
			.andExpect(jsonPath("$.user.id").value(userId.intValue()))
			.andExpect(jsonPath("$.user.nickname").value(nickname))
			.andExpect(jsonPath("$.user.trustScore").value(0))
			.andExpect(jsonPath("$.user.password").doesNotExist())
			.andExpect(jsonPath("$.user.passwordHash").doesNotExist());

		String body = result.andReturn()
			.getResponse()
			.getContentAsString(StandardCharsets.UTF_8);

		String token = JsonPath.read(body, "$.accessToken");
		assertThat(token).isNotBlank();

		Jwt jwt = decodeToken(token);

		assertThat(jwt.getSubject()).isEqualTo(userId.toString());
		assertThat(jwt.getIssuedAt()).isEqualTo(now);
		assertThat(jwt.getExpiresAt())
			.isEqualTo(now.plus(Duration.ofMinutes(30)));
	}

	@Test
	@DisplayName("비밀번호가 틀리면 INVALID_CREDENTIALS를 반환한다")
	void wrongPassword() throws Exception {
		// given
		String email = uniqueEmail();
		createMember(email, uniqueNickname());

		// when
		ResultActions result = login(email, "wrong-password");

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"))
			.andExpect(jsonPath("$.accessToken").doesNotExist());
	}

	@Test
	@DisplayName("가입하지 않은 이메일이면 INVALID_CREDENTIALS를 반환한다")
	void unknownEmail() throws Exception {
		// given
		String email = uniqueEmail();

		// when
		ResultActions result = login(email, "test-password");

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"))
			.andExpect(jsonPath("$.accessToken").doesNotExist());
	}

	@Test
	@DisplayName("탈퇴 계정은 비밀번호가 맞아도 ACCOUNT_WITHDRAWN을 반환한다")
	void withdrawnAccount() throws Exception {
		// given
		String email = uniqueEmail();
		Long userId = createMember(email, uniqueNickname());

		jdbcTemplate.update(
			"UPDATE users SET status = 'WITHDRAWN' WHERE id = ?",
			userId
		);

		// when
		ResultActions result = login(email, "test-password");

		// then
		result
			.andExpect(status().isForbidden())
			.andExpect(jsonPath("$.code").value("ACCOUNT_WITHDRAWN"))
			.andExpect(jsonPath("$.accessToken").doesNotExist());
	}

	@Test
	@DisplayName("로그인 이메일 형식이 잘못되면 VALIDATION_ERROR를 반환한다")
	void invalidEmail() throws Exception {
		// given
		String email = "not-an-email";

		// when
		ResultActions result = login(email, "test-password");

		// then
		result
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	private Long createMember(
		String email,
		String nickname
	) throws Exception {
		Long regionId = jdbcTemplate.queryForObject(
			"SELECT id FROM regions WHERE region_code = ?",
			Long.class,
			"11200"
		);

		String body = """
			{
			  "email": "%s",
			  "password": "test-password",
			  "nickname": "%s",
			  "regionId": %d
			}
			""".formatted(email, nickname, regionId);

		mockMvc.perform(
			post("/api/v1/auth/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(body)
		).andExpect(status().isCreated());

		return jdbcTemplate.queryForObject(
			"SELECT id FROM users WHERE email = ?",
			Long.class,
			email
		);
	}

	private ResultActions login(
		String email,
		String password
	) throws Exception {
		String body = """
			{
			  "email": "%s",
			  "password": "%s"
			}
			""".formatted(email, password);

		return mockMvc.perform(
			post("/api/v1/auth/login")
				.contentType(MediaType.APPLICATION_JSON)
				.content(body)
		);
	}

	private Jwt decodeToken(String token) {
		SecretKeySpec key = new SecretKeySpec(
			jwtSecret.getBytes(StandardCharsets.UTF_8),
			"HmacSHA256"
		);

		NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(key)
			.macAlgorithm(MacAlgorithm.HS256)
			.build();

		JwtTimestampValidator timestampValidator =
			new JwtTimestampValidator(Duration.ZERO);
		timestampValidator.setClock(clock);
		timestampValidator.setAllowEmptyExpiryClaim(false);

		decoder.setJwtValidator(
			new DelegatingOAuth2TokenValidator<>(
				timestampValidator,
				new JwtIssuerValidator("layer7-marketplace")
			)
		);

		return decoder.decode(token);
	}

	private String uniqueEmail() {
		return UUID.randomUUID() + "@example.com";
	}

	private String uniqueNickname() {
		return "user-" + UUID.randomUUID().toString().substring(0, 12);
	}
}
