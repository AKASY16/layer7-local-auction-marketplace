# Auth / User / Product API

## 1. Auth

### POST /auth/signup
회원가입.

Request:
```json
{
  "email": "user@example.com",
  "password": "password",
  "nickname": "layer7",
  "regionId": 11020
}
```

Response `201`:
```json
{
  "id": 15,
  "email": "user@example.com",
  "nickname": "layer7",
  "trustScore": 0,
  "status": "ACTIVE",
  "region": {
    "id": 11020,
    "regionCode": "11200",
    "sidoName": "서울특별시",
    "sigunguName": "성동구"
  }
}
```

Errors:
- 400 VALIDATION_ERROR
- 404 RESOURCE_NOT_FOUND(region)
- 409 DUPLICATE_EMAIL
- 409 DUPLICATE_NICKNAME

### POST /auth/login

Request:
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Response `200`:
```http
Set-Cookie: refresh_token=<opaque>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=1209600
```
```json
{
  "accessToken": "<jwt>",
  "tokenType": "Bearer",
  "expiresAt": "2026-10-03T05:00:00Z",
  "user": {
    "id": 15,
    "nickname": "layer7",
    "trustScore": 0
  }
}
```

- `expiresAt`은 Access Token 만료 시각 (발급 후 30분)
- 로그인할 때마다 새 Refresh Token family를 시작

Errors:
- 401 INVALID_CREDENTIALS
- 403 ACCOUNT_WITHDRAWN

### POST /auth/refresh
Refresh Token 쿠키로 새 Access Token을 발급합니다. 요청 본문은 없습니다.

- 정상: 이전 Refresh Token을 교체 처리하고 새 Refresh Token 쿠키와 Access Token을 반환
- 교체된 지 10초 이내의 토큰: 여러 탭의 동시 갱신으로 보고 Access Token만 반환 (쿠키는 이미 먼저 응답한 요청이 갱신함)
- 그보다 오래전에 교체된 토큰: 탈취로 보고 family 전체 폐기 후 `401 INVALID_REFRESH_TOKEN`
- 교체 처리는 `rotatedAt IS NULL` 조건의 UPDATE로 한 번만 성공하므로, 같은 토큰의 동시 요청 중 하나만 새 Refresh Token을 받음

Response `200`: Login 응답과 같은 형태

Errors:
- 401 INVALID_REFRESH_TOKEN (없음, 만료, 폐기, 재사용, 탈퇴한 사용자)

### POST /auth/logout
현재 Refresh Token의 family를 폐기하고 쿠키를 삭제합니다. 쿠키가 없거나 이미 폐기됐어도 `204`.

로그아웃 UI는 PushSubscription을 먼저 삭제한 뒤 이 API를 호출합니다.

Response: `204`

---

## 2. User

### GET /users/me
현재 사용자 정보.

거래 참여 정지 중이면 `tradingRestriction`에 사유와 해제 시각을, 아니면 `null`을 반환합니다.

```json
{
  "tradingRestriction": {
    "reason": "CONSECUTIVE_FAILURES",
    "endsAt": "2026-10-10T04:30:00Z"
  }
}
```

### PATCH /users/me/region
지역 변경.

Request:
```json
{
  "regionId": 11020
}
```

Response `200`: 갱신된 User.

기존 Product의 region은 생성 당시 지역 snapshot을 유지합니다.

### DELETE /users/me
회원탈퇴. 물리삭제하지 않고 `WITHDRAWN`.

탈퇴 전 서버가 다음 활성 의무를 검사합니다.
- ACTIVE Product 보유
- 판매자로서 READY/OPEN Auction 보유
- OPEN Auction에서 현재 leadingBid의 bidder
- OPEN Auction의 ACTIVE AutoBid 보유
- AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED Trade의 당사자

하나라도 존재하면 `409 USER_WITHDRAWAL_BLOCKED`.
단순 과거 Bid 이력만 있고 현재 선두/AutoBid/Trade 의무가 없다면 탈퇴 가능.

검사는 User 락을 잡은 뒤 수행해 같은 사용자의 동시 입찰과 직렬화합니다 ([락 규칙](../backend/locking.md#입찰과-회원탈퇴)).

탈퇴 시 그 사용자의 모든 Refresh Token을 폐기하고 쿠키를 삭제합니다. 이미 발급된 Access Token은 최대 30분 남을 수 있지만 쓰기 API는 요청마다 사용자 상태를 확인하므로 사용할 수 없습니다.

Response: `204`

### GET /users/me/products
내 등록 상품 목록.

Query:
- `status=ACTIVE|SOLD|DELETED` optional
- page / size

### GET /users/me/auctions
내가 판매자로 생성한 Auction 목록.

Query:
- `status` optional
- page / size

### GET /users/me/bids
내 실제 Bid 이력.

### GET /users/me/auto-bids
내 AutoBid 설정 목록.

Query:
- `status=ACTIVE|STOPPED|EXHAUSTED` optional
- page / size

다른 사용자의 maxAmount는 어떤 경우에도 반환하지 않습니다.

### GET /users/me/trades
내 거래 목록.

Query:
- `role=BUYER|SELLER` optional
- `status` optional
- page / size

### GET /users/me/trust-history
내 신뢰점수 변경 이력.

### GET /regions?query=성동
지역 검색.

### GET /categories
Category code/label 목록.

---

## 3. Product

### ProductCondition
- UNOPENED
- LIKE_NEW
- GOOD
- FAIR
- DAMAGED
- NEEDS_REPAIR

### ProductStatus
- ACTIVE
- SOLD
- DELETED

### POST /products
인증 필요. 상품과 초기 이미지를 함께 등록.

`multipart/form-data`

Part `product`:
```json
{
  "category": "DIGITAL",
  "title": "중고 키보드",
  "description": "사용하던 키보드 판매합니다.",
  "condition": "GOOD",
  "conditionDescription": "키캡에 약간의 사용감이 있고 정상 작동합니다."
}
```

Part `images`:
- 1~10개
- JPEG / PNG / WebP
- 파일당 최대 10MB

Product.region은 현재 User.region을 생성 시점에 snapshot으로 저장합니다.

Response `201`:
```json
{
  "id": 30,
  "seller": {
    "id": 15,
    "nickname": "layer7",
    "trustScore": 0
  },
  "region": {
    "id": 11020,
    "regionCode": "11200",
    "sidoName": "서울특별시",
    "sigunguName": "성동구"
  },
  "category": "DIGITAL",
  "title": "중고 키보드",
  "description": "사용하던 키보드 판매합니다.",
  "condition": "GOOD",
  "conditionDescription": "키캡에 약간의 사용감이 있고 정상 작동합니다.",
  "status": "ACTIVE",
  "images": [
    {
      "id": 101,
      "url": "https://...",
      "sortOrder": 0
    }
  ],
  "createdAt": "2026-10-03T04:30:00Z",
  "updatedAt": "2026-10-03T04:30:00Z"
}
```

### GET /products/{productId}
상품 정보 조회.

삭제(DELETED) 상품은 거래 이력 당사자/소유자 등 허용된 경우를 제외하고 일반 목록에서는 노출하지 않습니다.

### PATCH /products/{productId}
판매자만 가능. 다음 조건을 모두 만족할 때만 핵심정보 수정 가능.
- 해당 Product의 어떤 Auction에도 Bid가 한 건도 발생하지 않음
- 논리적으로 시작된 Auction이 없음 (OPEN이거나, READY이면서 startAt이 지난 경매)

한 번이라도 Bid가 발생한 Product는 과거 경매 화면의 의미가 바뀌지 않도록 핵심정보를 계속 잠급니다. 재경매 전에 핵심 내용 자체를 바꿔야 한다면 새 Product로 등록합니다.

OPEN 경매는 입찰이 없어도 수정할 수 없습니다. 구매자가 보고 있는 진행 중 경매의 내용이 바뀌지 않게 하기 위함이며, 고치려면 경매를 취소한 뒤 수정하고 새 경매를 등록합니다. 판정은 Product 락과 READY/OPEN Auction 락을 잡은 뒤 수행합니다 ([락 규칙](../backend/locking.md#상품-수정)).

Request:
```json
{
  "category": "DIGITAL",
  "title": "수정된 제목",
  "description": "수정된 설명",
  "condition": "FAIR",
  "conditionDescription": "생활기스가 있습니다."
}
```

Errors:
- 403 FORBIDDEN
- 409 PRODUCT_LOCKED_AFTER_BID
- 409 PRODUCT_LOCKED_AUCTION_STARTED

### POST /products/{productId}/images
판매자 전용. 핵심정보 수정과 같은 조건에서만 이미지 추가.

multipart `images`.

규칙:
- 기존 이미지 포함 총 10장 초과 불가
- 초과 시 `409 PRODUCT_IMAGE_LIMIT`

### DELETE /products/{productId}/images/{imageId}
판매자 전용. 핵심정보 수정과 같은 조건에서만 이미지 제거.
삭제 후 최소 1장 이상 남아야 하며, 마지막 이미지를 삭제하려 하면 `409 PRODUCT_IMAGE_REQUIRED`.

### PATCH /products/{productId}/images/order
판매자 전용. 핵심정보 수정과 같은 조건에서만 순서변경.

Request:
```json
{
  "imageIds": [103, 101, 102]
}
```

`imageIds`는 현재 Product에 속한 전체 이미지 id를 중복 없이 정확히 한 번씩 포함해야 합니다.

### DELETE /products/{productId}
판매자 전용. Product를 `DELETED`로 전환.

- ACTIVE 상품만 삭제 가능. SOLD 상품은 거래 기록 보존을 위해 삭제하지 않음
- READY/OPEN Auction이 존재하면 먼저 경매 취소가 필요
- AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED Trade가 있으면 삭제 불가
- 조건을 만족하지 않으면 `409 PRODUCT_DELETE_NOT_ALLOWED`

Response: `204`

---

## 4. Favorite

### PUT /products/{productId}/favorite
관심상품 등록. 동일 요청 반복 시에도 결과는 동일.

Response `200`:
```json
{
  "productId": 30,
  "favorited": true
}
```

### DELETE /products/{productId}/favorite
관심상품 해제.

Response `200`:
```json
{
  "productId": 30,
  "favorited": false
}
```

### GET /users/me/favorites
관심상품 목록.
