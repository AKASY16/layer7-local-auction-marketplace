package com.layer7.marketplace.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.layer7.marketplace.support.IntegrationTest;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class SignupApiTest extends IntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Autowired
	private PasswordEncoder passwordEncoder;

	@Test
	@DisplayName("회원가입하면 회원이 저장되고 비밀번호는 해시로 저장된다")
	void signupSuccessfully() throws Exception {
		// given
		String email = uniqueEmail();
		String nickname = uniqueNickname();
		Long regionId = findRegionId();

		// when
		ResultActions result = signup(email, nickname, regionId);

		// then
		result
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").isNumber())
			.andExpect(jsonPath("$.email").value(email))
			.andExpect(jsonPath("$.nickname").value(nickname))
			.andExpect(jsonPath("$.trustScore").value(0))
			.andExpect(jsonPath("$.status").value("ACTIVE"))
			.andExpect(jsonPath("$.region.id").value(regionId.intValue()))
			.andExpect(jsonPath("$.region.regionCode").value("11200"))
			.andExpect(jsonPath("$.password").doesNotExist())
			.andExpect(jsonPath("$.passwordHash").doesNotExist());

		String passwordHash = jdbcTemplate.queryForObject(
			"SELECT password_hash FROM users WHERE email = ?",
			String.class,
			email
		);

		assertThat(passwordHash).isNotEqualTo("test-password");
		assertThat(passwordEncoder.matches("test-password", passwordHash))
			.isTrue();
	}

	@Test
	@DisplayName("이미 가입한 이메일로 가입하면 DUPLICATE_EMAIL을 반환한다")
	void duplicateEmail() throws Exception {
		// given
		String email = uniqueEmail();
		Long regionId = findRegionId();

		signup(email, uniqueNickname(), regionId)
			.andExpect(status().isCreated());

		// when
		ResultActions result = signup(email, uniqueNickname(), regionId);

		// then
		result
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.code").value("DUPLICATE_EMAIL"));
	}

	@Test
	@DisplayName("이미 사용 중인 닉네임으로 가입하면 DUPLICATE_NICKNAME을 반환한다")
	void duplicateNickname() throws Exception {
		// given
		String nickname = uniqueNickname();
		Long regionId = findRegionId();

		signup(uniqueEmail(), nickname, regionId)
			.andExpect(status().isCreated());

		// when
		ResultActions result = signup(uniqueEmail(), nickname, regionId);

		// then
		result
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.code").value("DUPLICATE_NICKNAME"));
	}

	@Test
	@DisplayName("없는 지역으로 가입하면 RESOURCE_NOT_FOUND를 반환한다")
	void missingRegion() throws Exception {
		// given
		String email = uniqueEmail();
		String nickname = uniqueNickname();
		Long missingRegionId = Long.MAX_VALUE;

		// when
		ResultActions result = signup(email, nickname, missingRegionId);

		// then
		result
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"));
	}

	@Test
	@DisplayName("이메일 형식이 잘못되면 VALIDATION_ERROR를 반환한다")
	void invalidEmail() throws Exception {
		// given
		String email = "not-an-email";
		String nickname = uniqueNickname();
		Long regionId = findRegionId();

		// when
		ResultActions result = signup(email, nickname, regionId);

		// then
		result
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	private ResultActions signup(
		String email,
		String nickname,
		Long regionId
	) throws Exception {
		String body = """
			{
			  "email": "%s",
			  "password": "test-password",
			  "nickname": "%s",
			  "regionId": %d
			}
			""".formatted(email, nickname, regionId);

		return mockMvc.perform(
			post("/api/v1/auth/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(body)
		);
	}

	private Long findRegionId() {
		return jdbcTemplate.queryForObject(
			"SELECT id FROM regions WHERE region_code = ?",
			Long.class,
			"11200"
		);
	}

	private String uniqueEmail() {
		return UUID.randomUUID() + "@example.com";
	}

	private String uniqueNickname() {
		return "user-" + UUID.randomUUID().toString().substring(0, 12);
	}
	@ParameterizedTest
	@ValueSource(strings = {"ASCII", "KOREAN"})
	@DisplayName("UTF-8 기준 72바이트 비밀번호로 가입할 수 있다")
	void passwordAtLimit(String kind) throws Exception {
		// given
		String password = kind.equals("ASCII")
			? "a".repeat(72)
			: "가".repeat(24);

		// when
		ResultActions result = signupWithPassword(password);

		// then
		result.andExpect(status().isCreated());
	}

	@ParameterizedTest
	@ValueSource(strings = {"ASCII", "KOREAN"})
	@DisplayName("UTF-8 기준 72바이트를 넘는 비밀번호는 거부한다")
	void passwordOverLimit(String kind) throws Exception {
		// given
		String password = kind.equals("ASCII")
			? "a".repeat(73)
			: "가".repeat(25);

		// when
		ResultActions result = signupWithPassword(password);

		// then
		result
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
			.andExpect(
				jsonPath("$.fieldErrors[?(@.field == 'password')]")
					.isNotEmpty()
			);
	}

	private ResultActions signupWithPassword(
		String password
	) throws Exception {
		String body = """
		{
		  "email": "%s",
		  "password": "%s",
		  "nickname": "%s",
		  "regionId": %d
		}
		""".formatted(
			uniqueEmail(),
			password,
			uniqueNickname(),
			findRegionId()
		);

		return mockMvc.perform(
			post("/api/v1/auth/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(body)
		);
	}
}

