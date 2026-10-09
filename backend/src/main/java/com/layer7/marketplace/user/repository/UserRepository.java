package com.layer7.marketplace.user.repository;

import com.layer7.marketplace.user.domain.User;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, Long> {

	boolean existsByEmail(String email);

	boolean existsByNickname(String nickname);

	Optional<User> findByEmail(String email);
}
