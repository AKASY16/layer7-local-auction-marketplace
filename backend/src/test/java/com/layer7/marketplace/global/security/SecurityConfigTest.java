package com.layer7.marketplace.global.security;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.global.time.ClockConfig;
import com.layer7.marketplace.region.controller.RegionController;
import com.layer7.marketplace.region.service.RegionService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

// 보안 규칙은 컨트롤러보다 먼저 적용되므로, 아직 없는 API 경로도 "401이 아니면 통과"로 확인할 수 있다
@WebMvcTest(controllers = RegionController.class)
@Import({SecurityConfig.class, ClockConfig.class})
class SecurityConfigTest {

	@Autowired
	private MockMvcTester mvc;

	@Autowired
	private PasswordEncoder passwordEncoder;

	@MockitoBean
	private RegionService regionService;

	@ParameterizedTest
	@CsvSource({
		"GET, /api/v1/regions",
		"POST, /api/v1/auth/signup",
		"POST, /api/v1/auth/login",
		"POST, /api/v1/auth/refresh",
		"POST, /api/v1/auth/logout",
		"GET, /api/v1/categories",
		"GET, /api/v1/bid-increment-policy",
		"GET, /actuator/health",
		"GET, /ws"
	})
	@DisplayName("공개 경로는 토큰과 CSRF 토큰 없이 보안 필터를 통과한다")
	void publicPaths(String method, String path) {
		// given
		HttpMethod httpMethod = HttpMethod.valueOf(method);

		// when
		MvcTestResult result = mvc.method(httpMethod).uri(path).exchange();

		// then
		assertThat(result.getResponse().getStatus())
				.isNotIn(HttpStatus.UNAUTHORIZED.value(), HttpStatus.FORBIDDEN.value());
	}

	@ParameterizedTest
	@CsvSource({
		"GET, /api/v1/users/me",
		"POST, /api/v1/auctions/1/bids",
		"POST, /api/v1/regions",
		"POST, /api/v1/categories"
	})
	@DisplayName("그 밖의 경로는 토큰이 없으면 05 명세 형식의 401 UNAUTHORIZED로 응답한다")
	void protectedPaths(String method, String path) {
		// given
		HttpMethod httpMethod = HttpMethod.valueOf(method);

		// when
		MvcTestResult result = mvc.method(httpMethod).uri(path).exchange();

		// then
		assertThat(result)
				.hasStatus(HttpStatus.UNAUTHORIZED)
				.bodyJson()
				.isLenientlyEqualTo("""
						{
						  "status": 401,
						  "code": "UNAUTHORIZED",
						  "path": "%s",
						  "traceId": null,
						  "fieldErrors": []
						}
						""".formatted(path));
	}

	@Test
	@DisplayName("인증에 실패해도 서버 세션을 만들지 않는다")
	void stateless() {
		// given
		String path = "/api/v1/users/me";

		// when
		MvcTestResult result = mvc.get().uri(path).exchange();

		// then
		assertThat(result).hasStatus(HttpStatus.UNAUTHORIZED);
		assertThat(result.getRequest().getSession(false)).isNull();
	}

	@ParameterizedTest
	@CsvSource({
		"GET, /login",
		"POST, /logout"
	})
	@DisplayName("Spring Security 기본 로그인 페이지와 로그아웃 경로를 쓰지 않는다")
	void defaultLoginAndLogoutDisabled(String method, String path) {
		// given
		HttpMethod httpMethod = HttpMethod.valueOf(method);

		// when
		MvcTestResult result = mvc.method(httpMethod).uri(path).exchange();

		// then
		assertThat(result).hasStatus(HttpStatus.UNAUTHORIZED);
	}

	@Test
	@DisplayName("비밀번호는 BCrypt로 해시하고 원래 비밀번호와 대조할 수 있다")
	void bcryptPasswordEncoder() {
		// given
		String rawPassword = "password1234";

		// when
		String hash = passwordEncoder.encode(rawPassword);

		// then
		assertThat(hash).startsWith("$2").isNotEqualTo(rawPassword);
		assertThat(passwordEncoder.matches(rawPassword, hash)).isTrue();
		assertThat(passwordEncoder.matches("wrong-password", hash)).isFalse();
	}
}
