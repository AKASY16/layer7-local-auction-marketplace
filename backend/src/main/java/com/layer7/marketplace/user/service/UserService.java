package com.layer7.marketplace.user.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.trust.dto.TradingRestrictionResponse;
import com.layer7.marketplace.trust.service.TrustService;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.dto.UserMeResponse;
import com.layer7.marketplace.user.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class UserService {

	private final UserRepository userRepository;
	private final TrustService trustService;

	public UserService(
		UserRepository userRepository,
		TrustService trustService
	) {
		this.userRepository = userRepository;
		this.trustService = trustService;
	}

	public UserMeResponse getMe(Long userId) {
		User user = userRepository.findById(userId)
			.orElseThrow(() ->
				new BusinessException(ErrorCode.INVALID_TOKEN)
			);

		TradingRestrictionResponse restriction =
			trustService.getActiveTradingRestriction(userId)
				.orElse(null);

		return UserMeResponse.from(user, restriction);
	}
}
