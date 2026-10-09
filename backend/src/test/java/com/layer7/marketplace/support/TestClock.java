package com.layer7.marketplace.support;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 통합 테스트용 시계. 평소에는 실제 시각을 따르고, {@link #fixAt}으로 고정하거나 {@link #advance}로 시간을 흘려보낼 수 있다.
 *
 * <p>동시성 테스트에서 여러 스레드가 함께 읽어도 같은 시각을 보도록 AtomicReference에 보관한다.
 */
public class TestClock extends Clock {

	private final AtomicReference<Instant> fixedInstant = new AtomicReference<>();

	public void fixAt(Instant instant) {
		fixedInstant.set(instant);
	}

	public void advance(Duration duration) {
		fixedInstant.updateAndGet(current -> {
			if (current == null) {
				throw new IllegalStateException("advance는 fixAt으로 시각을 고정한 뒤에 쓸 수 있습니다.");
			}
			return current.plus(duration);
		});
	}

	public void reset() {
		fixedInstant.set(null);
	}

	@Override
	public Instant instant() {
		Instant fixed = fixedInstant.get();
		return fixed != null ? fixed : Clock.systemUTC().instant();
	}

	@Override
	public ZoneId getZone() {
		return ZoneOffset.UTC;
	}

	@Override
	public Clock withZone(ZoneId zone) {
		throw new UnsupportedOperationException("서버 시각은 UTC로만 다룹니다.");
	}
}
