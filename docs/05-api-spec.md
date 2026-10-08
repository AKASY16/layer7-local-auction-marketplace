# API 명세 v1

Base URL: `/api/v1`

이 문서는 Frontend/Backend 간 계약의 기준입니다. 실제 구현 시 DTO/Controller 이름은 달라질 수 있지만 HTTP method, path, payload 의미, 상태코드와 비즈니스 규칙은 이 명세를 기준으로 합니다.

## API 문서 운영

마크다운 명세와 코드에서 자동 생성하는 Swagger 문서(springdoc-openapi)를 역할을 나눠 함께 씁니다.

| 문서 | 담는 것 | 기준이 되는 때 |
|---|---|---|
| 마크다운 (`docs/05-api-spec.md`, `docs/api/`) | 정책, 흐름, 상태 전이, 기한, 오류 코드의 의미 | 항상 |
| Swagger UI (`/swagger-ui`) | 엔드포인트별 요청·응답 필드, 상태 코드 | 구현된 API부터 |

- 구현 전에는 마크다운이 Frontend/Backend의 약속입니다. 프론트는 마크다운의 예시로 화면을 먼저 만들 수 있습니다.
- 구현된 API의 필드는 Swagger가 기준입니다. 마크다운 예시와 다르면 둘 중 맞는 쪽으로 같은 PR에서 맞춥니다.
- API를 추가·변경하는 PR은 마크다운 명세도 함께 고칩니다 (PR 템플릿 체크 항목).
- Swagger UI는 로컬·개발 환경에서만 열고 운영에서는 끕니다.
- springdoc-openapi는 첫 API를 구현하는 PR에서 의존성과 보안 예외 경로를 함께 추가합니다. Spring Boot 4에 맞는 3.x를 쓰고, 추가할 때 4.1과 호환되는 버전인지 확인합니다.

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

토큰 없이 호출할 수 있는 API는 다음과 같고, 그 밖의 API는 토큰이 없으면 `401 UNAUTHORIZED`입니다.
- `/auth/**`: 회원가입, 로그인, 토큰 갱신, 로그아웃
- `GET /regions`, `GET /categories`, `GET /bid-increment-policy`
- WebSocket 연결(`/ws`). 인증은 연결 뒤 STOMP `CONNECT` 프레임에서 합니다 ([Realtime](api/realtime.md))

Access Token과 Refresh Token을 함께 사용합니다. 경매는 마감 직전에 참여가 몰리는데, 그 순간 토큰이 만료되어 재로그인하느라 마감을 놓치는 일이 없도록 하기 위함입니다.

- Access Token: JWT, 유효기간 30분. Login/Refresh 응답 본문으로 전달하며 Frontend는 메모리에만 보관 (localStorage 저장 금지)
- Refresh Token: 서버가 생성한 256bit 임의 문자열, 유효기간 14일. `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` 쿠키로만 전달하며 서버는 SHA-256 해시만 저장
- `POST /auth/refresh`를 호출할 때마다 Refresh Token을 새로 발급(rotation)하고 이전 토큰은 교체 처리
- 이미 교체된 Refresh Token이 다시 오면 탈취로 보고, 같은 로그인에서 이어진 토큰 묶음(family)을 모두 폐기한 뒤 401. 단, 교체 후 10초 이내라면 여러 탭이 동시에 갱신한 경우로 보고 새 Access Token만 발급
- 로그아웃은 현재 family 폐기, 회원탈퇴는 그 사용자의 모든 Refresh Token 폐기
- Access Token은 만료 전에 폐기할 수 없으므로 쓰기 API는 요청마다 사용자 상태(ACTIVE)를 확인. 조회 API는 탈퇴 전에 발급된 토큰을 최대 30분까지 허용
- 쿠키를 사용하므로 Frontend와 API는 같은 사이트(등록 도메인)에 배포 ([Infra](08-infra.md))

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
- PRODUCT_IMAGE_ADD
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

키가 필요 없는 API(같은 요청을 반복해도 결과가 같음): 경매 취소, 관심상품 PUT/DELETE, 알림 읽음 처리, PushSubscription 등록/삭제. 업로드 URL 발급도 키를 쓰지 않으며, 중복 발급으로 남은 PENDING 업로드는 정리 배치가 삭제합니다.

### 공통 Error Response

```json
{
  "timestamp": "2026-10-03T04:30:00Z",
  "status": 409,
  "code": "AUCTION_ENDED",
  "message": "종료된 경매에는 입찰할 수 없습니다.",
  "path": "/api/v1/auctions/10/bids",
  "traceId": null,
  "fieldErrors": []
}
```

- 프론트는 `message`가 아니라 `code`로 분기합니다. `message`는 사용자에게 보여줄 한국어 문장이며 상황에 따라 더 구체적으로 바뀔 수 있습니다.
- `traceId`는 요청 추적을 도입하기 전까지 `null`입니다.
- `fieldErrors`는 오류가 없으면 빈 배열입니다.
- 인증 실패(401)·권한 없음(403)도 같은 형식으로 응답합니다.

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

- `fieldErrors[].code`는 검증 애노테이션 이름을 대문자 스네이크로 바꾼 값입니다. 예: `@NotBlank` → `NOT_BLANK`, `@Size` → `SIZE`, `@Positive` → `POSITIVE`
- 요청 본문(JSON)의 `field`는 필드 경로, 쿼리·경로 값의 `field`는 파라미터 이름입니다.
- JSON 문법이 틀리거나 값의 타입이 맞지 않아 본문을 읽지 못하면 `fieldErrors` 없이 `VALIDATION_ERROR`로 응답합니다.

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
| 405 | 지원하지 않는 HTTP 메서드 |
| 409 | 현재 상태/동시성/중복키 때문에 명령 수행 불가 |
| 415 | 지원하지 않는 Content-Type |
| 500 | 예상하지 못한 서버 오류. 내부 메시지는 응답에 담지 않음 |
| 503 | 락 대기 시간 초과 등 일시적으로 처리 불가. 같은 Idempotency-Key로 재시도 가능 |

## 주요 Error Code

백엔드의 `ErrorCode` enum과 1:1로 대응합니다. 코드를 추가·변경할 때는 이 표와 enum을 같은 PR에서 함께 고칩니다. 둘이 어긋나면 백엔드 테스트(`ErrorCodeSpecTest`)가 실패합니다.

| Code | HTTP | 의미 |
|---|---:|---|
| VALIDATION_ERROR | 400 | 일반 필드 검증 실패 |
| INVALID_PRICE_UNIT | 400 | 가격단위표에 맞지 않는 금액 |
| AMOUNT_LIMIT_EXCEEDED | 400 | 금액 상한(10,000,000원) 초과 |
| INVALID_UPLOAD | 400 | imageKey가 본인 업로드가 아니거나 만료·미업로드·조건 불일치 |
| AUCTION_PERIOD_INVALID | 400 | 경매 기간 1시간~7일, 예약 시작 7일 이내 조건 위반 |
| IDEMPOTENCY_KEY_REQUIRED | 400 | 필수 Idempotency-Key 없음 |
| UNAUTHORIZED | 401 | 로그인 필요 |
| INVALID_TOKEN | 401 | JWT 오류/만료 |
| INVALID_CREDENTIALS | 401 | 로그인 정보 불일치 |
| INVALID_REFRESH_TOKEN | 401 | Refresh Token 없음/만료/폐기/재사용 감지. 재로그인 필요 |
| ACCOUNT_WITHDRAWN | 403 | 탈퇴 처리된 계정 |
| USER_WITHDRAWAL_BLOCKED | 409 | 진행 중 상품/경매/입찰/거래 의무로 탈퇴 불가 |
| FORBIDDEN | 403 | 권한 없음 |
| SELF_BID_FORBIDDEN | 403 | 판매자 본인 입찰 |
| USER_RESTRICTED | 403 | 거래 참여 정지 중 입찰·AutoBid 설정·경매 생성 시도 |
| COMPLETION_SELF_CONFIRM_FORBIDDEN | 403 | 본인이 요청한 거래완료를 본인이 승인 |
| RESOURCE_NOT_FOUND | 404 | 대상 없음 |
| METHOD_NOT_ALLOWED | 405 | 지원하지 않는 HTTP 메서드 |
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
| PRODUCT_APPEND_LIMIT | 409 | 경매당 내용 추가 최대 개수(10건) 초과 |
| AUCTION_RELIST_NOT_ALLOWED | 409 | 현재 경매/거래 상태에서 재경매 불가 |
| AUCTION_CANNOT_CANCEL | 409 | 입찰 발생 후 판매자 취소 시도 |
| TRADE_INVALID_STATE | 409 | 허용되지 않은 Trade 상태전이 |
| TRADE_RESPONSE_EXPIRED | 409 | 응답기한 종료 |
| TRADE_DEADLINE_PASSED | 409 | 거래 기한 또는 완료 응답 기한 종료 |
| IDEMPOTENCY_KEY_REUSED | 409 | 동일 key를 다른 요청에 재사용 |
| UNSUPPORTED_MEDIA_TYPE | 415 | 지원하지 않는 Content-Type |
| INTERNAL_ERROR | 500 | 예상하지 못한 서버 오류 |
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
