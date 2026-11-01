# Auction / Bid / AutoBid API

> 2026-10-29: 현재 구현은 경매 목록과 수동입찰입니다. P1 필수는 경매 생성/상세(#64), 입찰 이력(#65), 종료·낙찰(#47)이며 AutoBid·재경매·ProductAppend는 후순위입니다. 아래 미구현 응답 예시를 현재 동작으로 간주하지 않습니다. 적용 범위는 [요구사항](../02-requirements.md)을 따릅니다.

## 1. Auction

### POST /products/{productId}/auctions
판매자 전용.
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)

Request:
```json
{
  "startPrice": 9000,
  "startAt": null,
  "endAt": "2026-10-04T04:30:00Z"
}
```

- `startAt = null`: 즉시 시작. Backend가 serverNow를 startAt으로 사용하고 OPEN으로 생성
- 미래 startAt: READY
- 경매 기간(`endAt - effective startAt`)은 1시간 이상 7일 이하, startAt은 serverNow + 7일 이내 (`400 AUCTION_PERIOD_INVALID`)
- startPrice는 유효 가격단위이며 10,000,000원 이하 (`400 AMOUNT_LIMIT_EXCEEDED`)
- Product 소유자이며 Product.status = ACTIVE
- 판매자가 거래 참여 정지 상태가 아님 (`403 USER_RESTRICTED`)
- 동일 Product에 READY/OPEN Auction이 이미 있으면 409
- `startAt = null`이면 즉시 시작
- `startAt`을 명시했다면 serverNow보다 미래여야 함

Response `201`:
```json
{
  "id": 40,
  "productId": 30,
  "status": "OPEN",
  "finalized": false,
  "version": 0,
  "startPrice": 9000,
  "currentPrice": 9000,
  "bidCount": 0,
  "leadingBid": null,
  "winningBid": null,
  "startAt": "2026-10-03T04:30:00Z",
  "endAt": "2026-10-04T04:30:00Z",
  "relistedFromAuctionId": null,
  "serverTime": "2026-10-03T04:30:00Z"
}
```

### GET /auctions
경매 탐색. 인증 없이 호출할 수 있습니다.

Query:
- `regionId` optional
- `category` optional
- `keyword` optional, 최대 100자
  - 상품 제목 부분 검색. `%`·`_`도 글자 그대로 찾음
  - 앞뒤 공백 제거. 비어 있으면 조건 없음
- `status=READY|OPEN|ENDED` optional. 논리 상태 기준
  - 그 밖의 값(`CANCELED` 포함)은 `400 VALIDATION_ERROR`
  - 생략하면 상태로 거르지 않음 (취소된 경매도 포함)
- page / size: [페이지](../05-api-spec.md#페이지) 공통 규칙 (기본 0 / 20, 최대 50)

논리 상태 조회 조건:
- READY: `status = READY AND startAt > now`
- OPEN: `status IN (READY, OPEN) AND startAt <= now AND endAt > now`
- ENDED: `status = ENDED OR (status IN (READY, OPEN) AND endAt <= now)`

기본 정렬: 최신 등록순 (등록 시각이 같으면 id가 큰 순). Frontend 요구에 따라 종료임박순을 추가할 수 있음.

지역·카테고리·상태 필터는 auctions 테이블의 복사된 regionId/category로 처리해 products 조인 없이 인덱스를 탑니다. keyword는 MVP에서 상품 제목 LIKE 검색이며, 부하 테스트에서 병목으로 확인되면 FULLTEXT 검색으로 바꿉니다 ([ERD](../backend/erd.md#auctions)).

Item:
```json
{
  "auctionId": 40,
  "status": "OPEN",
  "finalized": false,
  "currentPrice": 9000,
  "startAt": "2026-10-03T04:30:00Z",
  "endAt": "2026-10-04T04:30:00Z",
  "product": {
    "id": 30,
    "title": "중고 키보드",
    "category": "DIGITAL",
    "condition": "GOOD",
    "thumbnailUrl": "https://...",
    "region": {
      "id": 11020,
      "sigunguName": "성동구"
    }
  }
}
```

응답은 [페이지](../05-api-spec.md#페이지) 공통 형식이고 `content`에 Item이 들어갑니다.

- `status`는 서버 시각 기준 논리 상태, `finalized`는 저장 status가 ENDED·CANCELED인지 여부 ([상태 모델](../backend/auction-state.md))
- 현재 구현의 `thumbnailUrl`은 `null`. P1의 최초 이미지 등록(#63) 이후에는 등록된 첫 이미지 URL을 반환해 표시하며 썸네일 변환 기능은 요구하지 않음

Errors:
- 400 VALIDATION_ERROR

### GET /auctions/{auctionId}
경매 상세. 인증 없이 호출할 수 있습니다.

Response `200` 주요 필드:
```json
{
  "id": 40,
  "status": "OPEN",
  "finalized": false,
  "version": 6,
  "startPrice": 9000,
  "currentPrice": 10000,
  "nextBidAmount": 10500,
  "bidCount": 3,
  "startAt": "2026-10-03T04:30:00Z",
  "endAt": "2026-10-04T04:30:00Z",
  "serverTime": "2026-10-03T05:00:00Z",
  "leadingBid": {
    "id": 300,
    "amount": 10000,
    "bidder": {
      "id": 21,
      "nickname": "buyer01"
    }
  },
  "winningBid": null,
  "relistedFromAuctionId": null,
  "product": {},
  "appends": []
}
```

다른 사용자의 AutoBid.maxAmount는 절대 노출하지 않습니다.

`status`는 서버시간 기준 논리 상태입니다 ([상태와 finalized](../05-api-spec.md#상태와-finalized)).
- Scheduler 반영이 늦어 저장 status가 잠시 OPEN이어도 endAt이 지났다면 `status=ENDED`, `finalized=false`, `nextBidAmount=null`로 반환
- startAt이 지났는데 저장 status가 READY로 남아 있으면 `status=OPEN`으로 반환하고 입찰을 받음
- 입찰 가능 여부는 `status == OPEN`으로 판단하며 별도 `biddingOpen` 필드는 두지 않음
- `ENDED + finalized=false`는 집계 중이며 winningBid는 아직 null. 낙찰 예정자는 leadingBid로 표시 가능
- `version`은 Auction row가 바뀔 때마다 증가하는 값으로, 실시간 이벤트의 순서 판단에 사용 ([Realtime](realtime.md#공개-auction-topic))
- `appends`는 같은 Product의 모든 경매에서 등록한 내용 추가를 시간순으로 담고, 항목마다 `auctionId`를 포함해 어느 경매에서 고지했는지 보여줌

### POST /auctions/{auctionId}/cancel
판매자 전용. 판정은 논리 상태 기준.
- READY: 가능
- OPEN: Bid 0건일 때만 가능
- 이미 CANCELED이면 현재 상태를 그대로 반환하여 자연스럽게 멱등 처리

Response `200`: Auction 상태.

### POST /auctions/{auctionId}/relist
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)

기존 Auction은 변경하지 않고 동일 Product에 새 Auction 생성.

허용 조건:
- 원 Auction이 finalized ENDED (유찰 여부는 winningBid로 판단하며 Trade 유무만으로 판단하지 않음)
- Product.status = ACTIVE
- 유찰(finalized ENDED, winningBid == null)이면 허용
- 아래 Trade 기반 재경매 규칙은 후순위 도입 후 적용. 이번 P1에서 Trade가 없다는 사실만으로 유찰로 판단하지 않음
- Trade가 있으면 finalized 상태가 DECLINED / NO_RESPONSE / CANCELED / EXPIRED일 때만 허용
- AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED이면 불가

불가 시 `409 AUCTION_RELIST_NOT_ALLOWED`. 판매자가 거래 참여 정지 중이면 `403 USER_RESTRICTED`. 기간과 금액 제한은 경매 생성과 같습니다.

Request:
```json
{
  "startPrice": 9000,
  "startAt": null,
  "endAt": "2026-10-05T04:30:00Z"
}
```

Response `201`: 새 Auction. `relistedFromAuctionId`는 기존 id.

---

## 2. BidIncrement Policy API

### GET /bid-increment-policy
인증 불필요. 서비스 공통 가격단위표 전체.

Response:
```json
{
  "minAmount": 100,
  "maxAmount": 10000000,
  "bands": [
    { "from": 100, "to": 9999, "unit": 100 },
    { "from": 10000, "to": 49999, "unit": 500 },
    { "from": 50000, "to": 99999, "unit": 1000 },
    { "from": 100000, "to": 499999, "unit": 5000 },
    { "from": 500000, "to": 999999, "unit": 10000 },
    { "from": 1000000, "to": 10000000, "unit": 20000 }
  ]
}
```

Frontend는 이 표로 시작가·입찰가·maxAmount가 유효 금액인지 입력 즉시 검증하고, 표를 코드에 하드코딩하지 않습니다. 정책이 바뀌면 이 응답만 바뀝니다. 최종 검증은 Backend가 수행합니다.

### GET /auctions/{auctionId}/bid-policy
인증 필요. 입찰 금액을 입력할 때 쓰는 조회입니다.

Response:
```json
{
  "currentPrice": 9900,
  "hasBid": true,
  "minimumBidAmount": 10000,
  "minimumBidUnit": 500,
  "serverTime": "2026-10-03T05:00:00Z"
}
```

Bid가 0건이면 `minimumBidAmount = startPrice`.

`minimumBidUnit`은 minimumBidAmount가 속한 구간의 단위입니다. 현재가 구간의 단위가 아니므로, 위 예시처럼 9,900원에서는 다음 금액부터 500원 단위가 적용됩니다. 최소 입찰가보다 높은 임의 금액의 유효성은 가격단위표 전체로 판단합니다.

Frontend 편의를 위한 조회이며 최종 검증은 Bid 요청 Transaction 안에서 다시 수행합니다.
논리적으로 입찰 불가능한 상태면 `409 AUCTION_NOT_OPEN` 또는 `409 AUCTION_ENDED`를 반환합니다.

---

## 3. Manual Bid

### POST /auctions/{auctionId}/bids
인증 필요.
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)

Request:
```json
{
  "amount": 10000
}
```

검증:
- 논리 상태 OPEN: 저장 status가 READY/OPEN이고 `startAt <= serverNow < endAt`. 저장값이 READY면 이 트랜잭션에서 OPEN으로 전이
- 판매자 본인 아님
- 현재 선두 아님 (`409 ALREADY_LEADING`)
- 입찰자가 거래 참여 정지 상태가 아님 (`403 USER_RESTRICTED`)
- 유효 가격단위
- 10,000,000원 이하 (`400 AMOUNT_LIMIT_EXCEEDED`)
- Bid 0건: amount >= startPrice
- Bid 존재: amount >= nextValidAmount(currentPrice)

Response `201`:
```json
{
  "acceptedBid": {
    "id": 301,
    "type": "MANUAL",
    "amount": 10000,
    "createdAt": "2026-10-03T05:00:00Z"
  },
  "auction": {
    "id": 40,
    "status": "OPEN",
    "version": 8,
    "currentPrice": 10500,
    "nextBidAmount": 11000,
    "bidCount": 5,
    "leadingBidder": {
      "id": 22,
      "nickname": "autoUser"
    },
    "currentUserLeading": false,
    "endAt": "2026-10-04T04:30:00Z",
    "serverTime": "2026-10-03T05:00:00Z"
  },
  "resolution": "OUTBID_BY_AUTO_BID"
}
```

`resolution`:
- LEADING
- OUTBID_BY_AUTO_BID

수동 Bid가 정상 성립한 뒤 기존 AutoBid가 즉시 반응한 경우에도 HTTP 요청 자체는 성공입니다. 최종 선두 여부를 resolution으로 전달합니다.

경쟁 판정과 저장되는 Bid는 [경매 정책의 AutoBid 경쟁 처리](../03-auction-policy.md#autobid-경쟁-처리)를 따릅니다.

입찰 금액이 현재 선두의 AutoBid 상한과 정확히 같으면 동액 선두 우선 규칙에 따라 선두가 그 금액으로 응답하고, 요청자의 Bid는 저장되지 않습니다. 생성된 resource가 없으므로 이 경우는 `200`과 함께 `acceptedBid: null`, `resolution: OUTBID_BY_AUTO_BID`를 반환합니다.

금액 상한에 도달해 다음 입찰가가 없으면(현재가 10,000,000원) `nextBidAmount`는 `null`이고, 이후 입찰은 `400 AMOUNT_LIMIT_EXCEEDED`로 거절합니다.

Errors (위에서부터 먼저 확인):
- 404 RESOURCE_NOT_FOUND: 없는 경매
- 409 AUCTION_ENDED: 논리 상태가 ENDED (`now >= endAt`)
- 409 AUCTION_NOT_OPEN: 시작 전이거나 취소된 경매
- 403 SELF_BID_FORBIDDEN: 판매자 본인
- 409 ALREADY_LEADING: 현재 선두
- 403 ACCOUNT_WITHDRAWN: 탈퇴한 회원 (탈퇴 전에 발급한 토큰으로 요청한 경우)
- 403 USER_RESTRICTED: 거래 참여 정지 중
- 400 AMOUNT_LIMIT_EXCEEDED: 10,000,000원 초과, 또는 현재가가 상한이라 더 입찰할 수 없음
- 400 INVALID_PRICE_UNIT: 가격단위표에 맞지 않는 금액
- 409 BID_AMOUNT_TOO_LOW: 최소 입찰가 미만. `message`에 최소 입찰가를 담음 (예: "최소 입찰가는 10,500원입니다.")
- 503 RESOURCE_BUSY: 경매 락 대기 시간 초과. 같은 요청을 다시 보내면 됨

### 현재 구현 범위 — Sprint 1 (#27)

- AutoBid가 아직 없어 `resolution`은 항상 `LEADING`이고, `acceptedBid: null`인 `200` 응답은 없습니다.
- P1에서는 HTTP 요청 멱등 기능 자체를 미룹니다. `Idempotency-Key`는 필수가 아니고 전달되어도 검증·중복 처리·응답 재사용에 사용하지 않습니다. 종료 처리(#47)의 중복 방지는 별도로 필수입니다.

### GET /auctions/{auctionId}/bids
공개 Bid 이력. 인증 없이 호출할 수 있습니다.

Query:
- page / size
- 기본 정렬: id DESC (같은 트랜잭션에서 저장된 패자·승자 Bid의 순서를 보존)

다른 사용자의 AutoBid 설정 상한은 노출하지 않고 실제 성립한 Bid만 반환.
`bidCount`는 이 API에 나타나는 **실제 Bid row 개수**이며 AutoBid 내부의 가상 중간 상승단계는 포함하지 않습니다.

---

## 4. AutoBid

### GET /auctions/{auctionId}/auto-bid/me
인증 필요. 해당 사용자의 AutoBid 설정만 조회.

없으면 `404 RESOURCE_NOT_FOUND`.

Response:
```json
{
  "id": 501,
  "auctionId": 40,
  "maxAmount": 100000,
  "status": "ACTIVE",
  "currentUserLeading": true
}
```

### PUT /auctions/{auctionId}/auto-bid
신규 설정 또는 기존 maxAmount 변경/재활성화.
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)

AutoBid는 저장만 해두는 예약값이 아니라 **설정/변경 요청이 성공한 Transaction 안에서 즉시 경매 경쟁에 참여**합니다.

Bid가 0건인 경매에서 첫 AutoBid를 설정하면:
- maxAmount >= startPrice 검증
- startPrice 금액의 실제 `AUTO Bid`를 생성
- 해당 사용자가 leadingBidder가 됨
- 이 Bid가 생긴 순간부터 판매자의 OPEN 경매 취소는 불가

Request:
```json
{
  "maxAmount": 100000
}
```

검증:
- 논리 상태 OPEN (수동입찰과 동일)
- 판매자 본인 금지
- 요청자가 거래 참여 정지 상태가 아님 (`403 USER_RESTRICTED`)
- maxAmount 유효 가격단위이며 10,000,000원 이하 (`400 AMOUNT_LIMIT_EXCEEDED`)
- Bid 0건이면 maxAmount >= startPrice
- 현재 사용자가 leader라면 maxAmount >= currentPrice
- leader가 아니라면 maxAmount >= nextValidAmount(currentPrice)

경쟁 계산:
- leader 본인의 설정·변경·재활성화는 경쟁 없이 maxAmount만 갱신
- leader가 아니면 요청한 maxAmount와 현재 leader의 상한(ACTIVE AutoBid의 maxAmount, 없으면 currentPrice)을 비교
- 요청 maxAmount가 더 크면 요청자가 선두, 같거나 작으면 기존 leader 유지 (동액 선두 우선)
- STOPPED/EXHAUSTED → ACTIVE 재활성화도 같은 규칙으로 경쟁
- 현재 leader가 거래 참여 정지 상태면 그 leader의 AutoBid를 이 트랜잭션에서 STOPPED로 바꾸고, leader 상한을 currentPrice로 취급 (수동입찰도 동일)
- 저장되는 Bid는 [경매 정책의 Bid 저장 규칙](../03-auction-policy.md#bid-저장-규칙)을 따름

Response `200`:
```json
{
  "autoBid": {
    "id": 501,
    "maxAmount": 100000,
    "status": "ACTIVE"
  },
  "auction": {
    "id": 40,
    "version": 9,
    "currentPrice": 81000,
    "nextBidAmount": 82000,
    "leadingBidder": {
      "id": 15,
      "nickname": "layer7"
    },
    "currentUserLeading": true,
    "serverTime": "2026-10-03T05:00:00Z"
  },
  "resolution": "LEADING"
}
```

`resolution`:
- LEADING: 처리 후 요청자가 선두
- OUTBID_BY_AUTO_BID: 기존 leader가 이겨 요청자의 AutoBid는 `EXHAUSTED`로 저장됨

설정 직후 바로 지는 경우에도 HTTP 요청 자체는 성공이며, 결과를 resolution과 `autoBid.status`로 전달합니다.

### DELETE /auctions/{auctionId}/auto-bid
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)

AutoBid를 삭제하지 않고 `STOPPED`로 전환. 이미 성립한 Bid에는 영향 없음. 거래 참여 정지 중에도 중지는 가능합니다.
현재 선두 사용자가 AutoBid를 중지해도 이미 성립한 leadingBid는 그대로 유지되며 가격은 내려가지 않습니다.

### AutoBid EXHAUSTED 의미
- AutoBid 사용자가 현재 선두가 아니고
- 자신의 maxAmount로는 `nextValidAmount(currentPrice)` 이상을 만들 수 없게 된 순간

`EXHAUSTED`로 전환합니다.

현재 선두이면서 currentPrice == maxAmount인 경우에는 아직 이기고 있으므로 ACTIVE를 유지합니다.
이후 다른 Bid가 maxAmount를 넘어 상회하면 EXHAUSTED가 되며 `AUTO_BID_EXHAUSTED` 알림을 생성합니다.
maxAmount를 상향하면 PUT 요청으로 다시 ACTIVE가 될 수 있습니다.

Response `200`: AutoBid 상태.

---

## 5. ProductAppend

### POST /auctions/{auctionId}/appends
판매자 전용.
Header: `Idempotency-Key`는 후순위 HTTP 멱등 기능 도입 시 적용 (P1에서는 불필요·전달 시 무시)
- 논리 상태 READY 또는 OPEN (입찰 여부 무관)
- content 1~200자
- 경매당 최대 10건 (`409 PRODUCT_APPEND_LIMIT`)
- 개수 확인은 Auction 락 안에서 수행

Request:
```json
{
  "content": "구성품 사진을 추가 확인했으며 케이블도 함께 드립니다."
}
```

Response `201`:
```json
{
  "id": 700,
  "auctionId": 40,
  "content": "구성품 사진을 추가 확인했으며 케이블도 함께 드립니다.",
  "createdAt": "2026-10-03T05:00:00Z"
}
```

등록 후 참여자에게 Notification 생성, AFTER_COMMIT WebSocket/Web Push 발송.
- 참여자: 해당 경매에 Bid 또는 AutoBid가 있는 사용자, 해당 상품을 관심상품으로 등록한 사용자
- dedupeKey: `PRODUCT_APPEND_ADDED:{appendId}:{userId}`
