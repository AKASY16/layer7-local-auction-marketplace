package com.layer7.marketplace.global.time;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

// BaseTimeEntityTest 전용 엔티티 (테이블: src/test/resources/db/migration)
@Entity
@Table(name = "test_audited_samples")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class AuditedSample extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "name", nullable = false, length = 50)
	private String name;

	public static AuditedSample create(String name) {
		AuditedSample sample = new AuditedSample();
		sample.name = name;
		return sample;
	}

	public void rename(String name) {
		this.name = name;
	}
}
