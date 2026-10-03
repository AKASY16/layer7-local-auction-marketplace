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
```json
{
  "accessToken": "<jwt>",
  "tokenType": "Bearer",
  "expiresAt": "2026-10-03T06:30:00Z",
  "user": {
    "id": 15,
    "nickname": "layer7",
    "trustScore": 0
  }
}
```

Errors:
- 401 INVALID_CREDENTIALS
- 403 ACCOUNT_WITHDRAWN

---

## 2. User

### GET /users/me
현재 사용자 정보.

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

Response: `204`

### GET /users/me/products
내 등록 상품 목록.

Query:
- `status=ACTIVE|SOLD|DELETED` optional
- page / size

### GET /users/me/bids
내 실제 Bid 이력.

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
판매자만 가능. **해당 Product의 어떤 Auction에도 Bid가 한 건도 발생하지 않았을 때만** 핵심정보 수정 가능.

한 번이라도 Bid가 발생한 Product는 과거 경매 화면의 의미가 바뀌지 않도록 핵심정보를 계속 잠급니다. 재경매 전에 핵심 내용 자체를 바꿔야 한다면 새 Product로 등록합니다.

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

### POST /products/{productId}/images
판매자 전용. 입찰 전 이미지만 추가.

multipart `images`.

규칙:
- 기존 이미지 포함 총 10장 초과 불가
- 초과 시 `409 PRODUCT_IMAGE_LIMIT`

### DELETE /products/{productId}/images/{imageId}
판매자 전용. 입찰 전 이미지만 제거.
삭제 후 최소 1장 이상 남아야 하며, 마지막 이미지를 삭제하려 하면 `409 PRODUCT_IMAGE_REQUIRED`.

### PATCH /products/{productId}/images/order
판매자 전용. 입찰 전 순서변경.

Request:
```json
{
  "imageIds": [103, 101, 102]
}
```

`imageIds`는 현재 Product에 속한 전체 이미지 id를 중복 없이 정확히 한 번씩 포함해야 합니다.

### DELETE /products/{productId}
판매자 전용. Product를 `DELETED`로 전환.

READY/OPEN Auction이 존재하면 먼저 경매 취소가 필요합니다.

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
