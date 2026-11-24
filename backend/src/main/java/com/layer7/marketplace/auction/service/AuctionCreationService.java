package com.layer7.marketplace.auction.service;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.dto.AuctionCreateRequest;
import com.layer7.marketplace.auction.dto.AuctionCreateResponse;
import com.layer7.marketplace.auction.repository.AuctionRepository;
import com.layer7.marketplace.bid.domain.BidIncrementPolicy;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductStatus;
import com.layer7.marketplace.product.service.ProductService;
import com.layer7.marketplace.trust.service.TrustService;
import com.layer7.marketplace.user.service.UserService;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuctionCreationService {

	private static final Duration MIN_DURATION = Duration.ofHours(1);
	private static final Duration MAX_DURATION = Duration.ofDays(7);
	private static final Duration MAX_START_DELAY = Duration.ofDays(7);
	private static final List<AuctionStatus> ACTIVE_STATUSES = List.of(AuctionStatus.READY, AuctionStatus.OPEN);

	private final AuctionRepository auctions;
	private final ProductService products;
	private final UserService users;
	private final TrustService trust;
	private final BidIncrementPolicy bidIncrementPolicy;
	private final Clock clock;

	public AuctionCreationService(AuctionRepository auctions, ProductService products, UserService users,
		TrustService trust, BidIncrementPolicy bidIncrementPolicy, Clock clock) {
		this.auctions = auctions;
		this.products = products;
		this.users = users;
		this.trust = trust;
		this.bidIncrementPolicy = bidIncrementPolicy;
		this.clock = clock;
	}

	@Transactional
	public AuctionCreateResponse createAuction(Long productId, Long sellerId, AuctionCreateRequest request) {
		// 같은 상품의 생성 요청은 상품 락 뒤에 중복을 검사하고 저장한다.
		Product product = products.getProductForUpdate(productId);
		if (!product.getSeller().getId().equals(sellerId)) {
			throw new BusinessException(ErrorCode.FORBIDDEN);
		}
		users.getActiveUserForShare(sellerId);
		if (trust.getActiveTradingRestriction(sellerId).isPresent()) {
			throw new BusinessException(ErrorCode.USER_RESTRICTED);
		}
		if (product.getStatus() != ProductStatus.ACTIVE) {
			throw new BusinessException(ErrorCode.PRODUCT_NOT_ACTIVE);
		}

		Instant now = Instant.now(clock);
		validatePeriod(request.startAt(), request.endAt(), now);
		validateStartPrice(request.startPrice());
		if (auctions.existsByProductIdAndStatusIn(productId, ACTIVE_STATUSES)) {
			throw new BusinessException(ErrorCode.ACTIVE_AUCTION_ALREADY_EXISTS);
		}

		Auction auction = request.startAt() == null
			? Auction.openImmediately(product, request.startPrice(), now, request.endAt())
			: Auction.create(product, request.startPrice(), request.startAt(), request.endAt());
		return AuctionCreateResponse.from(auctions.save(auction), now);
	}

	private static void validatePeriod(Instant startAt, Instant endAt, Instant now) {
		if (startAt != null && (!startAt.isAfter(now) || startAt.isAfter(now.plus(MAX_START_DELAY)))) {
			throw new BusinessException(ErrorCode.AUCTION_PERIOD_INVALID);
		}
		Duration duration = Duration.between(startAt == null ? now : startAt, endAt);
		if (duration.compareTo(MIN_DURATION) < 0 || duration.compareTo(MAX_DURATION) > 0) {
			throw new BusinessException(ErrorCode.AUCTION_PERIOD_INVALID);
		}
	}

	private void validateStartPrice(long amount) {
		if (bidIncrementPolicy.isAmountLimitExceeded(amount)) {
			throw new BusinessException(ErrorCode.AMOUNT_LIMIT_EXCEEDED);
		}
		if (!bidIncrementPolicy.isValidAmount(amount)) {
			throw new BusinessException(ErrorCode.INVALID_PRICE_UNIT);
		}
	}
}
