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
- 동일 user + scope + key + 동일 요청: 최초 처리 결과 재사용
- replay 응답에는 `Idempotency-Replayed: true`
- 동일 key를 다른 요청 내용에 재사용: `409 IDEMPOTENCY_KEY_REUSED`
- 서버는 requestHash와 최초 HTTP status/body snapshot을 저장

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

## 주요 Error Code

| Code | HTTP | 의미 |
|---|---:|---|
| VALIDATION_ERROR | 400 | 일반 필드 검증 실패 |
| INVALID_PRICE_UNIT | 400 | 가격단위표에 맞지 않는 금액 |
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
