package com.layer7.marketplace.auction.event;

import java.time.Instant;

/**
 * 종료 처리가 경매를 ENDED로 저장하고 낙찰(또는 유찰)을 확정했다. 종료 트랜잭션이 커밋된 뒤에만 실시간 소식으로 나간다.
 *
 * <p>{@code version}은 이번 종료까지 반영된 값이다. 유찰이면 {@code winningBidId}가 null이다.
 */
public record AuctionClosedEvent(
	Long auctionId,
	long version,
	Instant occurredAt,
	Long winningBidId,
	Instant endAt
) {
}
