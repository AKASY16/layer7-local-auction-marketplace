package com.layer7.marketplace.product.repository;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * 관심상품을 중복 없이 저장한다. 같은 회원·상품이 이미 있으면 DB의 고유 키({@code uq_favorites_user_product})가 막는다.
 *
 * <p>JPA 대신 JDBC로 넣는 이유는 {@code NotificationInsertRepository}와 같다. JPA는 저장 중 오류가 나면 트랜잭션 전체를
 * 롤백하게 표시해, 동시에 등록한 요청이 "이미 등록됨"이 아니라 오류로 끝난다. 같은 이유로 이 클래스에는
 * {@code @Transactional}을 붙이지 않고, {@code INSERT IGNORE}는 잘못된 id(FK) 오류까지 숨겨서 쓰지 않는다.
 */
@Repository
public class FavoriteInsertRepository {

	private final JdbcTemplate jdbcTemplate;

	public FavoriteInsertRepository(JdbcTemplate jdbcTemplate) {
		this.jdbcTemplate = jdbcTemplate;
	}

	/**
	 * 새로 넣었으면 true, 이미 등록돼 있으면 false. 이미 있으면 처음 등록 시각을 그대로 둔다.
	 *
	 * <p>다른 트랜잭션이 같은 회원·상품을 넣고 아직 커밋하지 않았으면 그 트랜잭션이 끝날 때까지 기다린다.
	 * 커밋하면 false, 롤백하면 이쪽이 새로 넣어 true다.
	 */
	public boolean insertIfAbsent(Long userId, Long productId, Instant createdAt) {
		try {
			jdbcTemplate.update(
				"INSERT INTO favorites (user_id, product_id, created_at) VALUES (?, ?, ?)",
				userId,
				productId,
				// DATETIME 컬럼에는 UTC 시각을 그대로 넣는다 (서버 시간대와 무관하게)
				LocalDateTime.ofInstant(createdAt, ZoneOffset.UTC)
			);
			return true;
		} catch (DuplicateKeyException e) {
			return false;
		}
	}
}
