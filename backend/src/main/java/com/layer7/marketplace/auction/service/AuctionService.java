package com.layer7.marketplace.auction.service;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.dto.AuctionPageResponse;
import com.layer7.marketplace.auction.dto.AuctionSearchCondition;
import com.layer7.marketplace.auction.dto.AuctionSummaryResponse;
import com.layer7.marketplace.auction.repository.AuctionRepository;
import com.layer7.marketplace.auction.repository.AuctionSpecifications;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
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

	private final AuctionRepository auctionRepository;
	private final Clock clock;

	public AuctionService(AuctionRepository auctionRepository, Clock clock) {
		this.auctionRepository = auctionRepository;
		this.clock = clock;
	}

	// 락은 부른 쪽 트랜잭션이 끝날 때까지 유지돼야 하므로 진행 중인 쓰기 트랜잭션 안에서만 부른다
	@Transactional(propagation = Propagation.MANDATORY)
	public Auction getAuctionForUpdate(Long auctionId) {
		return auctionRepository.findByIdForUpdate(auctionId)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
	}

	// GET /api/v1/auctions. 상태 조건과 응답의 status는 같은 서버 시각으로 판단한다
	public AuctionPageResponse searchAuctions(AuctionSearchCondition condition, int page, int size) {
		Instant now = Instant.now(clock);

		Page<AuctionSummaryResponse> result = auctionRepository
			.findAll(toSpecification(condition, now), PageRequest.of(page, size, NEWEST_FIRST))
			.map(auction -> AuctionSummaryResponse.from(auction, now));

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
