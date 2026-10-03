# API 명세 v1

Base URL: `/api/v1`

이 문서는 Frontend/Backend 간 계약의 기준입니다. 실제 구현 시 DTO/Controller 이름은 달라질 수 있지만 HTTP method, path, payload 의미, 상태코드와 비즈니스 규칙은 이 명세를 기준으로 합니다.

## 상세 문서
- [Auth / User / Product](api/auth-user-product.md)
- [Auction / Bid / AutoBid](api/auction-bidding.md)
- [Trade / Trust / Notification](api/trade-notification.md)
- [WebSocket / Realtime](api/realtime.md)

---

## 공통 규칙

### 인증
인증이 필요한 REST API는 다음 헤더를 사용합니다.

```http
Authorization: Bearer <access-token>
```

MVP는 JWT Access Token 방식으로 구현합니다. Login 응답은 token과 `expiresAt`을 반환합니다. Refresh Token 흐름은 MVP 범위에서 제외하며 토큰 만료 시 재로그인합니다.

### 시간
- JSON 시간은 ISO-8601 UTC 문자열 사용
- 예: `2026-10-03T04:30:00Z`
- 서버 내부 판정은 `Instant` / UTC
- 경매 입찰 가능 시간: `startAt <= serverNow < endAt`
- 브라우저 카운트다운은 표시용이며 서버시간이 최종 권위

### 상태와 finalized
Auction과 Trade의 `status`는 DB에 저장된 값이 아니라 서버시간 기준 **논리 상태**로 반환합니다. 저장 상태는 Scheduler가 뒤따라 맞추는 값이고, 시간 경계의 기준은 startAt/endAt과 각 기한입니다.

`finalized`는 저장 상태가 최종 상태에 도달해 후처리(낙찰 확정·Trade 생성·신뢰점수·정지·알림 등)가 끝났는지를 나타냅니다.
- Auction: 저장 status가 ENDED 또는 CANCELED면 true
- Trade: 저장 status가 COMPLETED / DECLINED / NO_RESPONSE / CANCELED / EXPIRED면 true

예:
- `status = ENDED, finalized = false`: 종료됐지만 낙찰 확정 전(집계 중)
- `status = ENDED, finalized = true, winningBid = null`: 유찰
- `status = NO_RESPONSE, finalized = false`: 응답기한이 지났고 페널티 반영 전

상세 규칙: [Auction / Trade 상태 모델](backend/auction-state.md)

### 금액
- KRW 원 단위 정수
- JSON에서는 number
- 음수/소수 금액 없음
- startPrice, Bid.amount, AutoBid.maxAmount는 모두 BidIncrementPolicy의 유효 가격 격자를 따라야 함

### 페이지
목록 API 기본값:
- `page=0`
- `size=20`
- 최대 `size=50`

응답:

```json
{
  "content": [],
  "page": 0,
  "size": 20,
  "totalElements": 0,
  "totalPages": 0
}
```

### 성공 응답
별도 공통 `data` wrapper를 사용하지 않습니다. Resource 또는 Command Result를 직접 반환합니다.

### Idempotency
중복 실행 시 부작용이 발생하는 명령 API는 다음 헤더를 필수로 사용합니다.

```http
Idempotency-Key: <UUID>
```

적용 scope:
- PRODUCT_CREATE
- AUCTION_CREATE
- PRODUCT_APPEND_CREATE
- MANUAL_BID
- AUTO_BID_SET
- AUTO_BID_STOP
- TRADE_PROCEED
- TRADE_DECLINE
- TRADE_CANCEL
- COMPLETION_REQUEST
- COMPLETION_CONFIRM
- COMPLETION_REJECT
- AUCTION_RELIST

규칙:
- 동일 user + scope + key + 동일 요청: 최초 성공 결과 재사용
- replay 응답에는 `Idempotency-Replayed: true`
- 동일 key를 다른 요청 내용에 재사용: `409 IDEMPOTENCY_KEY_REUSED`
- Idempotency-Key는 UUID 형식. 형식이 아니면 `400 VALIDATION_ERROR`
- requestHash = SHA-256(HTTP method + path variable이 포함된 경로 + 정규화한 JSON body). 같은 key로 다른 경매에 입찰하면 경로가 달라 `IDEMPOTENCY_KEY_REUSED`
- 서버는 성공한 요청의 requestHash와 HTTP status/body snapshot을 저장하고, replay 시 snapshot을 그대로 반환 (serverTime 등도 최초 응답 값)
- 기록 보관 기간은 24시간이며 이후 정리 배치가 삭제

처리 방식:
- 멱등 기록은 비즈니스 트랜잭션 안에서 **가장 먼저** INSERT하고, 비즈니스 처리가 끝나면 같은 트랜잭션에서 응답 snapshot을 채움
- 같은 key의 동시 요청은 UNIQUE index에서 앞선 트랜잭션이 끝날 때까지 대기
  - 앞선 요청이 커밋되면 duplicate key 오류가 나고, 새 트랜잭션에서 snapshot을 조회해 replay
  - 앞선 요청이 롤백되면 기록도 사라지므로 대기하던 요청이 그대로 실행
- 실패한 요청(4xx/5xx)은 롤백과 함께 기록도 사라지므로 같은 key로 재시도하면 다시 실행됨. 비즈니스 효과가 두 번 생기는 일은 없으며, 클라이언트는 4xx를 받으면 다음 사용자 액션에서 새 key를 만듦
- 멱등 기록 INSERT는 모든 도메인 락보다 먼저이므로 중복 요청은 도메인 락을 잡지 않은 채 대기함 ([락 규칙](backend/locking.md))

키가 필요 없는 API(같은 요청을 반복해도 결과가 같음): 경매 취소, 관심상품 PUT/DELETE, 알림 읽음 처리, PushSubscription 등록/삭제

### 공통 Error Response

```json
{
  "timestamp": "2026-10-03T04:30:00Z",
  "status": 409,
  "code": "AUCTION_ENDED",
  "message": "종료된 경매에는 입찰할 수 없습니다.",
  "path": "/api/v1/auctions/10/bids",
  "traceId": "optional",
  "fieldErrors": []
}
```

Validation 오류 예:

```json
{
  "timestamp": "2026-10-03T04:30:00Z",
  "status": 400,
  "code": "VALIDATION_ERROR",
  "message": "요청 값을 확인해주세요.",
  "path": "/api/v1/products",
  "fieldErrors": [
    {
      "field": "title",
      "code": "NOT_BLANK",
      "message": "제목은 필수입니다."
    }
  ]
}
```

## HTTP Status 기준

| Status | 의미 |
|---|---|
| 200 | 조회/수정/상태전이 성공 |
| 201 | Resource 생성 성공 |
| 204 | 반환 본문 없는 삭제/탈퇴 성공 |
| 400 | 형식/필드/가격단위 등 요청 자체가 잘못됨 |
| 401 | 인증 필요 또는 토큰 오류 |
| 403 | 인증은 됐으나 해당 행위 권한 없음 |
| 404 | Resource 없음 |
| 409 | 현재 상태/동시성/중복키 때문에 명령 수행 불가 |
| 503 | 락 대기 시간 초과 등 일시적으로 처리 불가. 같은 Idempotency-Key로 재시도 가능 |

## 주요 Error Code

| Code | HTTP | 의미 |
|---|---:|---|
| VALIDATION_ERROR | 400 | 일반 필드 검증 실패 |
| INVALID_PRICE_UNIT | 400 | 가격단위표에 맞지 않는 금액 |
| AMOUNT_LIMIT_EXCEEDED | 400 | 금액 상한(10,000,000원) 초과 |
| AUCTION_PERIOD_INVALID | 400 | 경매 기간 1시간~7일, 예약 시작 7일 이내 조건 위반 |
| IDEMPOTENCY_KEY_REQUIRED | 400 | 필수 Idempotency-Key 없음 |
| UNAUTHORIZED | 401 | 로그인 필요 |
| INVALID_TOKEN | 401 | JWT 오류/만료 |
| INVALID_CREDENTIALS | 401 | 로그인 정보 불일치 |
| ACCOUNT_WITHDRAWN | 403 | 탈퇴 처리된 계정 |
| USER_WITHDRAWAL_BLOCKED | 409 | 진행 중 상품/경매/입찰/거래 의무로 탈퇴 불가 |
| FORBIDDEN | 403 | 권한 없음 |
| SELF_BID_FORBIDDEN | 403 | 판매자 본인 입찰 |
| USER_RESTRICTED | 403 | 거래 참여 정지 중 입찰·AutoBid 설정·경매 생성 시도 |
| COMPLETION_SELF_CONFIRM_FORBIDDEN | 403 | 본인이 요청한 거래완료를 본인이 승인 |
| RESOURCE_NOT_FOUND | 404 | 대상 없음 |
| DUPLICATE_EMAIL | 409 | 이메일 중복 |
| DUPLICATE_NICKNAME | 409 | 닉네임 중복 |
| PRODUCT_LOCKED_AFTER_BID | 409 | 입찰 후 핵심 상품 수정 시도 |
| PRODUCT_LOCKED_AUCTION_STARTED | 409 | 논리적으로 시작된 경매가 있는 상품 수정 시도 |
| PRODUCT_DELETE_NOT_ALLOWED | 409 | SOLD 상품, 진행 중 경매·거래가 있는 상품 삭제 시도 |
| ACTIVE_AUCTION_ALREADY_EXISTS | 409 | 동일 상품 READY/OPEN 경매 존재 |
| AUCTION_NOT_OPEN | 409 | READY/CANCELED/ENDED 경매에 입찰 |
| AUCTION_ENDED | 409 | serverNow >= endAt |
| BID_AMOUNT_TOO_LOW | 409 | 최소 입찰가 미달 |
| ALREADY_LEADING | 409 | 현재 선두가 수동입찰로 자기 가격을 올리려 함 |
| DUPLICATE_BID_AMOUNT | 409 | 동일 경매 동일 가격 Bid 충돌 |
| AUTO_BID_MAX_TOO_LOW | 409 | 현재 상태에서 의미 있는 maxAmount 미달 |
| PRODUCT_IMAGE_LIMIT | 409 | 상품 이미지 최대 개수 초과 |
| PRODUCT_IMAGE_REQUIRED | 409 | 최소 1장의 상품 이미지가 필요 |
| AUCTION_RELIST_NOT_ALLOWED | 409 | 현재 경매/거래 상태에서 재경매 불가 |
| AUCTION_CANNOT_CANCEL | 409 | 입찰 발생 후 판매자 취소 시도 |
| TRADE_INVALID_STATE | 409 | 허용되지 않은 Trade 상태전이 |
| TRADE_RESPONSE_EXPIRED | 409 | 응답기한 종료 |
| TRADE_DEADLINE_PASSED | 409 | 거래 기한 또는 완료 응답 기한 종료 |
| IDEMPOTENCY_KEY_REUSED | 409 | 동일 key를 다른 요청에 재사용 |
| RESOURCE_BUSY | 503 | 락 대기 시간 초과. 재시도 가능 |

## 공통 User Summary

```json
{
  "id": 15,
  "nickname": "seller01",
  "trustScore": 4
}
```

## 공통 Region

```json
{
  "id": 11020,
  "regionCode": "11200",
  "sidoName": "서울특별시",
  "sigunguName": "성동구"
}
```

## Category Code
MVP:
- DIGITAL
- HOME_APPLIANCE
- FURNITURE
- LIVING_KITCHEN
- FASHION
- BEAUTY
- SPORTS_LEISURE
- HOBBY_GAME
- BOOK_MEDIA
- ETC

`GET /categories`로 Frontend에 제공하며 화면에서는 서버 응답 label을 사용합니다.
