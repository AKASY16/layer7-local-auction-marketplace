package com.layer7.marketplace.bid.repository;

import com.layer7.marketplace.bid.domain.Bid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BidRepository extends JpaRepository<Bid, Long> {

	long countByAuctionId(Long auctionId);

	// 입찰자를 함께 읽어 항목마다 User를 다시 조회하지 않는다. 정렬은 Pageable로 받는다
	@Query(value = "SELECT b FROM Bid b JOIN FETCH b.bidder WHERE b.auction.id = :auctionId",
		countQuery = "SELECT COUNT(b) FROM Bid b WHERE b.auction.id = :auctionId")
	Page<Bid> findHistory(@Param("auctionId") Long auctionId, Pageable pageable);
}
