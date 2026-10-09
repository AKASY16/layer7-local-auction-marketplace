package com.layer7.marketplace.global.security;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerExceptionResolver;

public class JwtAuthenticationFilter extends OncePerRequestFilter {

	private final JwtTokenProvider jwtTokenProvider;
	private final HandlerExceptionResolver exceptionResolver;

	public JwtAuthenticationFilter(
		JwtTokenProvider jwtTokenProvider,
		HandlerExceptionResolver exceptionResolver
	) {
		this.jwtTokenProvider = jwtTokenProvider;
		this.exceptionResolver = exceptionResolver;
	}

	@Override
	protected void doFilterInternal(
		HttpServletRequest request,
		HttpServletResponse response,
		FilterChain filterChain
	) throws ServletException, IOException {
		String authorization = request.getHeader(
			HttpHeaders.AUTHORIZATION
		);

		if (authorization == null) {
			filterChain.doFilter(request, response);
			return;
		}

		try {
			if (!authorization.regionMatches(
				true, 0, "Bearer ", 0, 7
			)) {
				throw new BusinessException(ErrorCode.INVALID_TOKEN);
			}

			String token = authorization.substring(7).trim();

			if (token.isEmpty()) {
				throw new BusinessException(ErrorCode.INVALID_TOKEN);
			}

			Long userId = jwtTokenProvider.parseUserId(token);

			AuthenticatedUser principal = new AuthenticatedUser(userId);

			UsernamePasswordAuthenticationToken authentication =
				UsernamePasswordAuthenticationToken.authenticated(
					principal,
					null,
					List.of()
				);

			SecurityContext context =
				SecurityContextHolder.createEmptyContext();
			context.setAuthentication(authentication);
			SecurityContextHolder.setContext(context);

		} catch (BusinessException exception) {
			SecurityContextHolder.clearContext();

			exceptionResolver.resolveException(
				request, response, null, exception
			);
			return;
		}

		filterChain.doFilter(request, response);
	}
}
