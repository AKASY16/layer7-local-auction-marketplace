package com.layer7.marketplace.notification.domain;

// docs/api/trade-notification.md "3. Notification"의 대표 type. 알림을 만드는 기능이 생길 때 필요한 type을 여기에 더한다
public enum NotificationType {
	OUTBID,
	AUTO_BID_EXHAUSTED,
	AUCTION_WON,
	AUCTION_SOLD,
	AUCTION_UNSOLD,
	TRADE_RESPONSE_REQUIRED,
	TRADE_DEADLINE_SOON,
	TRADE_PROCEEDED,
	TRADE_DECLINED,
	TRADE_NO_RESPONSE,
	TRADE_CANCELED,
	TRADE_EXPIRED,
	PRODUCT_APPEND_ADDED,
	COMPLETION_REQUESTED,
	COMPLETION_REJECTED,
	TRADE_COMPLETED,
	USER_RESTRICTED
}
