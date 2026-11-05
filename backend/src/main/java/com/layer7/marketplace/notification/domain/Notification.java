package com.layer7.marketplace.notification.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * 앱 내부 알림. 조회용 엔티티다.
 *
 * <p>저장은 중복 방지 때문에 {@code NotificationInsertRepository}가 JDBC로 하고, 읽음 처리는 조건부 UPDATE로 한다.
 * 그래서 이 엔티티에는 값을 바꾸는 메서드가 없다.
 *
 * <p>응답에 id만 나가므로 회원·상품·경매·거래는 연관관계 없이 id로 둔다. 거래(Trade) 엔티티는 아직 없다.
 */
@Entity
@Table(name = "notifications")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Notification {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "user_id", nullable = false, updatable = false)
	private Long userId;

	@Enumerated(EnumType.STRING)
	@Column(name = "type", nullable = false, length = 50, updatable = false)
	private NotificationType type;

	@Column(name = "message", nullable = false, length = 500, updatable = false)
	private String message;

	@Column(name = "product_id", updatable = false)
	private Long productId;

	@Column(name = "auction_id", updatable = false)
	private Long auctionId;

	@Column(name = "trade_id", updatable = false)
	private Long tradeId;

	@Column(name = "read_at")
	private Instant readAt;

	@Column(name = "dedupe_key", nullable = false, length = 200, updatable = false)
	private String dedupeKey;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;
}
