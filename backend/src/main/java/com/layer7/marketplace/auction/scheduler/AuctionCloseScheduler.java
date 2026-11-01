package com.layer7.marketplace.auction.scheduler;

import com.layer7.marketplace.auction.service.AuctionService;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 마감이 지난 경매를 종료하고 낙찰(또는 유찰)을 확정한다 (docs/backend/scheduler.md "경매 종료").
 *
 * <p>경매마다 {@link AuctionService#closeAuction}의 별도 트랜잭션으로 처리한다. 정합성은 락과 락 후 재판정이 지키므로,
 * 이 작업이 늦게 돌아도 결과가 틀리지 않고 "마감 후 확정까지 기다리는 시간"만 길어진다.
 */
@Slf4j
@Component
public class AuctionCloseScheduler {

	static final int BATCH_SIZE = 100;

	private final AuctionService auctionService;

	public AuctionCloseScheduler(AuctionService auctionService) {
		this.auctionService = auctionService;
	}

	// 이전 실행이 끝난 뒤 1초 쉬고 다시 돈다. 실행이 겹치지 않게 fixedRate가 아니라 fixedDelay를 쓴다
	@Scheduled(fixedDelay = 1000)
	public void closeEndedAuctions() {
		List<Long> auctionIds = auctionService.findAuctionIdsToClose(BATCH_SIZE);

		int closed = 0;
		for (Long auctionId : auctionIds) {
			// 한 경매의 실패(락 대기 초과 등)가 나머지 경매 처리를 막지 않도록 경매 단위로 기록하고 넘어간다
			try {
				if (auctionService.closeAuction(auctionId)) {
					closed++;
				}
			} catch (RuntimeException exception) {
				log.error("경매 종료 처리 실패: auctionId={}", auctionId, exception);
			}
		}

		if (closed > 0) {
			log.info("경매 {}건 종료", closed);
		}
	}
}
