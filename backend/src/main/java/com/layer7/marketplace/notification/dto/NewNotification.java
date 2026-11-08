package com.layer7.marketplace.notification.dto;

import com.layer7.marketplace.notification.domain.NotificationType;
import java.util.Objects;

/**
 * 다른 기능이 알림을 만들 때 넘기는 값. 사용자 입력이 아니라 서버 코드가 만드는 값이라, 잘못되면 400이 아니라 예외로 막는다.
 *
 * <p>{@code dedupeKey}는 "같은 일에 대한 알림"을 가리키는 키다. 같은 키로 다시 만들면 새로 만들지 않는다.
 * 예: 타임 경매 시작 알림이면 경매 id와 받는 사람 id를 넣어, 같은 사람이 같은 경매의 시작 알림을 두 번 받지 않게 한다.
 */
public record NewNotification(
	Long userId,
	NotificationType type,
	String message,
	Long productId,
	Long auctionId,
	Long tradeId,
	String dedupeKey
) {

	// DB 컬럼 길이(VARCHAR). MySQL은 글자 수로 세므로 이모지도 1글자다
	private static final int MESSAGE_MAX_LENGTH = 500;
	private static final int DEDUPE_KEY_MAX_LENGTH = 200;

	public NewNotification {
		Objects.requireNonNull(userId, "userId");
		Objects.requireNonNull(type, "type");
		requireText(message, MESSAGE_MAX_LENGTH, "message");
		requireText(dedupeKey, DEDUPE_KEY_MAX_LENGTH, "dedupeKey");
	}

	// 길이를 넘기면 DB가 오류를 내지만, 여기서 먼저 막아 어떤 값이 문제인지 바로 보이게 한다
	private static void requireText(String value, int maxLength, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + "은(는) 비어 있을 수 없습니다.");
		}
		if (value.codePointCount(0, value.length()) > maxLength) {
			throw new IllegalArgumentException(name + "은(는) " + maxLength + "자를 넘을 수 없습니다.");
		}
	}
}
