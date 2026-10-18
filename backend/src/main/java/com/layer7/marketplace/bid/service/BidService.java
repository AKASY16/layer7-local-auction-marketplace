package com.layer7.marketplace.bid.service;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.service.AuctionService;
import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.bid.domain.BidIncrementPolicy;
import com.layer7.marketplace.bid.dto.BidCreateResponse;
import com.layer7.marketplace.bid.repository.BidRepository;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.trust.service.TrustService;
import com.layer7.marketplace.user.domain.User;
import com.layer7.marketplace.user.service.UserService;
import java.time.Clock;
import java.time.Instant;
import java.util.OptionalLong;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class BidService {

	private final AuctionService auctionService;
	private final UserService userService;
	private final TrustService trustService;
	private final BidRepository bidRepository;
	private final BidIncrementPolicy bidIncrementPolicy;
	private final Clock clock;

	public BidService(
		AuctionService auctionService,
		UserService userService,
		TrustService trustService,
		BidRepository bidRepository,
		BidIncrementPolicy bidIncrementPolicy,
		Clock clock
	) {
		this.auctionService = auctionService;
		this.userService = userService;
		this.trustService = trustService;
		this.bidRepository = bidRepository;
		this.bidIncrementPolicy = bidIncrementPolicy;
		this.clock = clock;
	}

	// 락 순서는 Auction → 입찰자 User(FOR SHARE)다 (docs/backend/locking.md)
	@Transactional
	public BidCreateResponse placeManualBid(Long auctionId, Long bidderId, long amount) {
		Auction auction = auctionService.getAuctionForUpdate(auctionId);

		// 시각은 락을 잡은 뒤에 읽는다. 마감 직전 입찰과 종료 처리가 같은 기준으로 판정되게 하기 위함이다
		Instant now = Instant.now(clock);
		auction.openForBid(now);

		if (auction.isSeller(bidderId)) {
			throw new BusinessException(ErrorCode.SELF_BID_FORBIDDEN);
		}
		if (auction.isLeadingBidder(bidderId)) {
			throw new BusinessException(ErrorCode.ALREADY_LEADING);
		}

		User bidder = userService.getActiveUserForShare(bidderId);
		if (trustService.getActiveTradingRestriction(bidderId).isPresent()) {
			throw new BusinessException(ErrorCode.USER_RESTRICTED);
		}

		validateAmount(auction, amount);

		Bid bid = bidRepository.save(Bid.manual(auction, bidder, amount, now));
		auction.acceptBid(bid);
		// 응답의 version이 이번 변경까지 반영된 값이 되도록 먼저 DB에 반영한다
		bidRepository.flush();

		OptionalLong nextBidAmount = bidIncrementPolicy.nextValidAmount(auction.getCurrentPrice());
		long bidCount = bidRepository.countByAuctionId(auctionId);

		return BidCreateResponse.leading(
			bid,
			auction,
			nextBidAmount.isPresent() ? nextBidAmount.getAsLong() : null,
			bidCount,
			now
		);
	}

	// 상한 → 가격 단위 → 최소 금액 순서로 확인한다. 상한을 넘는 금액은 가격 단위 검사에서도 false라서 상한을 먼저 본다
	private void validateAmount(Auction auction, long amount) {
		if (bidIncrementPolicy.isAmountLimitExceeded(amount)) {
			throw new BusinessException(ErrorCode.AMOUNT_LIMIT_EXCEEDED);
		}
		if (!bidIncrementPolicy.isValidAmount(amount)) {
			throw new BusinessException(ErrorCode.INVALID_PRICE_UNIT);
		}

		long minimumAmount = auction.hasBid()
			? bidIncrementPolicy.nextValidAmount(auction.getCurrentPrice())
				.orElseThrow(() -> new BusinessException(
					ErrorCode.AMOUNT_LIMIT_EXCEEDED,
					"최고가에 도달해 더 이상 입찰할 수 없습니다."
				))
			: auction.getStartPrice();

		if (amount < minimumAmount) {
			throw new BusinessException(
				ErrorCode.BID_AMOUNT_TOO_LOW,
				"최소 입찰가는 %,d원입니다.".formatted(minimumAmount)
			);
		}
	}
}
