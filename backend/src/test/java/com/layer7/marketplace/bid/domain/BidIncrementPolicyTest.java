package com.layer7.marketplace.bid.domain;

import java.util.OptionalLong;

import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("입찰 가격 단위 정책")
class BidIncrementPolicyTest {

	@ParameterizedTest
	@ValueSource(longs = {
		100, 9_900, 10_000, 10_500, 49_500, 50_000, 51_000,
		99_000, 100_000, 105_000, 495_000, 500_000, 510_000,
		990_000, 1_000_000, 1_020_000, 9_980_000, 10_000_000
	})
	@DisplayName("허용 범위 안에서 가격 단위에 맞는 금액은 유효하다")
	void acceptsValidAmounts(long amount) {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();

		// when
		boolean valid = policy.isValidAmount(amount);

		// then
		assertThat(valid).isTrue();
	}

	@ParameterizedTest
	@ValueSource(longs = {
		-100, 0, 99, 9_350, 10_300, 99_800, 103_000,
		503_000, 1_010_000, 10_000_001, 10_020_000
	})
	@DisplayName("허용 범위를 벗어나거나 가격 단위에 맞지 않는 금액은 유효하지 않다")
	void rejectsInvalidAmounts(long amount) {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();

		// when
		boolean valid = policy.isValidAmount(amount);

		// then
		assertThat(valid).isFalse();
	}

	@ParameterizedTest
	@CsvSource({
		"10300, false",
		"9999999, false",
		"10000000, false",
		"10000001, true",
		"10020000, true"
	})
	@DisplayName("가격 단위와 관계없이 천만 원 초과 여부를 구분한다")
	void detectsAmountLimit(long amount, boolean expected) {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();

		// when
		boolean exceeded = policy.isAmountLimitExceeded(amount);

		// then
		assertThat(exceeded).isEqualTo(expected);
	}

	@ParameterizedTest
	@CsvSource({
		"100, 200",
		"9900, 10000",
		"10000, 10500",
		"49500, 50000",
		"99000, 100000",
		"100000, 105000",
		"495000, 500000",
		"500000, 510000",
		"990000, 1000000",
		"1000000, 1020000",
		"9980000, 10000000"
	})
	@DisplayName("가격 구간 경계에서도 현재가보다 큰 가장 가까운 유효 금액을 계산한다")
	void calculatesNextAmount(long currentPrice, long expected) {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();

		// when
		OptionalLong nextAmount = policy.nextValidAmount(currentPrice);

		// then
		assertThat(nextAmount).hasValue(expected);
	}

	@ParameterizedTest
	@ValueSource(longs = {0, 9_350, 10_300, 10_020_000})
	@DisplayName("유효하지 않은 현재가로 다음 입찰가를 계산하면 예외가 발생한다")
	void rejectsInvalidCurrentPrice(long currentPrice) {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();

		// when
		ThrowingCallable action = () -> policy.nextValidAmount(currentPrice);

		// then
		assertThatThrownBy(action).isInstanceOf(IllegalArgumentException.class);
	}

	@Test
	@DisplayName("현재가가 천만 원이면 다음 입찰가가 없어 빈 값을 반환한다")
	void maximumPriceHasNoNextAmount() {
		// given
		BidIncrementPolicy policy = new BidIncrementPolicy();
		long currentPrice = 10_000_000;

		// when
		OptionalLong nextAmount = policy.nextValidAmount(currentPrice);

		// then
		assertThat(nextAmount).isEmpty();
	}
}
