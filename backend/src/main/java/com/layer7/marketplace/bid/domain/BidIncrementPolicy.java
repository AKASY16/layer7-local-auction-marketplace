package com.layer7.marketplace.bid.domain;

import java.util.List;
import java.util.OptionalLong;

import org.springframework.stereotype.Component;

@Component
public class BidIncrementPolicy {

	private static final long MIN_AMOUNT = 100;
	private static final long MAX_AMOUNT = 10_000_000;

	// 가격 구간별 입찰 단위 (docs/03-auction-policy.md). 검증과 GET /bid-increment-policy 응답이 이 표 하나를 쓴다
	private static final List<Band> BANDS = List.of(
		new Band(100, 9_999, 100),
		new Band(10_000, 49_999, 500),
		new Band(50_000, 99_999, 1_000),
		new Band(100_000, 499_999, 5_000),
		new Band(500_000, 999_999, 10_000),
		new Band(1_000_000, MAX_AMOUNT, 20_000)
	);

	// from 이상 to 이하 금액은 unit 단위로 입찰한다
	public record Band(long from, long to, long unit) {
	}

	public long minAmount() {
		return MIN_AMOUNT;
	}

	public long maxAmount() {
		return MAX_AMOUNT;
	}

	public List<Band> bands() {
		return BANDS;
	}

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

	// 가격 구간에 따른 단위. 허용 범위 안의 금액으로만 부른다
	private long getUnit(long amount) {
		return BANDS.stream()
			.filter(band -> amount <= band.to())
			.findFirst()
			.orElseThrow()
			.unit();
	}
}
