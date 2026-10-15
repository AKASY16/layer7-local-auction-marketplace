package com.layer7.marketplace.bid.repository;

import com.layer7.marketplace.bid.domain.Bid;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BidRepository extends JpaRepository<Bid, Long> {

	long countByAuctionId(Long auctionId);
}
