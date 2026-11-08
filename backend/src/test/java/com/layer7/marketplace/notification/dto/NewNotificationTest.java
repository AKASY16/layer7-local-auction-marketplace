package com.layer7.marketplace.notification.dto;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.layer7.marketplace.notification.domain.NotificationType;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class NewNotificationTest {

	@Test
	@DisplayName("메시지와 dedupeKey는 실제 글자 수로 세어 각각 500자, 200자까지 받는다")
	void countsCharacters() {
		// 이모지는 Java 문자열 길이로는 2지만 MySQL VARCHAR는 1글자로 센다
		assertThatCode(() -> notification("🔔".repeat(500), "k".repeat(200))).doesNotThrowAnyException();
		assertThatThrownBy(() -> notification("🔔".repeat(501), "key"))
			.isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> notification("메시지", "k".repeat(201)))
			.isInstanceOf(IllegalArgumentException.class);
	}

	@ParameterizedTest
	@NullAndEmptySource
	@ValueSource(strings = {"  "})
	@DisplayName("메시지나 dedupeKey가 비어 있으면 거절한다")
	void rejectsBlank(String blank) {
		assertThatThrownBy(() -> notification(blank, "key")).isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> notification("메시지", blank)).isInstanceOf(IllegalArgumentException.class);
	}

	@Test
	@DisplayName("받는 사람과 type은 꼭 있어야 한다")
	void requiresUserAndType() {
		assertThatThrownBy(() -> new NewNotification(null, NotificationType.OUTBID, "메시지", null, null, null, "key"))
			.isInstanceOf(NullPointerException.class);
		assertThatThrownBy(() -> new NewNotification(1L, null, "메시지", null, null, null, "key"))
			.isInstanceOf(NullPointerException.class);
	}

	private static NewNotification notification(String message, String dedupeKey) {
		return new NewNotification(1L, NotificationType.OUTBID, message, null, null, null, dedupeKey);
	}
}
