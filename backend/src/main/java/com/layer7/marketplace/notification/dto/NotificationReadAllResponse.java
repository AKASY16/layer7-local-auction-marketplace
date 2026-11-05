package com.layer7.marketplace.notification.dto;

// PATCH /api/v1/notifications/read-all 응답. 이번 요청으로 읽음 처리한 알림 수
public record NotificationReadAllResponse(int updatedCount) {
}
