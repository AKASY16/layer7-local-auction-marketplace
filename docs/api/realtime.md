# Realtime / WebSocket 명세

Spring WebSocket + STOMP를 사용합니다.

## 연결
- WebSocket endpoint: `/ws`
- STOMP `CONNECT` frame의 `Authorization: Bearer <access-token>` 헤더로 JWT 인증
- 공개 Auction topic만 사용할 경우 인증 없이 연결 가능
- `/user/queue/**` 구독은 인증된 CONNECT session만 허용
- 클라이언트는 WebSocket을 통해 입찰 명령을 보내지 않으며, 상태변경 명령은 REST API를 사용

## 공개 Auction Topic

Subscribe:
```text
/topic/auctions/{auctionId}
```

공통 envelope:
```json
{
  "type": "AUCTION_PRICE_CHANGED",
  "occurredAt": "2026-10-03T05:00:00Z",
  "auctionId": 40,
  "data": {}
}
```

### AUCTION_PRICE_CHANGED
DB Commit 이후 발행.

```json
{
  "type": "AUCTION_PRICE_CHANGED",
  "occurredAt": "2026-10-03T05:00:00Z",
  "auctionId": 40,
  "data": {
    "currentPrice": 10500,
    "nextBidAmount": 11000,
    "bidCount": 5,
    "leadingBidder": {
      "id": 22,
      "nickname": "buyer02"
    }
  }
}
```

### AUCTION_STATUS_CHANGED

저장 상태를 바꾼 쪽이 DB Commit 이후 발행합니다.
- OPEN: 시작 Scheduler 또는 startAt 이후 첫 쓰기 요청(입찰 등)이 READY → OPEN으로 바꿀 때
- ENDED: 종료 Scheduler가 낙찰 확정·Trade 생성을 마쳤을 때 (`finalized: true`)
- CANCELED: 판매자 취소 시 (`finalized: true`)

논리적으로 종료되는 endAt 순간에는 이벤트가 없습니다. 클라이언트는 `endAt`과 `serverTime`으로 종료를 표시하고, 정산 완료는 ENDED 이벤트의 `finalized: true`로 확인합니다.

```json
{
  "type": "AUCTION_STATUS_CHANGED",
  "occurredAt": "2026-10-04T04:30:01Z",
  "auctionId": 40,
  "data": {
    "status": "ENDED",
    "finalized": true,
    "winningBidId": 305,
    "endAt": "2026-10-04T04:30:00Z"
  }
}
```

### PRODUCT_APPEND_ADDED

```json
{
  "type": "PRODUCT_APPEND_ADDED",
  "occurredAt": "2026-10-03T06:00:00Z",
  "auctionId": 40,
  "data": {
    "appendId": 700,
    "content": "구성품 케이블도 함께 드립니다.",
    "createdAt": "2026-10-03T06:00:00Z"
  }
}
```

## 사용자 전용 Queue

Subscribe:
```text
/user/queue/notifications
```

Payload는 REST Notification과 동일한 형태를 사용합니다.

예:
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

## 전달 원칙
- 비즈니스 상태 변경과 Notification row 저장은 동일 DB Transaction
- WebSocket / Web Push 발송은 `AFTER_COMMIT`
- 클라이언트는 WebSocket 이벤트를 절대 DB의 유일한 진실원천으로 간주하지 않음
- 연결 유실/재연결 시 REST 상세 API를 다시 조회해 최종 상태 동기화
- 동일 이벤트 중복 수신 가능성을 고려해 Notification.id 또는 event 식별자로 Frontend가 중복 표시를 방지할 수 있음
