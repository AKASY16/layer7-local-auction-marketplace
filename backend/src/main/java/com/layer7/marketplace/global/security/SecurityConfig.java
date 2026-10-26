package com.layer7.marketplace.global.security;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
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
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.servlet.HandlerExceptionResolver;

/**
 * 공개 API와 인증이 필요한 API를 구분하고 JWT 인증 필터를 연결한다.
 */
@Configuration
public class SecurityConfig {

	@Bean
	public SecurityFilterChain securityFilterChain(
		HttpSecurity http,
		JwtTokenProvider jwtTokenProvider,
		@Qualifier("handlerExceptionResolver")
		HandlerExceptionResolver exceptionResolver
	) throws Exception {
		JwtAuthenticationFilter jwtFilter =
			new JwtAuthenticationFilter(jwtTokenProvider);

		http
			.csrf(AbstractHttpConfigurer::disable)
			.sessionManagement(session -> session
				.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
			)
			.formLogin(AbstractHttpConfigurer::disable)
			.httpBasic(AbstractHttpConfigurer::disable)
			.logout(AbstractHttpConfigurer::disable)
			.addFilterBefore(
				jwtFilter,
				UsernamePasswordAuthenticationFilter.class
			)
			.authorizeHttpRequests(authorize -> authorize
				// 오류 처리 요청에서 다시 인증을 요구하지 않는다.
				.dispatcherTypeMatchers(DispatcherType.ERROR)
				.permitAll()
				.requestMatchers("/api/v1/auth/**")
				.permitAll()
				.requestMatchers(
					HttpMethod.GET,
					"/api/v1/regions",
					"/api/v1/categories",
					"/api/v1/bid-increment-policy",
					// 로그인하지 않아도 경매 목록·상세·입찰 이력은 볼 수 있다.
					// 입찰·자동입찰·입찰 정책(/auctions/{id}/bid-policy) 같은 입찰용 API는 막아 둔다
					"/api/v1/auctions",
					"/api/v1/auctions/*",
					"/api/v1/auctions/*/bids",
					"/actuator/health"
				)
				.permitAll()
				// WebSocket 인증은 STOMP CONNECT에서 처리한다.
				.requestMatchers("/ws/**")
				.permitAll()
				.anyRequest()
				.authenticated()
			)
			.exceptionHandling(exceptions -> exceptions
				.authenticationEntryPoint((request, response, exception) -> {
					boolean invalidToken = Boolean.TRUE.equals(
						request.getAttribute(
							JwtAuthenticationFilter.INVALID_TOKEN_ATTRIBUTE
						)
					);

					ErrorCode errorCode = invalidToken
						? ErrorCode.INVALID_TOKEN
						: ErrorCode.UNAUTHORIZED;

					exceptionResolver.resolveException(
						request,
						response,
						null,
						new BusinessException(errorCode)
					);
				})
				.accessDeniedHandler((request, response, exception) ->
					exceptionResolver.resolveException(
						request,
						response,
						null,
						exception
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
