# Trade / Trust / Notification API

## 1. Trade

TradeStatus:
- AWAITING_RESPONSE
- IN_PROGRESS
- COMPLETION_REQUESTED
- COMPLETED
- DECLINED
- NO_RESPONSE
- CANCELED
- EXPIRED

기한:
- `responseDeadline = Auction.endAt + 24시간`: 낙찰자의 진행/포기 응답 기한
- `tradeDeadline = Auction.endAt + 7일`: 완료 요청과 취소 기한
- `completionDeadline = max(tradeDeadline, completionRequestedAt + 24시간)`: 완료 요청을 받은 상대방의 확인/거절 기한. 기한 직전에 요청해도 상대방은 최소 24시간을 보장받음
- 모든 기한은 Scheduler 처리 시각이 아니라 위 기준으로 계산하며, 기한 이후 명령은 서버시간 기준으로 거절
- 가장 긴 거래 기간은 endAt + 8일

상태 표시:
- `status`는 서버시간 기준 논리 상태입니다 ([상태와 finalized](../05-api-spec.md#상태와-finalized)). 예를 들어 저장 상태가 AWAITING_RESPONSE여도 responseDeadline이 지났으면 `NO_RESPONSE`로 반환합니다.
- `finalized`는 저장 상태가 COMPLETED / DECLINED / NO_RESPONSE / CANCELED / EXPIRED에 도달했는지 여부입니다. 논리 상태가 바뀌었어도 finalized가 false면 신뢰점수·정지·상품 상태가 아직 반영되지 않은 상태입니다.

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
  "finalized": false,
  "responseDeadline": "2026-10-05T04:30:00Z",
  "tradeDeadline": "2026-10-11T04:30:00Z",
  "completionRequestedBy": null,
  "completionRequestedAt": null,
  "completionDeadline": null,
  "completedAt": null,
  "canceledBy": null,
  "canceledAt": null,
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
- buyer의 연속 실패 횟수 증가 ([이용 정지](#이용-정지))
- seller 알림
- Product는 ACTIVE 유지
- 차순위 승계 없음
- seller는 새 Auction 재경매 가능

### POST /trades/{tradeId}/cancel
Header: `Idempotency-Key`

일방 취소.
- seller: `AWAITING_RESPONSE` / `IN_PROGRESS` / `COMPLETION_REQUESTED`에서 가능
- buyer: `IN_PROGRESS` / `COMPLETION_REQUESTED`에서 가능. `AWAITING_RESPONSE`에서는 decline 사용
- `AWAITING_RESPONSE`는 responseDeadline 전, 나머지는 tradeDeadline 전까지만 가능

`→ CANCELED`

효과:
- 취소한 쪽 신뢰점수 -5
- TrustHistory TRADE_CANCELED
- 취소한 쪽의 연속 실패 횟수 증가
- 상대방 Notification
- Product는 ACTIVE 유지
- seller는 새 Auction 재경매 가능

Errors:
- 403 FORBIDDEN
- 409 TRADE_INVALID_STATE
- 409 TRADE_RESPONSE_EXPIRED
- 409 TRADE_DEADLINE_PASSED

### POST /trades/{tradeId}/completion-request
Header: `Idempotency-Key`

seller 또는 buyer가 `IN_PROGRESS`에서 요청. tradeDeadline 전까지만 가능.

`IN_PROGRESS → COMPLETION_REQUESTED`

요청 시 `completionDeadline = max(tradeDeadline, completionRequestedAt + 24시간)`을 저장합니다.

Response:
```json
{
  "id": 800,
  "status": "COMPLETION_REQUESTED",
  "completionRequestedBy": {
    "id": 15,
    "nickname": "seller"
  },
  "completionRequestedAt": "2026-10-04T10:00:00Z",
  "completionDeadline": "2026-10-11T04:30:00Z"
}
```

### POST /trades/{tradeId}/completion-confirm
Header: `Idempotency-Key`

완료 요청의 **상대방만** 가능. completionDeadline 전까지 가능.

`COMPLETION_REQUESTED → COMPLETED`

효과:
- seller +2
- buyer +2
- Product → SOLD
- TrustHistory 각 1건
- 양측 Notification

### POST /trades/{tradeId}/completion-reject
Header: `Idempotency-Key`

완료 요청의 상대방만 가능. completionDeadline 전까지 가능.

- tradeDeadline 전: `COMPLETION_REQUESTED → IN_PROGRESS`, 완료 요청 필드와 completionDeadline은 clear
- tradeDeadline 이후 연장 구간: IN_PROGRESS로 돌아갈 수 없으므로 `COMPLETION_REQUESTED → EXPIRED`

요청자에게 COMPLETION_REJECTED 알림.

### 기한 처리
아래 전이는 HTTP API로 직접 만들지 않고 Scheduler가 처리합니다.

| 대상 | 조건 | 결과 | 효과 |
|---|---|---|---|
| AWAITING_RESPONSE | responseDeadline <= now | NO_RESPONSE | buyer -10, TrustHistory WINNER_NO_RESPONSE, 연속 실패 횟수 증가 |
| IN_PROGRESS | tradeDeadline <= now | EXPIRED | 신뢰점수 변동 없음 |
| COMPLETION_REQUESTED | completionDeadline <= now | COMPLETED | completion-confirm과 같은 효과 |

공통:
- 양측 Notification
- NO_RESPONSE / EXPIRED는 Product ACTIVE 유지, 차순위 승계 없음, seller는 재경매 가능
- 상태검사 + Trade PESSIMISTIC_WRITE로 중복 실행에도 효과는 한 번만 반영

---

## 2. Trust

신뢰점수는 표시용 지표이며 점수만으로 입찰을 막지 않습니다. 제재는 아래 이용 정지로 처리합니다.

TrustHistory reason:
- TRADE_COMPLETED: seller/buyer +2
- WINNER_DECLINED: buyer -5
- WINNER_NO_RESPONSE: buyer -10
- TRADE_CANCELED: 취소한 쪽 -5

### 이용 정지
본인 책임의 거래 실패가 3회 연속되면 7일간 거래 참여가 정지됩니다.

- 실패: WINNER_DECLINED / WINNER_NO_RESPONSE / TRADE_CANCELED(본인 취소)
- 연속: 마지막 TRADE_COMPLETED와 마지막 자동 정지 이후에 쌓인 실패가 3건이 되는 순간 정지. EXPIRED는 세지 않음
- 정지 중 불가: 수동입찰, AutoBid 설정·변경·재활성화, 경매 생성·재경매 (`403 USER_RESTRICTED`)
- 정지 중 허용: AutoBid 중지, 진행 중 Trade 명령, 상품 수정·내용 추가
- 정지는 실패를 만든 트랜잭션 안에서 UserRestriction으로 생성하며 `UNIQUE(triggerTradeId)`로 중복 생성을 막음
- 해제는 Scheduler 없이 `endsAt`과 서버시간으로 판정
- 정지 시 USER_RESTRICTED 알림
- MVP에는 수동 정지 API가 없으며 운영자가 `source = ADMIN` 기록을 DB에 직접 생성

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
- TRADE_DEADLINE_SOON (응답 기한 / 거래 기한 / 완료 응답 기한 임박)
- TRADE_PROCEEDED
- TRADE_DECLINED
- TRADE_NO_RESPONSE
- TRADE_CANCELED
- TRADE_EXPIRED
- PRODUCT_APPEND_ADDED
- COMPLETION_REQUESTED
- COMPLETION_REJECTED
- TRADE_COMPLETED
- USER_RESTRICTED

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
- 동일 endpointHash가 현재 사용자에게 이미 있으면 key 정보 갱신
- 동일 endpointHash가 다른 사용자에게 연결되어 있으면 현재 사용자로 소유권을 이전하고 key 정보 갱신
- 공유 브라우저에서 이전 계정의 알림이 새 로그인 사용자에게 섞이지 않도록 함

로그아웃 UI에서는 현재 브라우저의 subscriptionId를 DELETE한 뒤 토큰을 제거하는 것을 권장합니다.

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
