package com.layer7.marketplace.trust.service;

import com.layer7.marketplace.trust.dto.TradingRestrictionResponse;
import com.layer7.marketplace.trust.repository.UserRestrictionRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class TrustService {

	private final UserRestrictionRepository userRestrictionRepository;
	private final Clock clock;

	public TrustService(
		UserRestrictionRepository userRestrictionRepository,
		Clock clock
	) {
		this.userRestrictionRepository = userRestrictionRepository;
		this.clock = clock;
	}

	public Optional<TradingRestrictionResponse> getActiveTradingRestriction(
		Long userId
	) {
		return userRestrictionRepository.findActiveTradingRestriction(
			userId,
			Instant.now(clock)
		);
	}
}
