package com.layer7.marketplace.notification.dto;

import com.layer7.marketplace.notification.domain.Notification;
import com.layer7.marketplace.notification.domain.NotificationType;
import java.time.Instant;

// docs/api/trade-notification.md "GET /notifications"의 Item
public record NotificationResponse(
	Long id,
	NotificationType type,
	String message,
	Long productId,
	Long auctionId,
	Long tradeId,
	Instant readAt,
	Instant createdAt
) {

	public static NotificationResponse from(Notification notification) {
		return new NotificationResponse(
			notification.getId(),
			notification.getType(),
			notification.getMessage(),
			notification.getProductId(),
			notification.getAuctionId(),
			notification.getTradeId(),
			notification.getReadAt(),
			notification.getCreatedAt()
		);
	}
}
