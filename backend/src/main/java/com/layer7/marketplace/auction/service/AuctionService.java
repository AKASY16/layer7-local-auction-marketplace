package com.layer7.marketplace.auction.service;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.repository.AuctionRepository;
import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuctionService {

	private final AuctionRepository auctionRepository;

	public AuctionService(AuctionRepository auctionRepository) {
		this.auctionRepository = auctionRepository;
	}

	// 락은 부른 쪽 트랜잭션이 끝날 때까지 유지돼야 하므로 진행 중인 쓰기 트랜잭션 안에서만 부른다
	@Transactional(propagation = Propagation.MANDATORY)
	public Auction getAuctionForUpdate(Long auctionId) {
		return auctionRepository.findByIdForUpdate(auctionId)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
	}
}
