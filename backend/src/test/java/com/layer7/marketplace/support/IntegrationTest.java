package com.layer7.marketplace.support;

import com.layer7.marketplace.TestcontainersConfiguration;
import org.junit.jupiter.api.AfterEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

/**
 * 통합 테스트의 공통 부모. 상속한 테스트는 모두 같은 Spring 컨텍스트를 함께 써서 MySQL 컨테이너도 한 번만 뜬다.
 *
 * <p>테스트 클래스에서 {@code @MockitoBean}, {@code @TestPropertySource} 등으로 설정을 바꾸면 그 클래스만 컨텍스트와
 * 컨테이너를 새로 띄우므로 꼭 필요할 때만 쓴다. 시각이 필요하면 {@link #clock}을 고정하고, 테스트가 끝나면 실제 시각으로 돌아간다.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({TestcontainersConfiguration.class, IntegrationTest.TestClockConfig.class})
public abstract class IntegrationTest {

	@Autowired
	protected TestClock clock;

	@AfterEach
	protected void resetClock() {
		clock.reset();
	}

	@TestConfiguration(proxyBeanMethods = false)
	static class TestClockConfig {

		// 운영 Clock 빈(ClockConfig) 대신 주입되도록 @Primary를 붙인다
		@Bean
		@Primary
		TestClock testClock() {
			return new TestClock();
		}
	}
}
