package com.layer7.marketplace.global.security;

import jakarta.servlet.DispatcherType;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.servlet.HandlerExceptionResolver;

/**
 * 인증이 필요한 API와 공개 API를 나눈다. 로그인 상태는 요청마다 Access Token(JWT)으로 확인하고 서버 세션에 두지 않는다.
 */
@Configuration
public class SecurityConfig {

	@Bean
	public SecurityFilterChain securityFilterChain(
		HttpSecurity http,
		@Qualifier("handlerExceptionResolver")
		HandlerExceptionResolver exceptionResolver
	) throws Exception {
		http
			// Access Token은 Authorization 헤더로만 받고, Refresh Token 쿠키는 SameSite=Strict라
			// 다른 사이트에서 보낸 요청에는 실리지 않는다 (docs/05-api-spec.md 인증)
			.csrf(AbstractHttpConfigurer::disable)
			.sessionManagement(session -> session
				.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
			)
			.formLogin(AbstractHttpConfigurer::disable)
			.httpBasic(AbstractHttpConfigurer::disable)
			.logout(AbstractHttpConfigurer::disable)
			.authorizeHttpRequests(authorize -> authorize
				// 처리 중 난 오류를 /error로 넘길 때 다시 인증을 요구하면 원래 오류 대신 401이 나간다
				.dispatcherTypeMatchers(DispatcherType.ERROR)
				.permitAll()
				.requestMatchers("/api/v1/auth/**")
				.permitAll()
				.requestMatchers(
					HttpMethod.GET,
					"/api/v1/regions",
					"/api/v1/categories",
					"/api/v1/bid-increment-policy",
					"/actuator/health"
				)
				.permitAll()
				// WebSocket은 연결 뒤 STOMP CONNECT 프레임의 토큰으로 인증한다 (docs/api/realtime.md)
				.requestMatchers("/ws/**")
				.permitAll()
				.anyRequest()
				.authenticated()
			)
			// JWT 인증 필터(#26)는 여기에 addFilterBefore(..., UsernamePasswordAuthenticationFilter.class)로 넣는다
			// 필터 단계의 인증 실패·권한 없음도 전역 예외 처리기로 넘겨 05 명세의 공통 오류 형식으로 응답한다
			.exceptionHandling(exceptions -> exceptions
				.authenticationEntryPoint((request, response, exception) ->
					exceptionResolver.resolveException(
						request, response, null, exception
					)
				)
				.accessDeniedHandler((request, response, exception) ->
					exceptionResolver.resolveException(
						request, response, null, exception
					)
				)
			);

		return http.build();
	}

	@Bean
	public PasswordEncoder passwordEncoder() {
		return new BCryptPasswordEncoder();
	}
}
