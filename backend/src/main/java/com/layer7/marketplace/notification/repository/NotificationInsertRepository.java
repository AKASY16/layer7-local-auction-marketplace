package com.layer7.marketplace.notification.repository;

import com.layer7.marketplace.notification.dto.NewNotification;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * 알림을 중복 없이 저장한다. 같은 {@code dedupe_key}가 이미 있으면 DB의 고유 키({@code uq_notifications_dedupe_key})가 막는다.
 *
 * <p>JPA 대신 JDBC로 넣는 이유: JPA는 저장 중 오류가 나면 바깥 트랜잭션 전체를 롤백하게 표시한다.
 * 그러면 입찰 같은 작업 안에서 알림이 중복이기만 해도 그 작업까지 실패한다. JDBC 오류는 그런 표시를 남기지 않고,
 * MySQL은 중복 오류가 난 문장만 되돌리므로 호출한 쪽 트랜잭션은 그대로 이어진다.
 * 같은 이유로 이 클래스에는 {@code @Transactional}을 붙이지 않는다. 붙이면 예외가 그 경계를 지나며 같은 표시가 남는다.
 *
 * <p>{@code INSERT IGNORE}는 잘못된 id(FK) 오류까지 경고로 낮춰 버그를 숨기고,
 * {@code ON DUPLICATE KEY UPDATE}는 지금 드라이버 설정에서 새로 넣은 경우와 중복을 같은 결과 수로 돌려줘서 쓰지 않는다.
 */
@Repository
public class NotificationInsertRepository {

	private final JdbcTemplate jdbcTemplate;

	public NotificationInsertRepository(JdbcTemplate jdbcTemplate) {
		this.jdbcTemplate = jdbcTemplate;
	}

	/**
	 * 새로 넣었으면 true, 같은 키가 이미 있으면 false. 중복이 아닌 오류(잘못된 id 등)는 그대로 던진다.
	 *
	 * <p>다른 트랜잭션이 같은 키를 넣고 아직 커밋하지 않았으면, 그 트랜잭션이 끝날 때까지 기다린다.
	 * 커밋하면 false, 롤백하면 이쪽이 새로 넣어 true다. 기다림이 락 대기 제한(3초)을 넘으면 락 오류로 실패한다.
	 */
	public boolean insertIfAbsent(NewNotification notification, Instant createdAt) {
		try {
			jdbcTemplate.update(
				"""
				INSERT INTO notifications (user_id, type, message, product_id, auction_id, trade_id, dedupe_key, created_at)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?)
				""",
				notification.userId(),
				notification.type().name(),
				notification.message(),
				notification.productId(),
				notification.auctionId(),
				notification.tradeId(),
				notification.dedupeKey(),
				// DATETIME 컬럼에는 UTC 시각을 그대로 넣는다 (서버 시간대와 무관하게)
				LocalDateTime.ofInstant(createdAt, ZoneOffset.UTC)
			);
			return true;
		} catch (DuplicateKeyException e) {
			return false;
		}
	}
}
