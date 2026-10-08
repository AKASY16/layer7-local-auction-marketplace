package com.layer7.marketplace.global.time;

import org.springframework.data.jpa.repository.JpaRepository;

public interface AuditedSampleRepository extends JpaRepository<AuditedSample, Long> {
}
