package com.layer7.marketplace.bid.domain;

public class BidIncrementPolicy {

	private static final long MIN_AMOUNT = 100;
	private static final long MAX_AMOUNT = 10_000_000;

	// 허용 범위와 가격 단위에 맞으면 true
	public boolean isValidAmount(long amount) {
		if (amount < MIN_AMOUNT || amount > MAX_AMOUNT) {
			return false;
		}

		return amount % getUnit(amount) == 0;
	}

	// 유효한 현재가보다 큰 가장 가까운 유효 금액
	public long nextValidAmount(long currentPrice) {
		if (!isValidAmount(currentPrice)) {
			throw new IllegalArgumentException(
				"현재가는 유효한 금액이어야 합니다."
			);
		}

		long nextAmount = currentPrice + getUnit(currentPrice);

		if (nextAmount > MAX_AMOUNT) {
			throw new IllegalStateException(
				"금액 상한에 도달해 다음 입찰가가 없습니다."
			);
		}

		return nextAmount;
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
