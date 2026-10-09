package com.layer7.marketplace.trust.repository;

import com.layer7.marketplace.trust.dto.TradingRestrictionResponse;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Calendar;
import java.util.List;
import java.util.Optional;
import java.util.TimeZone;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class UserRestrictionRepository {

	private final JdbcTemplate jdbcTemplate;

	public UserRestrictionRepository(JdbcTemplate jdbcTemplate) {
		this.jdbcTemplate = jdbcTemplate;
	}

	public Optional<TradingRestrictionResponse> findActiveTradingRestriction(
		Long userId,
		Instant now
	) {
		String sql = """
			SELECT reason, ends_at
			FROM user_restrictions
			WHERE user_id = ?
			  AND type = 'TRADING'
			  AND lifted_at IS NULL
			  AND starts_at <= ?
			  AND (ends_at IS NULL OR ends_at > ?)
			ORDER BY (ends_at IS NULL) DESC, ends_at DESC, id DESC
			LIMIT 1
			""";

		List<TradingRestrictionResponse> restrictions = jdbcTemplate.query(
			connection -> {
				var statement = connection.prepareStatement(sql);

				Calendar utc = Calendar.getInstance(
					TimeZone.getTimeZone("UTC")
				);

				statement.setLong(1, userId);
				statement.setTimestamp(2, Timestamp.from(now), utc);
				statement.setTimestamp(3, Timestamp.from(now), utc);

				return statement;
			},
			(resultSet, rowNum) -> {
				Calendar utc = Calendar.getInstance(
					TimeZone.getTimeZone("UTC")
				);

				Timestamp endsAt = resultSet.getTimestamp("ends_at", utc);

				return new TradingRestrictionResponse(
					resultSet.getString("reason"),
					endsAt == null ? null : endsAt.toInstant()
				);
			}
		);

		return restrictions.stream().findFirst();
	}
}
