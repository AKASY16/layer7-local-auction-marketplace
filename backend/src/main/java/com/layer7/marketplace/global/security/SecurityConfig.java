package com.layer7.marketplace.global.security;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.servlet.HandlerExceptionResolver;

@Configuration
public class SecurityConfig {

	@Bean
	public SecurityFilterChain securityFilterChain(
		HttpSecurity http,
		@Qualifier("handlerExceptionResolver")
		HandlerExceptionResolver exceptionResolver
	) throws Exception {
		http
			.authorizeHttpRequests(authorize -> authorize
				.requestMatchers(HttpMethod.GET, "/api/v1/regions")
				.permitAll()
				.anyRequest()
				.authenticated()
			)
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
}
