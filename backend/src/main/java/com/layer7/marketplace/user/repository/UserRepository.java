package com.layer7.marketplace.user.repository;

import com.layer7.marketplace.user.domain.User;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserRepository extends JpaRepository<User, Long> {

	boolean existsByEmail(String email);

	boolean existsByNickname(String nickname);

	Optional<User> findByEmail(String email);

	// SELECT ... FOR SHARE
	@Lock(LockModeType.PESSIMISTIC_READ)
	@Query("SELECT u FROM User u WHERE u.id = :id")
	Optional<User> findByIdForShare(@Param("id") Long id);
}
