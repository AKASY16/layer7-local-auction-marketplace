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

### 현재 구현 범위 — Sprint 1 (#26)

- 회원가입, 로그인, Access Token 인증, 현재 사용자 조회를 구현한다.
- Access Token은 JWT이며 유효기간은 30분이다.
- 이번 로그인 응답은 Access Token만 반환한다.
- Refresh Token 쿠키 발급과 refresh/logout API는 후속 스프린트에서 구현한다.
- 아래 Refresh Token 관련 설명은 후속 구현을 포함한 전체 명세이다.

### 입력 검증

- 이메일은 필수이며 이메일 형식, 최대 320자이다.
- 닉네임은 필수이며 최대 50자이다.
- 비밀번호는 필수이며 UTF-8 기준 최대 72바이트이다.
- 로그인 요청에도 동일한 이메일·비밀번호 형식 검증을 적용한다.
- regionId는 필수 양수이며 실제 regions 테이블에 존재해야 한다.
- 형식 검증 실패는 400 VALIDATION_ERROR를 반환한다.
- 존재하지 않는 지역은 404 RESOURCE_NOT_FOUND를 반환한다.
- 이메일·닉네임 중복은 동시 가입 요청에서도 각각
  409 DUPLICATE_EMAIL, 409 DUPLICATE_NICKNAME으로 반환한다.

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

Response `200` 예시:

```json
{
  "id": 15,
  "email": "user@example.com",
  "nickname": "layer7",
  "trustScore": 0,
  "status": "ACTIVE",
  "region": {
    "id": 4,
    "regionCode": "11200",
    "sidoName": "서울특별시",
    "sigunguName": "성동구"
  },
  "tradingRestriction": null
}
```

- 회원 ID는 요청 입력이 아니라 검증된 JWT에서 가져온다.
- 활성 거래 정지는 다음 조건으로 판정한다:
  liftedAt이 없고, startsAt이 현재 시각 이하이며,
  endsAt이 없거나 현재 시각보다 미래이다.
- 활성 정지가 여러 개라면 종료 시각이 없는 기록을 우선하고,
  기간제 기록은 가장 늦게 끝나는 기록을 반환한다.
- 탈퇴 전에 발급한 유효한 토큰으로 조회하는 것은 만료까지 허용한다.

Errors:
- 401 UNAUTHORIZED: 인증 헤더 없음
- 401 INVALID_TOKEN: 토큰 형식·서명·발급자·만료 검증 실패,
  또는 토큰의 회원이 존재하지 않음

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

회원가입에서 선택할 지역 검색. 인증 없이 호출할 수 있습니다.

Query:
- `query`: 선택, 최대 100자
  - 시도명 또는 시군구명에 대한 부분 검색
  - 앞뒤 공백 제거
  - 생략하거나 빈 문자열·공백이면 전체 지역 조회
- `page`: 기본 0, 최소 0
- `size`: 기본 20, 최소 1, 최대 50

시도명 → 시군구명 → 지역 코드 오름차순으로 정렬합니다.
검색 결과가 없으면 `200`과 빈 `content`를 반환합니다.

Response `200` 예시:
```json
{
  "content": [
    {
      "id": 4,
      "regionCode": "11200",
      "sidoName": "서울특별시",
      "sigunguName": "성동구"
    }
  ],
  "page": 0,
  "size": 20,
  "totalElements": 1,
  "totalPages": 1
}
```

`id`는 DB가 생성한 식별자이며 공식 지역 코드와 별개입니다.

Errors:
- 400 VALIDATION_ERROR

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

### 이미지 업로드

상품 이미지는 Presigned URL로 클라이언트가 Object Storage에 직접 업로드합니다. 백엔드는 파일 본문을 받지 않고 objectKey만 등록합니다.

```text
1. POST /uploads/product-images 로 업로드 URL 발급
2. 클라이언트가 각 uploadUrl에 파일을 PUT
3. POST /products 또는 POST /products/{productId}/images 에 imageKeys를 담아 등록
```

### POST /uploads/product-images
인증 필요. 업로드 URL 발급.

Request:
```json
{
  "files": [
    { "contentType": "image/jpeg", "size": 2450000 }
  ]
}
```

- 1~10개
- contentType: `image/jpeg` / `image/png` / `image/webp`
- size: 파일당 10MB 이하
- 서버가 objectKey(`uploads/{uuid}`)를 생성하고 PENDING 업로드 기록을 남김. 클라이언트가 key를 정하지 않음
- URL 유효기간 10분, 서명에 Content-Type 포함

Response `201`:
```json
{
  "uploads": [
    {
      "objectKey": "uploads/6f1c2a9e-...",
      "uploadUrl": "https://...",
      "expiresAt": "2026-10-03T04:40:00Z",
      "headers": { "Content-Type": "image/jpeg" }
    }
  ]
}
```

등록 시 검증:
- 각 imageKey가 요청자 본인의 PENDING 업로드이고 발급 후 24시간 이내
- Object Storage에 객체가 실제로 있고 크기와 Content-Type이 발급 조건과 일치 (HEAD 요청으로 확인)
- 하나라도 맞지 않으면 전체 거절 `400 INVALID_UPLOAD`
- 업로드 기록은 `status = PENDING` 조건의 UPDATE로 ATTACHED 처리하므로 같은 key를 두 상품에 붙일 수 없음. `product_images.objectKey` UNIQUE가 최종 방어선
- 파일 내용이 실제 이미지인지는 검증하지 않음. 썸네일 생성을 도입할 때 함께 검증

### POST /products
인증 필요. 상품과 초기 이미지를 함께 등록.
Header: `Idempotency-Key`

Request:
```json
{
  "category": "DIGITAL",
  "title": "중고 키보드",
  "description": "사용하던 키보드 판매합니다.",
  "condition": "GOOD",
  "conditionDescription": "키캡에 약간의 사용감이 있고 정상 작동합니다.",
  "imageKeys": ["uploads/6f1c2a9e-...", "uploads/0b7d41c3-..."]
}
```

- imageKeys 1~10개, 배열 순서가 sortOrder
- Product.region은 현재 User.region을 생성 시점에 snapshot으로 저장합니다.

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
Header: `Idempotency-Key`

Request:
```json
{
  "imageKeys": ["uploads/9a2e..."]
}
```

규칙:
- 기존 이미지 포함 총 10장 초과 불가
- 초과 시 `409 PRODUCT_IMAGE_LIMIT`
- imageKey 검증은 [이미지 업로드](#이미지-업로드)와 동일

### DELETE /products/{productId}/images/{imageId}
판매자 전용. 핵심정보 수정과 같은 조건에서만 이미지 제거.
ProductImage row를 삭제하고 업로드 기록을 DETACHED로 바꾸며, 실제 객체는 정리 배치가 삭제합니다.
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
