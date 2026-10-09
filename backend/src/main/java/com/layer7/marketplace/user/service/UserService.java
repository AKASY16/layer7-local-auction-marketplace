package com.layer7.marketplace.user.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.dto.TradingRestrictionResponse;
import com.layer7.marketplace.user.dto.UserMeResponse;
import com.layer7.marketplace.user.repository.UserRepository;
import com.layer7.marketplace.user.repository.UserRestrictionRepository;
import java.time.Clock;
import java.time.Instant;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class UserService {

	private final UserRepository userRepository;
	private final UserRestrictionRepository userRestrictionRepository;
	private final Clock clock;

	public UserService(
		UserRepository userRepository,
		UserRestrictionRepository userRestrictionRepository,
		Clock clock
	) {
		this.userRepository = userRepository;
		this.userRestrictionRepository = userRestrictionRepository;
		this.clock = clock;
	}

	public UserMeResponse getMe(Long userId) {
		User user = userRepository.findById(userId)
			.orElseThrow(() ->
				new BusinessException(ErrorCode.INVALID_TOKEN)
			);

		TradingRestrictionResponse restriction =
			userRestrictionRepository.findActiveTradingRestriction(
				userId,
				Instant.now(clock)
			).orElse(null);

		return UserMeResponse.from(user, restriction);
	}
}
