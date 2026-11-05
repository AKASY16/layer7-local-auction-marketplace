package com.layer7.marketplace.auction.event;

import com.layer7.marketplace.auction.dto.AuctionEventMessage;
import java.util.concurrent.Executor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * 경매 이벤트를 커밋 뒤에 {@code /topic/auctions/{auctionId}} 구독자에게 보낸다 (docs/api/realtime.md "전달 원칙", "발송 방식").
 *
 * <p>{@code @TransactionalEventListener}의 기본 시점이 AFTER_COMMIT이라 롤백된 트랜잭션의 이벤트는 나가지 않는다.
 * 이 리스너는 요청 스레드에서 돌기 때문에 발송은 별도 executor에 넘기기만 한다. 소식은 유실될 수 있고,
 * 화면은 다시 연결할 때 REST로 상태를 맞춘다.
 */
@Slf4j
@Component
public class AuctionEventBroadcaster {

	private final SimpMessagingTemplate messagingTemplate;
	private final Executor realtimeEventExecutor;

	public AuctionEventBroadcaster(
		SimpMessagingTemplate messagingTemplate,
		@Qualifier("realtimeEventExecutor") Executor realtimeEventExecutor
	) {
		this.messagingTemplate = messagingTemplate;
		this.realtimeEventExecutor = realtimeEventExecutor;
	}

	@TransactionalEventListener
	public void onPriceChanged(AuctionPriceChangedEvent event) {
		send(event.auctionId(), AuctionEventMessage.from(event));
	}

	@TransactionalEventListener
	public void onClosed(AuctionClosedEvent event) {
		send(event.auctionId(), AuctionEventMessage.from(event));
	}

	// 이미 커밋된 뒤라 여기서 예외가 나가면 성공한 요청이 실패 응답을 받는다. 발송 실패는 기록만 한다
	private void send(Long auctionId, AuctionEventMessage message) {
		try {
			realtimeEventExecutor.execute(() -> {
				try {
					messagingTemplate.convertAndSend("/topic/auctions/" + auctionId, message);
				} catch (RuntimeException exception) {
					log.warn("경매 실시간 소식 발송 실패: auctionId={}, type={}", auctionId, message.type(), exception);
				}
			});
		} catch (RuntimeException exception) {
			log.warn("경매 실시간 소식 발송 작업을 넘기지 못함: auctionId={}, type={}", auctionId, message.type(), exception);
		}
	}
}
