package com.layer7.marketplace.auction.domain;

import com.layer7.marketplace.bid.domain.Bid;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.time.BaseTimeEntity;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.region.domain.Region;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "auctions")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Auction extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "product_id", nullable = false)
	private Product product;

	// 탐색 API가 products 조인 없이 거르도록 생성 시 상품 값을 복사해 둔다 (docs/backend/erd.md)
	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "region_id", nullable = false)
	private Region region;

	@Enumerated(EnumType.STRING)
	@Column(name = "category", nullable = false, length = 50)
	private Category category;

	// 저장 상태. 입찰 판단과 API 응답은 statusAt(now)의 논리 상태를 쓴다
	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false, length = 20)
	private AuctionStatus status;

	@Column(name = "start_price", nullable = false)
	private long startPrice;

	@Column(name = "current_price", nullable = false)
	private long currentPrice;

	@OneToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "leading_bid_id", unique = true)
	private Bid leadingBid;

	@OneToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "winning_bid_id", unique = true)
	private Bid winningBid;

	@Column(name = "start_at", nullable = false)
	private Instant startAt;

	@Column(name = "end_at", nullable = false)
	private Instant endAt;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "relisted_from_auction_id")
	private Auction relistedFrom;

	// 동시성은 비관적 락이 맡고, version은 실시간 이벤트와 REST 응답의 순서 판단에 쓴다 (docs/api/realtime.md)
	@Version
	@Column(name = "version", nullable = false)
	private Long version;

	public static Auction create(Product product, long startPrice, Instant startAt, Instant endAt) {
		Auction auction = new Auction();
		auction.product = product;
		auction.region = product.getRegion();
		auction.category = product.getCategory();
		auction.status = AuctionStatus.READY;
		auction.startPrice = startPrice;
		auction.currentPrice = startPrice;
		auction.startAt = startAt;
		auction.endAt = endAt;
		return auction;
	}

	// 서버 시각 기준 논리 상태 (docs/backend/auction-state.md)
	public AuctionStatus statusAt(Instant now) {
		if (status == AuctionStatus.CANCELED || status == AuctionStatus.ENDED) {
			return status;
		}
		if (!now.isBefore(endAt)) {
			return AuctionStatus.ENDED;
		}
		if (now.isBefore(startAt)) {
			return AuctionStatus.READY;
		}
		return AuctionStatus.OPEN;
	}

	// 종료·취소가 저장 상태까지 반영됐는지. 논리 상태가 ENDED여도 false면 낙찰 확정 전이다 (docs/backend/auction-state.md)
	public boolean isFinalized() {
		return status == AuctionStatus.ENDED || status == AuctionStatus.CANCELED;
	}

	// 논리 상태가 OPEN이 아니면 입찰을 거절한다.
	// 시작 시각이 지난 READY는 따라붙는 부작용이 없으므로 그 자리에서 OPEN으로 바꾼다.
	public void openForBid(Instant now) {
		AuctionStatus logicalStatus = statusAt(now);

		if (logicalStatus == AuctionStatus.ENDED) {
			throw new BusinessException(ErrorCode.AUCTION_ENDED);
		}
		if (logicalStatus != AuctionStatus.OPEN) {
			throw new BusinessException(ErrorCode.AUCTION_NOT_OPEN);
		}
		if (status == AuctionStatus.READY) {
			status = AuctionStatus.OPEN;
		}
	}

	public boolean hasBid() {
		return leadingBid != null;
	}

	public boolean isSeller(Long userId) {
		return product.getSeller().getId().equals(userId);
	}

	public boolean isLeadingBidder(Long userId) {
		return leadingBid != null && leadingBid.getBidder().getId().equals(userId);
	}

	public void acceptBid(Bid bid) {
		this.currentPrice = bid.getAmount();
		this.leadingBid = bid;
	}
}
