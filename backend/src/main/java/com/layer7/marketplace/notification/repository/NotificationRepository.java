package com.layer7.marketplace.notification.repository;

import com.layer7.marketplace.notification.domain.Notification;
import java.time.Instant;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NotificationRepository extends JpaRepository<Notification, Long> {

	Page<Notification> findByUserId(Long userId, Pageable pageable);

	Page<Notification> findByUserIdAndReadAtIsNull(Long userId, Pageable pageable);

	Optional<Notification> findByIdAndUserId(Long id, Long userId);

	// 읽지 않은 경우에만 읽은 시각을 넣는다. 엔티티를 읽어 값을 넣으면, 그 사이 전체 읽음이 커밋됐을 때 읽은 시각을 덮어쓴다.
	// 바로 다시 조회하므로, 이전에 읽어 둔 엔티티가 남지 않게 비운다
	@Modifying(clearAutomatically = true)
	@Query("""
		UPDATE Notification n SET n.readAt = :readAt
		WHERE n.id = :id AND n.userId = :userId AND n.readAt IS NULL
		""")
	int markRead(@Param("id") Long id, @Param("userId") Long userId, @Param("readAt") Instant readAt);

	@Modifying
	@Query("UPDATE Notification n SET n.readAt = :readAt WHERE n.userId = :userId AND n.readAt IS NULL")
	int markAllRead(@Param("userId") Long userId, @Param("readAt") Instant readAt);
}
