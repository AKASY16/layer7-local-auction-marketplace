package com.layer7.marketplace.global.scheduling;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;

/**
 * {@code @Scheduled} 작업(경매 종료 등)을 켠다. 실행 규칙은 docs/backend/scheduler.md를 따른다.
 *
 * <p>통합 테스트는 {@code auction.scheduling.enabled=false}로 꺼서, 테스트가 만든 경매를 배경 작업이 먼저 처리하지 않게 한다.
 * 테스트는 Scheduler 메서드를 직접 부른다.
 */
@Configuration(proxyBeanMethods = false)
@EnableScheduling
@ConditionalOnProperty(name = "auction.scheduling.enabled", havingValue = "true", matchIfMissing = true)
public class SchedulingConfig {

	// WebSocket 설정이 STOMP heartbeat용 TaskScheduler(messageBrokerTaskScheduler)를 만들면 Spring Boot는 기본 Scheduler를 만들지 않고,
	// @Scheduled 작업이 그 스레드를 함께 쓰게 된다. 이름이 taskScheduler인 빈을 따로 두어 @Scheduled 작업은 이 스레드에서 돌게 한다
	@Bean
	public ThreadPoolTaskScheduler taskScheduler() {
		ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
		scheduler.setThreadNamePrefix("scheduling-");
		scheduler.setPoolSize(2);
		return scheduler;
	}
}
