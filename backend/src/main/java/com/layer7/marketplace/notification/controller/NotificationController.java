package com.layer7.marketplace.notification.controller;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.AuthenticatedUser;
import com.layer7.marketplace.notification.dto.NotificationPageResponse;
import com.layer7.marketplace.notification.dto.NotificationReadAllResponse;
import com.layer7.marketplace.notification.dto.NotificationResponse;
import com.layer7.marketplace.notification.service.NotificationService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

// 모두 로그인한 본인의 알림만 다룬다 (docs/api/trade-notification.md "3. Notification")
@RestController
@RequestMapping("/api/v1/notifications")
public class NotificationController {

	private final NotificationService notificationService;

	public NotificationController(NotificationService notificationService) {
		this.notificationService = notificationService;
	}

	@GetMapping
	public NotificationPageResponse getMyNotifications(
		@AuthenticationPrincipal AuthenticatedUser user,
		@RequestParam(name = "unreadOnly", defaultValue = "false") boolean unreadOnly,
		@RequestParam(name = "page", defaultValue = "0")
		@Min(0) int page,
		@RequestParam(name = "size", defaultValue = "20")
		@Min(1) @Max(50) int size
	) {
		return notificationService.getMyNotifications(requireUserId(user), unreadOnly, page, size);
	}

	// 같은 요청을 반복해도 결과가 같으므로 Idempotency-Key를 받지 않는다 (05 명세)
	@PatchMapping("/{notificationId}/read")
	public NotificationResponse markRead(
		@AuthenticationPrincipal AuthenticatedUser user,
		@PathVariable Long notificationId
	) {
		return notificationService.markRead(requireUserId(user), notificationId);
	}

	@PatchMapping("/read-all")
	public NotificationReadAllResponse markAllRead(
		@AuthenticationPrincipal AuthenticatedUser user
	) {
		return notificationService.markAllRead(requireUserId(user));
	}

	private static Long requireUserId(AuthenticatedUser user) {
		if (user == null) {
			throw new BusinessException(ErrorCode.UNAUTHORIZED);
		}
		return user.userId();
	}
}
