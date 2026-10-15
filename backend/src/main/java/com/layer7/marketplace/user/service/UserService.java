package com.layer7.marketplace.user.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.trust.dto.TradingRestrictionResponse;
import com.layer7.marketplace.trust.service.TrustService;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.dto.UserMeResponse;
import com.layer7.marketplace.user.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
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

	// 입찰처럼 진행 중에 회원 상태가 바뀌면 안 되는 쓰기 작업에서 회원을 FOR SHARE로 잠그고 ACTIVE인지 확인한다.
	// 회원탈퇴는 같은 회원을 FOR UPDATE로 잠그므로 둘이 겹치면 한쪽이 기다린다 (docs/backend/locking.md)
	@Transactional(propagation = Propagation.MANDATORY)
	public User getActiveUserForShare(Long userId) {
		User user = userRepository.findByIdForShare(userId)
			.orElseThrow(() ->
				new BusinessException(ErrorCode.INVALID_TOKEN)
			);

		if (!user.isActive()) {
			throw new BusinessException(ErrorCode.ACCOUNT_WITHDRAWN);
		}

		return user;
	}
}
