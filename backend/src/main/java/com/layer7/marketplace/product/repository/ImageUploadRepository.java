package com.layer7.marketplace.product.repository;

import com.layer7.marketplace.product.domain.ImageUpload;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ImageUploadRepository extends JpaRepository<ImageUpload, Long> {

	List<ImageUpload> findByObjectKeyIn(Collection<String> objectKeys);

	@Modifying
	@Query("""
		UPDATE ImageUpload u SET u.status = com.layer7.marketplace.product.domain.ImageUploadStatus.ATTACHED,
			u.updatedAt = :now
		WHERE u.objectKey = :key AND u.user.id = :userId
			AND u.status = com.layer7.marketplace.product.domain.ImageUploadStatus.PENDING
			AND u.createdAt > :cutoff AND u.createdAt <= :now
		""")
	int attachPending(@Param("key") String key, @Param("userId") Long userId,
		@Param("cutoff") Instant cutoff, @Param("now") Instant now);
}
