package com.layer7.marketplace.bid.domain;

import java.util.OptionalLong;

import org.springframework.stereotype.Component;

@Component
public class BidIncrementPolicy {

	private static final long MIN_AMOUNT = 100;
	private static final long MAX_AMOUNT = 10_000_000;

	// 허용 범위와 가격 단위에 맞으면 true
	public boolean isValidAmount(long amount) {
		if (amount < MIN_AMOUNT || isAmountLimitExceeded(amount)) {
			return false;
		}

		return amount % getUnit(amount) == 0;
	}

	// 서비스에서 상한 초과와 가격 단위 오류를 구분할 때 사용한다.
	public boolean isAmountLimitExceeded(long amount) {
		return amount > MAX_AMOUNT;
	}

	// 유효한 현재가보다 큰 가장 가까운 유효 금액. 상한에 도달하면 빈 값을 반환한다.
	public OptionalLong nextValidAmount(long currentPrice) {
		if (!isValidAmount(currentPrice)) {
			throw new IllegalArgumentException(
				"현재가는 유효한 금액이어야 합니다."
			);
		}

		long nextAmount = currentPrice + getUnit(currentPrice);

		if (nextAmount > MAX_AMOUNT) {
			return OptionalLong.empty();
		}

		return OptionalLong.of(nextAmount);
	}

	// 가격 구간에 따른 단위
	private long getUnit(long amount) {
		if (amount < 10_000) {
			return 100;
		} else if (amount < 50_000) {
			return 500;
		} else if (amount < 100_000) {
			return 1_000;
		} else if (amount < 500_000) {
			return 5_000;
		} else if (amount < 1_000_000) {
			return 10_000;
		} else {
			return 20_000;
		}
	}
}
