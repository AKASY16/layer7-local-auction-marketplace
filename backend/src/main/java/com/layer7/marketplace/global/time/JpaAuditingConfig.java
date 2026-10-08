package com.layer7.marketplace.global.time;

import java.time.Clock;
import java.time.Instant;
import java.util.Optional;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.auditing.DateTimeProvider;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

/**
 * {@link BaseTimeEntity}의 생성·수정 시각을 Clock 기준으로 기록한다.
 *
 * <p>Spring Data의 기본 시각은 Clock을 거치지 않는 서버 시간대의 현재 시각이라, 테스트에서 Clock을 고정해도 따라오지 않는다.
 */
@Configuration(proxyBeanMethods = false)
@EnableJpaAuditing(dateTimeProviderRef = "auditingDateTimeProvider")
public class JpaAuditingConfig {

	@Bean
	public DateTimeProvider auditingDateTimeProvider(Clock clock) {
		return () -> Optional.of(Instant.now(clock));
	}
}
