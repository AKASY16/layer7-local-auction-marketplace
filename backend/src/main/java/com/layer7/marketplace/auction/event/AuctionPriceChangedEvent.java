package com.layer7.marketplace.auction.event;

import java.time.Instant;

/**
 * 입찰이 성립해 현재가·선두가 바뀌었다. 입찰 트랜잭션 안에서 만들고, 커밋된 뒤에만 실시간 소식으로 나간다.
 *
 * <p>커밋 뒤에는 DB를 다시 읽지 않도록 소식에 필요한 값을 모두 담는다. {@code version}은 이번 입찰까지 반영된 값이다.
 */
public record AuctionPriceChangedEvent(
	Long auctionId,
	long version,
	Instant occurredAt,
	long currentPrice,
	// 금액 상한에 도달해 더 입찰할 수 없으면 null
	Long nextBidAmount,
	long bidCount,
	Long leadingBidderId,
	String leadingBidderNickname
) {
}
