package com.layer7.marketplace.global.scheduling;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

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
}
