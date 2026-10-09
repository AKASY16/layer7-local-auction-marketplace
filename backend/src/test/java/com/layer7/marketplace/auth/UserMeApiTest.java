package com.layer7.marketplace.auth;

import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.support.IntegrationTest;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.util.Calendar;
import java.util.TimeZone;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

class UserMeApiTest extends IntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("가입 후 로그인한 토큰으로 자신의 회원 정보를 조회한다")
	void signupLoginAndGetMe() throws Exception {
		// given
		MemberSession member = createMemberAndLogin();

		// when
		ResultActions result = getMe(member.token());

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.id").value(member.userId().intValue()))
			.andExpect(jsonPath("$.email").value(member.email()))
			.andExpect(jsonPath("$.nickname").value(member.nickname()))
			.andExpect(jsonPath("$.trustScore").value(0))
			.andExpect(jsonPath("$.status").value("ACTIVE"))
			.andExpect(jsonPath("$.region.regionCode").value("11200"))
			.andExpect(jsonPath("$.tradingRestriction").value(nullValue()))
			.andExpect(jsonPath("$.password").doesNotExist())
			.andExpect(jsonPath("$.passwordHash").doesNotExist());
	}

	@Test
	@DisplayName("토큰 없이 내 정보를 조회하면 UNAUTHORIZED를 반환한다")
	void missingToken() throws Exception {
		// given
		// 인증 헤더를 보내지 않는다.

		// when
		ResultActions result = mockMvc.perform(
			get("/api/v1/users/me")
		);

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
	}

	@Test
	@DisplayName("JWT 형식이 아닌 토큰은 INVALID_TOKEN을 반환한다")
	void malformedToken() throws Exception {
		// given
		String token = "not-a-jwt";

		// when
		ResultActions result = getMe(token);

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_TOKEN"));
	}

	@Test
	@DisplayName("서명을 변조한 토큰은 INVALID_TOKEN을 반환한다")
	void tamperedToken() throws Exception {
		// given
		MemberSession member = createMemberAndLogin();

		String[] parts = member.token().split("\\.");
		String signature = parts[2];
		String changedFirstCharacter =
			signature.charAt(0) == 'A' ? "B" : "A";

		parts[2] = changedFirstCharacter + signature.substring(1);
		String tamperedToken = String.join(".", parts);

		// when
		ResultActions result = getMe(tamperedToken);

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_TOKEN"));
	}

	@Test
	@DisplayName("발급 후 정확히 30분이 지나면 INVALID_TOKEN을 반환한다")
	void expiredToken() throws Exception {
		// given
		MemberSession member = createMemberAndLogin();
		clock.advance(Duration.ofMinutes(30));

		// when
		ResultActions result = getMe(member.token());

		// then
		result
			.andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_TOKEN"));
	}

	@Test
	@DisplayName("거래 정지 중이면 사유와 종료 시각을 반환한다")
	void activeRestriction() throws Exception {
		// given
		MemberSession member = createMemberAndLogin();
		Instant now = Instant.now(clock);
		Instant endsAt = now.plus(Duration.ofHours(1));

		createRestriction(
			member.userId(),
			now.minusSeconds(60),
			endsAt,
			null
		);

		// when
		ResultActions result = getMe(member.token());

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.tradingRestriction.reason")
				.value("ADMIN_ACTION"))
			.andExpect(jsonPath("$.tradingRestriction.endsAt")
				.value(endsAt.toString()));
	}

	@ParameterizedTest
	@ValueSource(strings = {"EXPIRED", "LIFTED", "FUTURE"})
	@DisplayName("종료·해제됐거나 시작 전인 정지는 응답에서 제외한다")
	void inactiveRestriction(String scenario) throws Exception {
		// given
		MemberSession member = createMemberAndLogin();
		Instant now = Instant.now(clock);

		Instant startsAt = now.minus(Duration.ofHours(1));
		Instant endsAt = now.plus(Duration.ofHours(1));
		Instant liftedAt = null;

		switch (scenario) {
			case "EXPIRED" -> endsAt = now;
			case "LIFTED" -> liftedAt = now;
			case "FUTURE" -> startsAt = now.plusSeconds(60);
			default -> throw new IllegalArgumentException(scenario);
		}

		createRestriction(
			member.userId(),
			startsAt,
			endsAt,
			liftedAt
		);

		// when
		ResultActions result = getMe(member.token());

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.tradingRestriction").value(nullValue()));
	}

	private MemberSession createMemberAndLogin() throws Exception {
		clock.fixAt(Instant.parse("2026-10-09T03:00:00Z"));

		String email = UUID.randomUUID() + "@example.com";
		String nickname = "user-"
			+ UUID.randomUUID().toString().substring(0, 12);

		Long regionId = jdbcTemplate.queryForObject(
			"SELECT id FROM regions WHERE region_code = ?",
			Long.class,
			"11200"
		);

		String signupBody = """
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
				.content(signupBody)
		).andExpect(status().isCreated());

		Long userId = jdbcTemplate.queryForObject(
			"SELECT id FROM users WHERE email = ?",
			Long.class,
			email
		);

		String loginBody = """
			{
			  "email": "%s",
			  "password": "test-password"
			}
			""".formatted(email);

		String responseBody = mockMvc.perform(
				post("/api/v1/auth/login")
					.contentType(MediaType.APPLICATION_JSON)
					.content(loginBody)
			)
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString(StandardCharsets.UTF_8);

		String token = JsonPath.read(responseBody, "$.accessToken");

		return new MemberSession(userId, email, nickname, token);
	}

	private ResultActions getMe(String token) throws Exception {
		return mockMvc.perform(
			get("/api/v1/users/me")
				.header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
		);
	}

	private void createRestriction(
		Long userId,
		Instant startsAt,
		Instant endsAt,
		Instant liftedAt
	) {
		String sql = """
			INSERT INTO user_restrictions (
			  user_id, type, reason, source,
			  starts_at, ends_at, lifted_at, created_at
			)
			VALUES (?, 'TRADING', 'ADMIN_ACTION', 'ADMIN', ?, ?, ?, ?)
			""";

		jdbcTemplate.update(connection -> {
			var statement = connection.prepareStatement(sql);

			Calendar utc = Calendar.getInstance(
				TimeZone.getTimeZone("UTC")
			);

			statement.setLong(1, userId);
			statement.setTimestamp(2, Timestamp.from(startsAt), utc);
			statement.setTimestamp(3, Timestamp.from(endsAt), utc);
			statement.setTimestamp(
				4,
				liftedAt == null ? null : Timestamp.from(liftedAt),
				utc
			);
			statement.setTimestamp(
				5,
				Timestamp.from(Instant.now(clock)),
				utc
			);

			return statement;
		});
	}

	private record MemberSession(
		Long userId,
		String email,
		String nickname,
		String token
	) {
	}
}
