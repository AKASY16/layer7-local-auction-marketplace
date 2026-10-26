package com.layer7.marketplace.auction.repository;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.product.domain.Category;
import jakarta.persistence.criteria.Path;
import jakarta.persistence.criteria.Predicate;
import java.time.Instant;
import org.springframework.data.jpa.domain.Specification;

// GET /api/v1/auctions의 검색 조건 (docs/api/auction-bidding.md)
public final class AuctionSpecifications {

	// 백슬래시는 MySQL 문자열에서도 이스케이프로 쓰여 헷갈리므로 LIKE 이스케이프 문자는 !를 쓴다
	private static final char LIKE_ESCAPE = '!';

	private AuctionSpecifications() {
	}

	// 지역·카테고리는 경매에 복사해 둔 값으로 거른다 (docs/backend/erd.md)
	public static Specification<Auction> inRegion(Long regionId) {
		return (root, query, cb) -> cb.equal(root.get("region").get("id"), regionId);
	}

	public static Specification<Auction> inCategory(Category category) {
		return (root, query, cb) -> cb.equal(root.get("category"), category);
	}

	// 상품 제목 부분 검색. 검색어의 %와 _는 와일드카드가 아니라 글자 그대로 찾는다
	public static Specification<Auction> titleContains(String keyword) {
		String pattern = "%" + escapeLike(keyword) + "%";
		return (root, query, cb) -> cb.like(root.join("product").get("title"), pattern, LIKE_ESCAPE);
	}

	// 서버 시각 기준 논리 상태. 저장 상태는 Scheduler가 뒤늦게 맞추므로 시각 조건을 함께 본다 (docs/backend/auction-state.md)
	public static Specification<Auction> logicalStatus(AuctionStatus status, Instant now) {
		return (root, query, cb) -> {
			Path<AuctionStatus> stored = root.get("status");
			Path<Instant> startAt = root.get("startAt");
			Path<Instant> endAt = root.get("endAt");
			Predicate notFinalized = stored.in(AuctionStatus.READY, AuctionStatus.OPEN);

			return switch (status) {
				case READY -> cb.and(cb.equal(stored, AuctionStatus.READY), cb.greaterThan(startAt, now));
				case OPEN -> cb.and(notFinalized, cb.lessThanOrEqualTo(startAt, now), cb.greaterThan(endAt, now));
				case ENDED -> cb.or(
					cb.equal(stored, AuctionStatus.ENDED),
					cb.and(notFinalized, cb.lessThanOrEqualTo(endAt, now))
				);
				case CANCELED -> throw new IllegalArgumentException("CANCELED는 검색할 수 있는 논리 상태가 아닙니다.");
			};
		};
	}

	private static String escapeLike(String keyword) {
		return keyword
			.replace("!", "!!")
			.replace("%", "!%")
			.replace("_", "!_");
	}
}
