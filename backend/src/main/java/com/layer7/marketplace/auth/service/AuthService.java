package com.layer7.marketplace.auth.service;

import com.layer7.marketplace.auth.dto.LoginRequest;
import com.layer7.marketplace.auth.dto.LoginResponse;
import com.layer7.marketplace.auth.dto.SignupRequest;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.region.service.RegionService;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.dto.UserResponse;
import com.layer7.marketplace.user.repository.UserRepository;
import java.sql.SQLException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {

	private static final Pattern DUPLICATE_KEY_PATTERN =
		Pattern.compile("for key ['`]([^'`]+)['`]\\s*$");

	private final UserRepository userRepository;
	private final RegionService regionService;
	private final PasswordEncoder passwordEncoder;
	private final JwtTokenProvider jwtTokenProvider;

	public AuthService(
		UserRepository userRepository,
		RegionService regionService,
		PasswordEncoder passwordEncoder,
		JwtTokenProvider jwtTokenProvider
	) {
		this.userRepository = userRepository;
		this.regionService = regionService;
		this.passwordEncoder = passwordEncoder;
		this.jwtTokenProvider = jwtTokenProvider;
	}

	@Transactional
	public UserResponse signup(SignupRequest request) {
		if (userRepository.existsByEmail(request.email())) {
			throw new BusinessException(ErrorCode.DUPLICATE_EMAIL);
		}

		if (userRepository.existsByNickname(request.nickname())) {
			throw new BusinessException(ErrorCode.DUPLICATE_NICKNAME);
		}

		Region region = regionService.getRegion(request.regionId());

		String passwordHash = passwordEncoder.encode(request.password());

		User user = User.create(
			request.email(),
			passwordHash,
			request.nickname(),
			region
		);

		User savedUser;

		try {
			savedUser = userRepository.save(user);
		} catch (DataIntegrityViolationException exception) {
			ErrorCode errorCode = findDuplicateUserError(exception);

			if (errorCode == null) {
				throw exception;
			}

			throw new BusinessException(errorCode);
		}

		return UserResponse.from(savedUser);
	}

	public LoginResponse login(LoginRequest request) {
		User user = userRepository.findByEmail(request.email())
			.orElseThrow(() ->
				new BusinessException(ErrorCode.INVALID_CREDENTIALS)
			);

		if (!passwordEncoder.matches(
			request.password(),
			user.getPasswordHash()
		)) {
			throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
		}

		if (!user.isActive()) {
			throw new BusinessException(ErrorCode.ACCOUNT_WITHDRAWN);
		}

		Jwt jwt = jwtTokenProvider.createAccessToken(user.getId());

		return LoginResponse.from(user, jwt);
	}

	private static ErrorCode findDuplicateUserError(
		DataIntegrityViolationException exception
	) {
		for (
			Throwable cause = exception;
			cause != null;
			cause = cause.getCause()
		) {
			if (!(cause instanceof SQLException sqlException)) {
				continue;
			}

			if (sqlException.getErrorCode() != 1062
				|| !"23000".equals(sqlException.getSQLState())) {
				continue;
			}

			String message = sqlException.getMessage();

			if (message == null) {
				continue;
			}

			Matcher matcher = DUPLICATE_KEY_PATTERN.matcher(message);

			if (!matcher.find()) {
				continue;
			}

			String constraintName = matcher.group(1);
			int lastDot = constraintName.lastIndexOf('.');

			if (lastDot >= 0) {
				constraintName = constraintName.substring(lastDot + 1);
			}

			return switch (constraintName) {
				case "uq_users_email" -> ErrorCode.DUPLICATE_EMAIL;
				case "uq_users_nickname" -> ErrorCode.DUPLICATE_NICKNAME;
				default -> null;
			};
		}

		return null;
	}
}
