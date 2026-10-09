package com.layer7.marketplace.user.domain;

public enum UserStatus {
	ACTIVE,
	// 회원탈퇴는 행을 지우지 않고 이 상태로 바꾼다 (docs/backend/erd.md)
	WITHDRAWN
}
