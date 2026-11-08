package com.layer7.marketplace.notification.dto;

import java.util.List;
import org.springframework.data.domain.Page;

// GET /api/v1/notifications 응답. 05 명세의 페이지 공통 형식
public record NotificationPageResponse(
	List<NotificationResponse> content,
	int page,
	int size,
	long totalElements,
	int totalPages
) {

	public static NotificationPageResponse from(Page<NotificationResponse> result) {
		return new NotificationPageResponse(
			result.getContent(),
			result.getNumber(),
			result.getSize(),
			result.getTotalElements(),
			result.getTotalPages()
		);
	}
}
