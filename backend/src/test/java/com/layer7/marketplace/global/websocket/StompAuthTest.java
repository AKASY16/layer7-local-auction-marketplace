package com.layer7.marketplace.global.websocket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.StompTestClient;
import com.layer7.marketplace.support.TestFixtures;
import com.layer7.marketplace.user.domain.User;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;

/**
 * STOMP 연결의 인증과 구독 범위 (docs/api/realtime.md "연결", StompAuthChannelInterceptor).
 */
class StompAuthTest extends IntegrationTest {

	private static final Instant NOW = Instant.parse("2026-11-04T03:00:00Z");
	private static final String NOTIFICATIONS = "/user/queue/notifications";
	private static final long ERROR_SECONDS = 5;
	private static final long SILENCE_MILLIS = 500;

	@Autowired
	private JwtTokenProvider jwtTokenProvider;

	@Autowired
	private TestFixtures fixtures;

	@Autowired
	private SimpMessagingTemplate messagingTemplate;

	@BeforeEach
	void setUp() {
		clock.fixAt(NOW);
	}

	@Test
	@DisplayName("로그인한 연결은 본인 알림을 구독해 받고, 다른 사람의 알림은 받지 않는다")
	void authenticatedUserReceivesOwnNotifications() throws Exception {
		// given
		User owner = fixtures.user();
		User other = fixtures.user();
		try (StompTestClient ownerClient = StompTestClient.connect(port, token(owner));
			 StompTestClient otherClient = StompTestClient.connect(port, token(other))) {
			BlockingQueue<Map<String, Object>> ownerMessages =
				ownerClient.subscribe(NOTIFICATIONS, probe -> sendToUser(owner, probe));
			BlockingQueue<Map<String, Object>> otherMessages =
				otherClient.subscribe(NOTIFICATIONS, probe -> sendToUser(other, probe));

			// when
			sendToUser(owner, Map.of("type", "TEST", "message", "본인 알림"));

			// then
			Map<String, Object> received = ownerMessages.poll(ERROR_SECONDS, TimeUnit.SECONDS);
			assertThat(received).containsEntry("message", "본인 알림");
			assertThat(otherMessages.poll(SILENCE_MILLIS, TimeUnit.MILLISECONDS)).isNull();
		}
	}

	@Test
	@DisplayName("익명 연결은 본인 알림을 구독할 수 없다")
	void anonymousCannotSubscribeNotifications() throws Exception {
		try (StompTestClient client = StompTestClient.connect(port, null)) {
			// when
			client.subscribe(NOTIFICATIONS);

			// then
			assertThat(client.error().get(ERROR_SECONDS, TimeUnit.SECONDS)).isNotNull();
		}
	}

	@Test
	@DisplayName("잘못된 토큰으로는 연결할 수 없다")
	void invalidTokenRejected() {
		assertThatThrownBy(() -> StompTestClient.connect(port, "not-a-jwt"))
			.isInstanceOf(Exception.class);
	}

	@Test
	@DisplayName("연결한 뒤 토큰이 만료되면 본인 알림을 새로 구독할 수 없다")
	void expiredTokenCannotSubscribe() throws Exception {
		// given
		User user = fixtures.user();
		try (StompTestClient client = StompTestClient.connect(port, token(user))) {
			// 액세스 토큰 수명(30분)이 지난 시각
			clock.advance(Duration.ofMinutes(31));

			// when
			client.subscribe(NOTIFICATIONS);

			// then
			assertThat(client.error().get(ERROR_SECONDS, TimeUnit.SECONDS)).isNotNull();
		}
	}

	@Test
	@DisplayName("허용하지 않은 주소는 구독할 수 없다")
	void unknownDestinationRejected() throws Exception {
		try (StompTestClient client = StompTestClient.connect(port, null)) {
			// when
			client.subscribe("/topic/users");

			// then
			assertThat(client.error().get(ERROR_SECONDS, TimeUnit.SECONDS)).isNotNull();
		}
	}

	@Test
	@DisplayName("WebSocket으로 보낸 명령(SEND)은 거절한다")
	void sendRejected() throws Exception {
		try (StompTestClient client = StompTestClient.connect(port, null)) {
			// when
			client.send("/app/bids", "{}");

			// then
			assertThat(client.error().get(ERROR_SECONDS, TimeUnit.SECONDS)).isNotNull();
		}
	}

	private String token(User user) {
		return jwtTokenProvider.createAccessToken(user.getId()).getTokenValue();
	}

	private void sendToUser(User user, Map<String, Object> payload) {
		messagingTemplate.convertAndSendToUser(String.valueOf(user.getId()), "/queue/notifications", payload);
	}
}
