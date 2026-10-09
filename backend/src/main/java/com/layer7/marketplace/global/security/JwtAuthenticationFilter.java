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

public class JwtAuthenticationFilter extends OncePerRequestFilter {

	public static final String INVALID_TOKEN_ATTRIBUTE =
		JwtAuthenticationFilter.class.getName() + ".invalidToken";

	private final JwtTokenProvider jwtTokenProvider;

	public JwtAuthenticationFilter(JwtTokenProvider jwtTokenProvider) {
		this.jwtTokenProvider = jwtTokenProvider;
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
			if (exception.getErrorCode() != ErrorCode.INVALID_TOKEN) {
				throw exception;
			}

			SecurityContextHolder.clearContext();
			request.setAttribute(INVALID_TOKEN_ATTRIBUTE, Boolean.TRUE);
		}

		filterChain.doFilter(request, response);
	}
}
