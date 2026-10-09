package com.layer7.marketplace.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.support.IntegrationTest;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

class SignupConcurrencyTest extends IntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@ParameterizedTest
	@ValueSource(strings = {"EMAIL", "NICKNAME"})
	@DisplayName("동시 중복 가입은 하나만 성공하고 나머지는 중복 오류를 반환한다")
	void concurrentSignup(String scenario) throws Exception {
		// given
		int requestCount = 4;
		String sharedEmail = uniqueEmail();
		String sharedNickname = uniqueNickname();

		Long regionId = jdbcTemplate.queryForObject(
			"SELECT id FROM regions WHERE region_code = ?",
			Long.class,
			"11200"
		);

		String expectedCode = scenario.equals("EMAIL")
			? "DUPLICATE_EMAIL"
			: "DUPLICATE_NICKNAME";

		CountDownLatch ready = new CountDownLatch(requestCount);
		CountDownLatch start = new CountDownLatch(1);

		ExecutorService executor =
			Executors.newFixedThreadPool(requestCount);

		List<Future<SignupResult>> futures = new ArrayList<>();
		List<SignupResult> results = new ArrayList<>();

		try {
			for (int i = 0; i < requestCount; i++) {
				String email = scenario.equals("EMAIL")
					? sharedEmail
					: uniqueEmail();

				String nickname = scenario.equals("NICKNAME")
					? sharedNickname
					: uniqueNickname();

				futures.add(executor.submit(() -> {
					ready.countDown();

					if (!start.await(15, TimeUnit.SECONDS)) {
						throw new IllegalStateException(
							"동시 요청 시작 대기 시간이 초과됐습니다."
						);
					}

					return signup(email, nickname, regionId);
				}));
			}

			assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();

			// when
			start.countDown();

			for (Future<SignupResult> future : futures) {
				results.add(future.get(30, TimeUnit.SECONDS));
			}

			// then
			assertThat(results)
				.filteredOn(result -> result.status() == 201)
				.hasSize(1);

			assertThat(results)
				.filteredOn(result -> result.status() == 409)
				.hasSize(requestCount - 1)
				.allSatisfy(result ->
					assertThat(result.code()).isEqualTo(expectedCode)
				);

			String countSql = scenario.equals("EMAIL")
				? "SELECT COUNT(*) FROM users WHERE email = ?"
				: "SELECT COUNT(*) FROM users WHERE nickname = ?";

			String sharedValue = scenario.equals("EMAIL")
				? sharedEmail
				: sharedNickname;

			Long savedCount = jdbcTemplate.queryForObject(
				countSql,
				Long.class,
				sharedValue
			);

			assertThat(savedCount).isEqualTo(1L);
		} finally {
			start.countDown();
			executor.shutdownNow();
			executor.awaitTermination(10, TimeUnit.SECONDS);
		}
	}

	private SignupResult signup(
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

		var response = mockMvc.perform(
			post("/api/v1/auth/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(body)
		).andReturn().getResponse();

		int responseStatus = response.getStatus();

		String code = responseStatus == 409
			? JsonPath.read(
			response.getContentAsString(StandardCharsets.UTF_8),
			"$.code"
		)
			: null;

		return new SignupResult(responseStatus, code);
	}

	private String uniqueEmail() {
		return UUID.randomUUID() + "@example.com";
	}

	private String uniqueNickname() {
		return "user-" + UUID.randomUUID().toString().substring(0, 12);
	}

	private record SignupResult(int status, String code) {
	}
}
