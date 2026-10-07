package com.layer7.marketplace.bid.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BidIncrementPolicyTest {

	private final BidIncrementPolicy policy =
		new BidIncrementPolicy();

	@Test
	void validAmountsAreAccepted() {
		assertTrue(policy.isValidAmount(100));
		assertTrue(policy.isValidAmount(9_900));
		assertTrue(policy.isValidAmount(10_500));
		assertTrue(policy.isValidAmount(51_000));
		assertTrue(policy.isValidAmount(105_000));
		assertTrue(policy.isValidAmount(510_000));
		assertTrue(policy.isValidAmount(1_020_000));
		assertTrue(policy.isValidAmount(10_000_000));
	}

	@Test
	void invalidAmountsAreRejected() {
		assertFalse(policy.isValidAmount(0));
		assertFalse(policy.isValidAmount(99));

		assertFalse(policy.isValidAmount(9_350));
		assertFalse(policy.isValidAmount(10_300));
		assertFalse(policy.isValidAmount(99_800));
		assertFalse(policy.isValidAmount(103_000));

		assertFalse(policy.isValidAmount(10_020_000));
	}

	@Test
	void nextAmountMatchesC01() {
		assertEquals(10_000L, policy.nextValidAmount(9_900));
		assertEquals(10_500L, policy.nextValidAmount(10_000));
		assertEquals(50_000L, policy.nextValidAmount(49_500));
		assertEquals(100_000L, policy.nextValidAmount(99_000));
		assertEquals(105_000L, policy.nextValidAmount(100_000));
	}

	@Test
	void maximumPriceHasNoNextAmount() {
		assertThrows(
			IllegalStateException.class,
			() -> policy.nextValidAmount(10_000_000)
		);
	}
}
