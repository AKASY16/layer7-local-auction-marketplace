package com.layer7.marketplace.support;

import java.lang.reflect.Type;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import org.springframework.messaging.MessageDeliveryException;
import org.springframework.messaging.converter.CompositeMessageConverter;
import org.springframework.messaging.converter.JacksonJsonMessageConverter;
import org.springframework.messaging.converter.StringMessageConverter;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

/**
 * 통합 테스트에서 실제 STOMP 연결을 맺는 클라이언트 (docs/api/realtime.md).
 *
 * <p>구독한 메시지는 큐에 쌓고, 서버가 ERROR 프레임을 보내거나 연결이 끊기면 {@link #error()}가 완료된다.
 */
public class StompTestClient implements AutoCloseable {

	private static final long TIMEOUT_SECONDS = 5;
	private static final String PROBE = "PROBE";

	private final WebSocketStompClient client;
	private final StompSession session;
	private final CompletableFuture<String> error;

	private StompTestClient(WebSocketStompClient client, StompSession session, CompletableFuture<String> error) {
		this.client = client;
		this.session = session;
		this.error = error;
	}

	// accessToken이 null이면 익명 연결이다. 서버가 연결을 거절하면 예외가 난다
	public static StompTestClient connect(int port, String accessToken) throws Exception {
		WebSocketStompClient client = new WebSocketStompClient(new StandardWebSocketClient());
		client.setMessageConverter(new CompositeMessageConverter(
			List.of(new StringMessageConverter(), new JacksonJsonMessageConverter())));

		StompHeaders connectHeaders = new StompHeaders();
		if (accessToken != null) {
			connectHeaders.add("Authorization", "Bearer " + accessToken);
		}

		CompletableFuture<String> error = new CompletableFuture<>();
		try {
			StompSession session = client.connectAsync(
				"ws://localhost:" + port + "/ws",
				new WebSocketHttpHeaders(),
				connectHeaders,
				new ErrorRecordingHandler(error)
			).get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			return new StompTestClient(client, session, error);
		} catch (Exception exception) {
			client.stop();
			throw exception;
		}
	}

	// 구독만 보낸다. 서버가 구독을 거절하는지 볼 때 쓴다
	public BlockingQueue<Map<String, Object>> subscribe(String destination) {
		BlockingQueue<Map<String, Object>> messages = new LinkedBlockingQueue<>();
		session.subscribe(destination, frameHandler(messages, new CountDownLatch(1)));
		return messages;
	}

	/**
	 * 구독하고, 서버에 등록될 때까지 기다린다. SUBSCRIBE는 비동기라 바로 이벤트를 만들면 놓칠 수 있다.
	 *
	 * <p>{@code sendProbe}로 시험 메시지를 받을 때까지 되풀이해 보낸다. 시험 메시지는 큐에 넣지 않으므로,
	 * 늦게 도착한 시험 메시지가 테스트가 기다리는 소식으로 잡히지 않는다.
	 */
	public BlockingQueue<Map<String, Object>> subscribe(String destination, Consumer<Map<String, Object>> sendProbe)
		throws InterruptedException {
		BlockingQueue<Map<String, Object>> messages = new LinkedBlockingQueue<>();
		CountDownLatch subscribed = new CountDownLatch(1);
		session.subscribe(destination, frameHandler(messages, subscribed));

		long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(TIMEOUT_SECONDS);
		do {
			if (System.nanoTime() > deadline) {
				throw new AssertionError("구독이 등록되지 않았습니다: " + destination);
			}
			sendProbe.accept(Map.of("type", PROBE));
		} while (!subscribed.await(100, TimeUnit.MILLISECONDS));
		return messages;
	}

	private static StompFrameHandler frameHandler(BlockingQueue<Map<String, Object>> messages, CountDownLatch subscribed) {
		return new StompFrameHandler() {

			@Override
			public Type getPayloadType(StompHeaders headers) {
				return Map.class;
			}

			@Override
			@SuppressWarnings("unchecked")
			public void handleFrame(StompHeaders headers, Object payload) {
				Map<String, Object> message = (Map<String, Object>) payload;
				if (PROBE.equals(message.get("type"))) {
					subscribed.countDown();
					return;
				}
				messages.add(message);
			}
		};
	}

	public void send(String destination, String payload) {
		session.send(destination, payload);
	}

	// 서버의 ERROR 프레임 message 헤더 또는 연결이 끊긴 이유
	public CompletableFuture<String> error() {
		return error;
	}

	// 서버가 ERROR로 연결을 끊은 직후에는 isConnected()가 아직 true여도 보내기가 실패할 수 있어 무시한다
	@Override
	public void close() {
		try {
			if (session.isConnected()) {
				session.disconnect();
			}
		} catch (MessageDeliveryException ignored) {
			// 이미 끊긴 연결
		} finally {
			client.stop();
		}
	}

	private static final class ErrorRecordingHandler extends StompSessionHandlerAdapter {

		private final CompletableFuture<String> error;

		private ErrorRecordingHandler(CompletableFuture<String> error) {
			this.error = error;
		}

		@Override
		public Type getPayloadType(StompHeaders headers) {
			return String.class;
		}

		// 세션 핸들러로 오는 프레임은 ERROR뿐이다
		@Override
		public void handleFrame(StompHeaders headers, Object payload) {
			error.complete(StompCommand.ERROR + ": " + headers.getFirst("message"));
		}

		@Override
		public void handleTransportError(StompSession session, Throwable exception) {
			error.complete("transport: " + exception);
		}
	}
}
