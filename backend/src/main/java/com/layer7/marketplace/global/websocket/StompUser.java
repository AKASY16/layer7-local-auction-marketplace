package com.layer7.marketplace.global.websocket;

import java.security.Principal;

// 인증된 STOMP 연결의 사용자. 사용자 알림은 이 이름(회원 id)으로 보낸다: convertAndSendToUser(userId, "/queue/notifications", ...)
public record StompUser(Long userId) implements Principal {

	@Override
	public String getName() {
		return String.valueOf(userId);
	}
}
