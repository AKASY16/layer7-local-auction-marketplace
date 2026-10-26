package com.layer7.marketplace.auction.dto;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.product.domain.Category;
import com.layer7.marketplace.product.domain.Product;
import com.layer7.marketplace.product.domain.ProductCondition;
import com.layer7.marketplace.region.domain.Region;
import java.time.Instant;

// GET /api/v1/auctions의 목록 항목 (docs/api/auction-bidding.md)
public record AuctionSummaryResponse(
	Long auctionId,
	AuctionStatus status,
	boolean finalized,
	long currentPrice,
	Instant startAt,
	Instant endAt,
	ProductSummary product
) {

	public static AuctionSummaryResponse from(Auction auction, Instant now) {
		return new AuctionSummaryResponse(
			auction.getId(),
			auction.statusAt(now),
			auction.isFinalized(),
			auction.getCurrentPrice(),
			auction.getStartAt(),
			auction.getEndAt(),
			ProductSummary.from(auction)
		);
	}

	public record ProductSummary(
		Long id,
		String title,
		Category category,
		ProductCondition condition,
		// 상품 이미지 기능이 생기기 전까지 null
		String thumbnailUrl,
		RegionSummary region
	) {

		// 지역은 경매에 복사해 둔 값(상품 지역과 같다)을 써서 상품의 지역을 따로 읽지 않는다
		static ProductSummary from(Auction auction) {
			Product product = auction.getProduct();

			return new ProductSummary(
				product.getId(),
				product.getTitle(),
				product.getCategory(),
				product.getCondition(),
				null,
				RegionSummary.from(auction.getRegion())
			);
		}
	}

	public record RegionSummary(
		Long id,
		String sigunguName
	) {

		static RegionSummary from(Region region) {
			return new RegionSummary(region.getId(), region.getSigunguName());
		}
	}
}
