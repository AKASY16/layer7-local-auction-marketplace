# Realtime / WebSocket 명세

Spring WebSocket + STOMP를 사용합니다.

## 연결
- WebSocket endpoint: `/ws`
- STOMP `CONNECT` frame의 `Authorization: Bearer <access-token>` 헤더로 JWT 인증
- 공개 Auction topic만 사용할 경우 인증 없이 연결 가능
- `/user/queue/**` 구독은 인증된 CONNECT session만 허용
- 서버는 CONNECT 시 Access Token 만료 시각을 세션에 저장하고, 만료 후 들어온 SUBSCRIBE 프레임에는 ERROR를 보내고 연결을 종료
- 클라이언트는 Access Token을 갱신하면 새 토큰으로 다시 연결하고, 재연결 후 REST로 상태를 동기화
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
  "version": 7,
  "data": {}
}
```

`version`은 Auction row가 바뀔 때마다 1씩 증가하는 값입니다(`auctions.version`). AUCTION_PRICE_CHANGED와 AUCTION_STATUS_CHANGED에만 포함됩니다.

이벤트는 요청마다 다른 스레드에서 커밋 이후 발행되므로, 커밋 순서와 도착 순서가 뒤바뀔 수 있습니다. 클라이언트는 경매별로 지금까지 본 가장 큰 version(REST 상세 응답 포함)을 기억하고, 그보다 작거나 같은 version의 이벤트는 버립니다.

### AUCTION_PRICE_CHANGED
DB Commit 이후 발행.

```json
{
  "type": "AUCTION_PRICE_CHANGED",
  "occurredAt": "2026-10-03T05:00:00Z",
  "auctionId": 40,
  "version": 7,
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
  "version": 12,
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
- 경매 이벤트의 순서는 `version`으로 판단하며, 오래된 이벤트는 버림

## 발송 방식

- AFTER_COMMIT 리스너는 발송 작업을 별도 executor에 넘기기만 합니다. `@TransactionalEventListener(AFTER_COMMIT)`는 기본적으로 요청 스레드에서 동기로 실행되고 이 시점에는 DB 커넥션도 아직 반환되지 않아서, 그 안에서 외부 HTTP(Web Push)를 호출하면 응답 지연과 커넥션 점유가 함께 늘어납니다.
- 발송 작업에서 DB를 쓰는 경우(만료 구독 삭제 등)는 별도 트랜잭션으로 처리합니다.
- Web Push 응답이 404/410이면 해당 PushSubscription을 삭제하고, 429/5xx는 최대 3회 backoff 재시도 후 포기합니다.
- 커밋 직후 서버가 종료되면 발송이 유실될 수 있습니다. Notification row와 REST 재조회가 최종 상태를 보장하므로 발송 보장을 위한 outbox는 MVP에서 두지 않습니다.
- MVP는 단일 서버의 STOMP Simple Broker를 사용합니다. 서버를 여러 대로 늘리면 외부 broker relay가 필요합니다.
