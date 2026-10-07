package com.layer7.marketplace.global.time;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 현재 시각은 이 Clock으로만 구한다: {@code Instant.now(clock)}. 테스트에서는 고정된 Clock으로 바꿔 끼운다.
 */
@Configuration(proxyBeanMethods = false)
public class ClockConfig {

	@Bean
	public Clock clock() {
		return Clock.systemUTC();
	}
}
