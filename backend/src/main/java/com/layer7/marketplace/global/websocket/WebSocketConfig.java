package com.layer7.marketplace.global.websocket;

import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * STOMP over WebSocket 설정 (docs/api/realtime.md).
 *
 * <p>서버가 화면으로 소식을 보내는 용도로만 쓴다. 공개 경매 소식은 {@code /topic/auctions/{auctionId}},
 * 사용자 알림은 {@code /user/queue/notifications}이다. 입찰 같은 명령은 REST로만 받는다.
 * MVP는 단일 서버의 내장 Simple Broker를 쓴다.
 */
@Configuration(proxyBeanMethods = false)
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

	private final StompAuthChannelInterceptor stompAuthChannelInterceptor;
	private final List<String> allowedOrigins;

	public WebSocketConfig(
		StompAuthChannelInterceptor stompAuthChannelInterceptor,
		@Value("${auction.websocket.allowed-origins}") List<String> allowedOrigins
	) {
		this.stompAuthChannelInterceptor = stompAuthChannelInterceptor;
		this.allowedOrigins = allowedOrigins;
	}

	// 기본값은 같은 출처만 허용이라, 개발 서버(Vite)가 넘겨준 요청의 Origin(5173)은 거절된다. 허용할 화면 주소를 설정으로 받는다
	@Override
	public void registerStompEndpoints(StompEndpointRegistry registry) {
		registry.addEndpoint("/ws")
			.setAllowedOriginPatterns(allowedOrigins.toArray(String[]::new));
	}

	@Override
	public void configureMessageBroker(MessageBrokerRegistry registry) {
		registry.enableSimpleBroker("/topic", "/queue");
		registry.setUserDestinationPrefix("/user");
	}

	// 클라이언트가 보낸 프레임(CONNECT·SUBSCRIBE·SEND)은 모두 이 인터셉터를 거친다
	@Override
	public void configureClientInboundChannel(ChannelRegistration registration) {
		registration.interceptors(stompAuthChannelInterceptor);
	}

	// 커밋 뒤 실시간 소식을 보내는 스레드. 입찰·종료 요청 스레드가 발송을 기다리지 않게 한다 (docs/api/realtime.md "발송 방식")
	@Bean
	public ThreadPoolTaskExecutor realtimeEventExecutor() {
		ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
		executor.setThreadNamePrefix("realtime-");
		executor.setCorePoolSize(2);
		executor.setMaxPoolSize(2);
		executor.setQueueCapacity(10_000);
		return executor;
	}
}
