package com.layer7.marketplace.auction.service;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import com.layer7.marketplace.auction.dto.AuctionPageResponse;
import com.layer7.marketplace.auction.dto.AuctionSearchCondition;
import com.layer7.marketplace.auction.dto.AuctionSummaryResponse;
import com.layer7.marketplace.auction.event.AuctionClosedEvent;
import com.layer7.marketplace.auction.repository.AuctionRepository;
import com.layer7.marketplace.auction.repository.AuctionSpecifications;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.product.repository.ProductImageRepository;
import com.layer7.marketplace.product.storage.ProductImageStorage;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuctionService {

	// 최신 등록순. 등록 시각이 같으면 id가 큰 순으로 순서를 고정해 페이지 사이에 항목이 겹치거나 빠지지 않게 한다
	private static final Sort NEWEST_FIRST = Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"));

	// 저장 상태가 아직 종료·취소가 아닌 경매. 시작 전이 반영되지 못한 READY도 마감이 지나면 종료 대상이다 (docs/backend/auction-state.md)
	private static final List<AuctionStatus> CLOSABLE_STATUSES = List.of(AuctionStatus.READY, AuctionStatus.OPEN);

	private final AuctionRepository auctionRepository;
	private final ApplicationEventPublisher eventPublisher;
	private final Clock clock;
	private final ProductImageRepository productImages;
	private final ProductImageStorage imageStorage;

	public AuctionService(AuctionRepository auctionRepository, ApplicationEventPublisher eventPublisher, Clock clock,
		ProductImageRepository productImages, ProductImageStorage imageStorage) {
		this.auctionRepository = auctionRepository;
		this.eventPublisher = eventPublisher;
		this.clock = clock;
		this.productImages = productImages;
		this.imageStorage = imageStorage;
	}

	// 락은 부른 쪽 트랜잭션이 끝날 때까지 유지돼야 하므로 진행 중인 쓰기 트랜잭션 안에서만 부른다
	@Transactional(propagation = Propagation.MANDATORY)
	public Auction getAuctionForUpdate(Long auctionId) {
		return auctionRepository.findByIdForUpdate(auctionId)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
	}

	// 종료 Scheduler가 처리할 경매 id. 마감이 지난 READY·OPEN 경매를 마감 시각이 이른 순으로 최대 limit개 고른다
	public List<Long> findAuctionIdsToClose(int limit) {
		return auctionRepository.findIdsToClose(CLOSABLE_STATUSES, Instant.now(clock), PageRequest.of(0, limit));
	}

	// 경매 하나를 자기 트랜잭션에서 종료한다. 종료됐으면 true.
	// 락을 잡은 뒤 시각을 읽고 상태를 다시 판단하므로, 조회 뒤 다른 처리가 먼저 종료했거나 같은 경매를 두 번 처리해도 결과가 바뀌지 않는다
	@Transactional
	public boolean closeAuction(Long auctionId) {
		Auction auction = getAuctionForUpdate(auctionId);
		Instant now = Instant.now(clock);
		if (!auction.close(now)) {
			return false;
		}

		// 실시간 소식의 version이 이번 종료까지 반영된 값이 되도록 먼저 DB에 반영한다. 소식은 커밋된 뒤에만 나간다
		auctionRepository.flush();
		Long winningBidId = auction.getWinningBid() == null ? null : auction.getWinningBid().getId();
		eventPublisher.publishEvent(
			new AuctionClosedEvent(auctionId, auction.getVersion(), now, winningBidId, auction.getEndAt()));
		return true;
	}

	// GET /api/v1/auctions. 상태 조건과 응답의 status는 같은 서버 시각으로 판단한다
	public AuctionPageResponse searchAuctions(AuctionSearchCondition condition, int page, int size) {
		Instant now = Instant.now(clock);

		Page<Auction> auctions = auctionRepository
			.findAll(toSpecification(condition, now), PageRequest.of(page, size, NEWEST_FIRST));
		List<Long> productIds = auctions.stream().map(auction -> auction.getProduct().getId()).toList();
		// 컬렉션 fetch join으로 페이지를 깨뜨리거나 이미지마다 추가 쿼리를 보내지 않는다.
		Map<Long, String> thumbnails = productIds.isEmpty() ? Map.of() : productImages
			.findByProductIdInAndSortOrder(productIds, 0).stream()
			.collect(Collectors.toMap(image -> image.getProduct().getId(),
				image -> imageStorage.getPublicUrl(image.getObjectKey())));
		Page<AuctionSummaryResponse> result = auctions.map(auction ->
			AuctionSummaryResponse.from(auction, now, thumbnails.get(auction.getProduct().getId())));

		return AuctionPageResponse.from(result);
	}

	private static Specification<Auction> toSpecification(AuctionSearchCondition condition, Instant now) {
		List<Specification<Auction>> specifications = new ArrayList<>();

		if (condition.regionId() != null) {
			specifications.add(AuctionSpecifications.inRegion(condition.regionId()));
		}
		if (condition.category() != null) {
			specifications.add(AuctionSpecifications.inCategory(condition.category()));
		}

		String keyword = condition.keyword() == null ? "" : condition.keyword().strip();
		if (!keyword.isEmpty()) {
			specifications.add(AuctionSpecifications.titleContains(keyword));
		}

		if (condition.status() != null) {
			specifications.add(AuctionSpecifications.logicalStatus(condition.status().toAuctionStatus(), now));
		}

		return Specification.allOf(specifications);
	}
}
