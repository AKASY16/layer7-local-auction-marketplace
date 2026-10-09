package com.layer7.marketplace.global.time;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.support.IntegrationTest;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

class BaseTimeEntityTest extends IntegrationTest {

	@Autowired
	private AuditedSampleRepository repository;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("저장하면 생성·수정 시각이 고정한 Clock의 시각으로 기록된다")
	void recordsTimesFromClock() {
		// given
		Instant now = Instant.parse("2026-10-09T03:00:00Z");
		clock.fixAt(now);

		// when
		Long id = repository.saveAndFlush(AuditedSample.create("처음")).getId();

		// then
		AuditedSample found = repository.findById(id).orElseThrow();
		assertThat(found.getCreatedAt()).isEqualTo(now);
		assertThat(found.getUpdatedAt()).isEqualTo(now);
	}

	@Test
	@DisplayName("수정하면 수정 시각만 바뀌고 생성 시각은 그대로다")
	void updatesOnlyUpdatedAt() {
		// given
		Instant createdAt = Instant.parse("2026-10-09T03:00:00Z");
		clock.fixAt(createdAt);
		AuditedSample sample = repository.saveAndFlush(AuditedSample.create("처음"));

		// when
		clock.advance(Duration.ofMinutes(10));
		sample.rename("수정");
		repository.saveAndFlush(sample);

		// then
		AuditedSample found = repository.findById(sample.getId()).orElseThrow();
		assertThat(found.getCreatedAt()).isEqualTo(createdAt);
		assertThat(found.getUpdatedAt()).isEqualTo(createdAt.plus(Duration.ofMinutes(10)));
	}

	@Test
	@DisplayName("DB에는 서버 시간대와 관계없이 UTC 시각으로 저장된다")
	void storesUtcInDatabase() {
		// given
		clock.fixAt(Instant.parse("2026-10-09T03:00:00Z"));

		// when
		Long id = repository.saveAndFlush(AuditedSample.create("UTC")).getId();

		// then
		String stored = jdbcTemplate.queryForObject(
				"SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') FROM test_audited_samples WHERE id = ?",
				String.class, id);
		assertThat(stored).isEqualTo("2026-10-09 03:00:00");
	}
}
