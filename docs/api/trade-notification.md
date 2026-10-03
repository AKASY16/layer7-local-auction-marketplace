# Trade / Trust / Notification API

## 1. Trade

TradeStatus:
- AWAITING_RESPONSE
- IN_PROGRESS
- COMPLETION_REQUESTED
- COMPLETED
- DECLINED
- NO_RESPONSE

### GET /trades/{tradeId}
판매자/구매자 당사자만 조회 가능.

Response:
```json
{
  "id": 800,
  "auctionId": 40,
  "seller": {
    "id": 15,
    "nickname": "seller",
    "trustScore": 4
  },
  "buyer": {
    "id": 21,
    "nickname": "buyer",
    "trustScore": 2
  },
  "status": "AWAITING_RESPONSE",
  "responseDeadline": "2026-10-05T04:30:00Z",
  "completionRequestedBy": null,
  "completionRequestedAt": null,
  "completedAt": null,
  "createdAt": "2026-10-04T04:30:01Z",
  "updatedAt": "2026-10-04T04:30:01Z"
}
```

### POST /trades/{tradeId}/proceed
Header: `Idempotency-Key`

낙찰자(buyer)만 가능.
`AWAITING_RESPONSE → IN_PROGRESS`.

상태가 아직 AWAITING_RESPONSE로 남아 있더라도 서버시간이 `responseDeadline` 이상이면 거절합니다. Scheduler 반영 지연으로 응답기한이 늘어나지 않습니다.

Response `200`: Trade.

Errors:
- 403 FORBIDDEN
- 409 TRADE_RESPONSE_EXPIRED
- 409 TRADE_INVALID_STATE

### POST /trades/{tradeId}/decline
Header: `Idempotency-Key`

낙찰자만 가능.
`AWAITING_RESPONSE → DECLINED`.

서버시간이 `responseDeadline` 이상이면 거절합니다.

효과:
- buyer 신뢰점수 -5
- TrustHistory WINNER_DECLINED
- seller 알림
- Product는 ACTIVE 유지
- 차순위 승계 없음
- seller는 새 Auction 재경매 가능

### POST /trades/{tradeId}/completion-request
Header: `Idempotency-Key`

seller 또는 buyer가 `IN_PROGRESS`에서 요청.

`IN_PROGRESS → COMPLETION_REQUESTED`

Response:
```json
{
  "id": 800,
  "status": "COMPLETION_REQUESTED",
  "completionRequestedBy": {
    "id": 15,
    "nickname": "seller"
  },
  "completionRequestedAt": "2026-10-04T10:00:00Z"
}
```

### POST /trades/{tradeId}/completion-confirm
Header: `Idempotency-Key`

완료 요청의 **상대방만** 가능.

`COMPLETION_REQUESTED → COMPLETED`

효과:
- seller +2
- buyer +2
- Product → SOLD
- TrustHistory 각 1건
- 양측 Notification

### POST /trades/{tradeId}/completion-reject
Header: `Idempotency-Key`

완료 요청의 상대방만 가능.

`COMPLETION_REQUESTED → IN_PROGRESS`

완료 요청 필드는 clear.

### NO_RESPONSE
HTTP API로 직접 만들지 않습니다.

Scheduler가:
- status = AWAITING_RESPONSE
- responseDeadline <= now

인 Trade를 처리하여 `NO_RESPONSE`.

효과:
- buyer -10
- TrustHistory WINNER_NO_RESPONSE
- seller Notification
- Product는 ACTIVE 유지
- 차순위 승계 없음
- seller는 새 Auction 재경매 가능

---

## 2. Trust

### GET /users/{userId}/trust
공개 신뢰점수 요약.

Response:
```json
{
  "userId": 21,
  "nickname": "buyer",
  "trustScore": 2
}
```

### GET /users/me/trust-history
본인 TrustHistory 목록.

Item:
```json
{
  "id": 900,
  "tradeId": 800,
  "delta": 2,
  "reason": "TRADE_COMPLETED",
  "scoreAfter": 4,
  "createdAt": "2026-10-04T10:00:00Z"
}
```

---

## 3. Notification

대표 type:
- OUTBID
- AUTO_BID_EXHAUSTED
- AUCTION_WON
- AUCTION_UNSOLD
- TRADE_RESPONSE_REQUIRED
- TRADE_DEADLINE_SOON
- TRADE_PROCEEDED
- TRADE_DECLINED
- TRADE_NO_RESPONSE
- PRODUCT_APPEND_ADDED
- COMPLETION_REQUESTED
- TRADE_COMPLETED

### GET /notifications
현재 사용자의 알림.

Query:
- `unreadOnly=true|false`
- page / size

Item:
```json
{
  "id": 1000,
  "type": "OUTBID",
  "message": "다른 입찰자가 현재 최고 입찰자가 되었습니다.",
  "productId": 30,
  "auctionId": 40,
  "tradeId": null,
  "readAt": null,
  "createdAt": "2026-10-03T05:00:00Z"
}
```

### PATCH /notifications/{notificationId}/read
본인 알림 읽음 처리.

Response `200`: 갱신 Notification.

### PATCH /notifications/read-all
모든 미읽음 알림 읽음 처리.

Response:
```json
{
  "updatedCount": 7
}
```

---

## 4. PushSubscription

### POST /push-subscriptions
Web Push 구독 등록/갱신.

Request:
```json
{
  "endpoint": "https://push.example/...",
  "p256dh": "...",
  "auth": "..."
}
```

Backend:
- endpoint SHA-256 → endpointHash
- 동일 endpointHash가 있으면 현재 사용자 구독값 갱신

Response `200`:
```json
{
  "id": 1100,
  "createdAt": "2026-10-03T05:00:00Z",
  "updatedAt": "2026-10-03T05:00:00Z"
}
```

### DELETE /push-subscriptions/{subscriptionId}
현재 사용자 소유 구독만 삭제.

Response `204`.
