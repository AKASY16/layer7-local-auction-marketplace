package com.layer7.marketplace.bid.domain;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.user.domain.User;
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
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

// 성립한 Bid는 수정·삭제하지 않으므로 생성 시각만 기록한다 (BaseTimeEntity는 수정 시각까지 있어 쓰지 않음)
@Entity
@Table(name = "bids")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Bid {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "auction_id", nullable = false)
	private Auction auction;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "bidder_id", nullable = false)
	private User bidder;

	@Column(name = "amount", nullable = false)
	private long amount;

	@Enumerated(EnumType.STRING)
	@Column(name = "type", nullable = false, length = 20)
	private BidType type;

	// AutoBid 엔티티는 자동입찰 작업에서 만든다. 그때 연관관계로 바꾼다
	@Column(name = "auto_bid_id")
	private Long autoBidId;

	// 입찰을 받아들인 판정 시각(경매 락을 잡은 뒤 읽은 시각)을 그대로 쓴다.
	// 저장할 때 시계를 다시 읽으면 마감 직전에 받아들인 입찰이 마감 이후에 생성된 것처럼 기록될 수 있다
	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	public static Bid manual(Auction auction, User bidder, long amount, Instant acceptedAt) {
		Bid bid = new Bid();
		bid.auction = auction;
		bid.bidder = bidder;
		bid.amount = amount;
		bid.type = BidType.MANUAL;
		bid.createdAt = acceptedAt;
		return bid;
	}
}
