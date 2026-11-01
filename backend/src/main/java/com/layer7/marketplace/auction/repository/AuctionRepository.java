package com.layer7.marketplace.auction.repository;

import com.layer7.marketplace.auction.domain.Auction;
import com.layer7.marketplace.auction.domain.AuctionStatus;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuctionRepository extends JpaRepository<Auction, Long>, JpaSpecificationExecutor<Auction> {

	// SELECT ... FOR UPDATE. 같은 경매의 입찰·종료 처리를 한 줄로 세운다 (docs/backend/locking.md)
	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("SELECT a FROM Auction a WHERE a.id = :id")
	Optional<Auction> findByIdForUpdate(@Param("id") Long id);

	// 종료 Scheduler 대상(docs/backend/scheduler.md). 락 전 조회라 id만 읽고, 판단은 락을 잡은 뒤 다시 한다 (docs/backend/locking.md)
	@Query("""
		SELECT a.id FROM Auction a
		WHERE a.status IN :statuses AND a.endAt <= :now
		ORDER BY a.endAt, a.id
		""")
	List<Long> findIdsToClose(
		@Param("statuses") Collection<AuctionStatus> statuses,
		@Param("now") Instant now,
		Pageable pageable
	);

	// 목록 항목에 쓰는 상품·지역을 함께 읽어 경매마다 추가 조회가 나가지 않게 한다. 개수 조회에는 적용되지 않는다
	@Override
	@EntityGraph(attributePaths = {"product", "region"})
	Page<Auction> findAll(Specification<Auction> spec, Pageable pageable);
}
