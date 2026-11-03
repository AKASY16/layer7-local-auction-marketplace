package com.layer7.marketplace.auction.scheduler;

import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.layer7.marketplace.auction.service.AuctionService;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.dao.PessimisticLockingFailureException;

class AuctionCloseSchedulerTest {

	@Test
	@DisplayName("한 경매의 종료가 실패해도 나머지 경매는 계속 처리한다")
	void continueAfterFailure() {
		// given
		AuctionService auctionService = mock(AuctionService.class);
		given(auctionService.findAuctionIdsToClose(AuctionCloseScheduler.BATCH_SIZE)).willReturn(List.of(1L, 2L, 3L));
		given(auctionService.closeAuction(2L)).willThrow(new PessimisticLockingFailureException("lock wait timeout"));
		AuctionCloseScheduler scheduler = new AuctionCloseScheduler(auctionService);

		// when
		scheduler.closeEndedAuctions();

		// then
		verify(auctionService).closeAuction(1L);
		verify(auctionService).closeAuction(2L);
		verify(auctionService).closeAuction(3L);
	}
}
