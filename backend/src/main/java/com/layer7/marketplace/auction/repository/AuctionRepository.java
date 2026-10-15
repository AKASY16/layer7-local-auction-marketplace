package com.layer7.marketplace.auction.repository;

import com.layer7.marketplace.auction.domain.Auction;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuctionRepository extends JpaRepository<Auction, Long> {

	// SELECT ... FOR UPDATE. 같은 경매의 입찰·종료 처리를 한 줄로 세운다 (docs/backend/locking.md)
	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("SELECT a FROM Auction a WHERE a.id = :id")
	Optional<Auction> findByIdForUpdate(@Param("id") Long id);
}
