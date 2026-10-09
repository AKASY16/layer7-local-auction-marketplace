package com.layer7.marketplace.user.domain;

import com.layer7.marketplace.global.time.BaseTimeEntity;
import com.layer7.marketplace.region.domain.Region;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "users")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "email", nullable = false, unique = true, length = 320)
	private String email;

	@Column(name = "password_hash", nullable = false)
	private String passwordHash;

	@Column(name = "nickname", nullable = false, unique = true, length = 50)
	private String nickname;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "region_id", nullable = false)
	private Region region;

	// 신뢰점수는 trust_score = trust_score + ? 원자 UPDATE로만 바꾼다 (docs/backend/erd.md).
	// 엔티티를 저장할 때 들고 있던 옛 값으로 덮어쓰지 않도록 JPA는 읽기만 하고, 처음 값은 DB 기본값 0을 쓴다.
	@Column(name = "trust_score", nullable = false, insertable = false, updatable = false)
	private int trustScore;

	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false, length = 20)
	private UserStatus status;

	public static User create(String email, String passwordHash, String nickname, Region region) {
		User user = new User();
		user.email = email;
		user.passwordHash = passwordHash;
		user.nickname = nickname;
		user.region = region;
		user.status = UserStatus.ACTIVE;
		return user;
	}

	public boolean isActive() {
		return status == UserStatus.ACTIVE;
	}
}
