package com.layer7.marketplace.global.websocket;

import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.global.security.JwtTokenProvider.AccessToken;
import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.http.HttpHeaders;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageDeliveryException;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.stereotype.Component;

/**
 * STOMP 프레임의 인증과 구독 범위를 확인한다 (docs/api/realtime.md "연결").
 *
 * <ul>
 *   <li>CONNECT: {@code Authorization: Bearer} 헤더가 있으면 JWT를 검사해 사용자를 붙이고 만료 시각을 세션에 둔다.
 *   헤더가 없으면 익명 연결로 공개 경매 소식만 받는다. 잘못된 토큰은 연결을 거절한다.</li>
 *   <li>SUBSCRIBE: 공개 경매 소식과 본인 알림만 허용한다. 본인 알림은 인증된 연결이고 토큰이 만료되지 않았을 때만 허용한다.</li>
 *   <li>SEND: 명령은 REST로만 받으므로 거절한다.</li>
 * </ul>
 *
 * <p>여기서 예외를 던지면 Spring이 ERROR 프레임을 보내고 연결을 끊는다.
 */
@Component
public class StompAuthChannelInterceptor implements ChannelInterceptor {

	private static final String BEARER_PREFIX = "Bearer ";
	private static final String TOKEN_EXPIRES_AT = "tokenExpiresAt";
	private static final Pattern AUCTION_TOPIC = Pattern.compile("/topic/auctions/[1-9][0-9]*");
	private static final String NOTIFICATION_QUEUE = "/user/queue/notifications";

	private final JwtTokenProvider jwtTokenProvider;
	private final Clock clock;

	public StompAuthChannelInterceptor(JwtTokenProvider jwtTokenProvider, Clock clock) {
		this.jwtTokenProvider = jwtTokenProvider;
		this.clock = clock;
	}

	@Override
	public Message<?> preSend(Message<?> message, MessageChannel channel) {
		StompHeaderAccessor accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
		if (accessor == null || accessor.getCommand() == null) {
			return message;
		}

		switch (accessor.getCommand()) {
			case CONNECT -> authenticate(accessor);
			case SUBSCRIBE -> checkSubscription(accessor);
			case SEND -> throw new MessageDeliveryException("WebSocket으로는 명령을 받지 않습니다. REST API를 사용하세요.");
			default -> {
			}
		}
		return message;
	}

	private void authenticate(StompHeaderAccessor accessor) {
		String authorization = accessor.getFirstNativeHeader(HttpHeaders.AUTHORIZATION);
		if (authorization == null) {
			return;
		}
		if (!authorization.regionMatches(true, 0, BEARER_PREFIX, 0, BEARER_PREFIX.length())) {
			throw new MessageDeliveryException("Authorization 헤더는 Bearer 형식이어야 합니다.");
		}

		// 잘못된 토큰이면 BusinessException(INVALID_TOKEN)이 그대로 올라가 연결이 거절된다
		AccessToken token = jwtTokenProvider.parseAccessToken(authorization.substring(BEARER_PREFIX.length()).trim());
		accessor.setUser(new StompUser(token.userId()));
		sessionAttributes(accessor).put(TOKEN_EXPIRES_AT, token.expiresAt());
	}

	private void checkSubscription(StompHeaderAccessor accessor) {
		String destination = accessor.getDestination();
		if (destination != null && AUCTION_TOPIC.matcher(destination).matches()) {
			return;
		}
		if (NOTIFICATION_QUEUE.equals(destination)) {
			checkAuthenticated(accessor);
			return;
		}
		throw new MessageDeliveryException("구독할 수 없는 주소입니다: " + destination);
	}

	// 토큰을 갱신하면 클라이언트는 새 토큰으로 다시 연결한다. 만료된 연결의 새 구독은 받지 않는다
	private void checkAuthenticated(StompHeaderAccessor accessor) {
		Object expiresAt = sessionAttributes(accessor).get(TOKEN_EXPIRES_AT);
		if (!(accessor.getUser() instanceof StompUser) || !(expiresAt instanceof Instant tokenExpiresAt)) {
			throw new MessageDeliveryException("로그인한 연결만 구독할 수 있습니다.");
		}
		if (!Instant.now(clock).isBefore(tokenExpiresAt)) {
			throw new MessageDeliveryException("토큰이 만료되었습니다. 새 토큰으로 다시 연결하세요.");
		}
	}

	private static Map<String, Object> sessionAttributes(StompHeaderAccessor accessor) {
		Map<String, Object> attributes = accessor.getSessionAttributes();
		if (attributes == null) {
			throw new IllegalStateException("STOMP 세션 속성이 없습니다.");
		}
		return attributes;
	}
}
