package com.layer7.marketplace.auth.service;

import com.layer7.marketplace.auth.dto.LoginRequest;
import com.layer7.marketplace.auth.dto.LoginResponse;
import com.layer7.marketplace.auth.dto.SignupRequest;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.region.domain.Region;
import com.layer7.marketplace.region.repository.RegionRepository;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.dto.UserResponse;
import com.layer7.marketplace.user.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {

	private final UserRepository userRepository;
	private final RegionRepository regionRepository;
	private final PasswordEncoder passwordEncoder;
	private final JwtTokenProvider jwtTokenProvider;

	public AuthService(
		UserRepository userRepository,
		RegionRepository regionRepository,
		PasswordEncoder passwordEncoder,
		JwtTokenProvider jwtTokenProvider
	) {
		this.userRepository = userRepository;
		this.regionRepository = regionRepository;
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

		Region region = regionRepository.findById(request.regionId())
			.orElseThrow(() ->
				new BusinessException(ErrorCode.RESOURCE_NOT_FOUND)
			);

		String passwordHash = passwordEncoder.encode(request.password());

		User user = User.create(
			request.email(),
			passwordHash,
			request.nickname(),
			region
		);

		User savedUser = userRepository.save(user);

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
}
