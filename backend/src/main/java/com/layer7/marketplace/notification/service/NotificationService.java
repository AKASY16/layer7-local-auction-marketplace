package com.layer7.marketplace.notification.service;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.notification.domain.Notification;
import com.layer7.marketplace.notification.dto.NewNotification;
import com.layer7.marketplace.notification.dto.NotificationPageResponse;
import com.layer7.marketplace.notification.dto.NotificationReadAllResponse;
import com.layer7.marketplace.notification.dto.NotificationResponse;
import com.layer7.marketplace.notification.repository.NotificationInsertRepository;
import com.layer7.marketplace.notification.repository.NotificationRepository;
import java.time.Clock;
import java.time.Instant;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class NotificationService {

	// 최신순. 같은 시각에 만든 알림은 나중에 만든 것(id가 큰 것)이 먼저다
	private static final Sort LATEST_FIRST = Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"));

	private final NotificationRepository notificationRepository;
	private final NotificationInsertRepository notificationInsertRepository;
	private final Clock clock;

	public NotificationService(
		NotificationRepository notificationRepository,
		NotificationInsertRepository notificationInsertRepository,
		Clock clock
	) {
		this.notificationRepository = notificationRepository;
		this.notificationInsertRepository = notificationInsertRepository;
		this.clock = clock;
	}

	/**
	 * 알림을 만든다. 같은 {@code dedupeKey}의 알림이 이미 있으면 만들지 않고 false를 돌려준다.
	 *
	 * <p>호출한 쪽 트랜잭션 안에서 저장되므로, 그 작업이 롤백되면 알림도 남지 않는다. 중복이어도 호출한 쪽 트랜잭션은 계속 쓸 수 있다.
	 * 회원·상품·경매는 저장할 때 바로 INSERT되므로(IDENTITY), 같은 트랜잭션에서 방금 만든 경매를 가리켜도 된다.
	 */
	@Transactional
	public boolean create(NewNotification notification) {
		return notificationInsertRepository.insertIfAbsent(notification, Instant.now(clock));
	}

	public NotificationPageResponse getMyNotifications(Long userId, boolean unreadOnly, int page, int size) {
		Pageable pageable = PageRequest.of(page, size, LATEST_FIRST);

		Page<Notification> notifications = unreadOnly
			? notificationRepository.findByUserIdAndReadAtIsNull(userId, pageable)
			: notificationRepository.findByUserId(userId, pageable);

		return NotificationPageResponse.from(notifications.map(NotificationResponse::from));
	}

	/**
	 * 본인 알림을 읽음 처리한다. 이미 읽은 알림은 처음 읽은 시각을 그대로 두고 같은 결과를 돌려준다.
	 * 다른 사람의 알림이면 있는지 여부도 알리지 않도록 없는 알림과 같이 404다.
	 */
	@Transactional
	public NotificationResponse markRead(Long userId, Long notificationId) {
		notificationRepository.markRead(notificationId, userId, Instant.now(clock));

		return notificationRepository.findByIdAndUserId(notificationId, userId)
			.map(NotificationResponse::from)
			.orElseThrow(() -> new BusinessException(ErrorCode.RESOURCE_NOT_FOUND));
	}

	@Transactional
	public NotificationReadAllResponse markAllRead(Long userId) {
		int updatedCount = notificationRepository.markAllRead(userId, Instant.now(clock));
		return new NotificationReadAllResponse(updatedCount);
	}
}
