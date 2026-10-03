# Auction / Bid / AutoBid API

## 1. Auction

### POST /products/{productId}/auctions
판매자 전용.
Header: `Idempotency-Key`

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
- endAt > effective startAt
- startPrice는 유효 가격단위
- Product 소유자이며 Product.status = ACTIVE
- 동일 Product에 READY/OPEN Auction이 이미 있으면 409
- `startAt = null`이면 즉시 시작
- `startAt`을 명시했다면 serverNow보다 미래여야 함

Response `201`:
```json
{
  "id": 40,
  "productId": 30,
  "status": "OPEN",
  "biddingOpen": true,
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
경매 탐색.

Query:
- `regionId` optional
- `category` optional
- `keyword` optional
- `status=READY|OPEN|ENDED` optional
- page / size

기본 정렬: 최신 등록순. Frontend 요구에 따라 종료임박순을 추가할 수 있음.

Item:
```json
{
  "auctionId": 40,
  "status": "OPEN",
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

### GET /auctions/{auctionId}
경매 상세.

Response `200` 주요 필드:
```json
{
  "id": 40,
  "status": "OPEN",
  "biddingOpen": true,
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

`biddingOpen`은 `status == OPEN && serverTime < endAt`으로 계산한 논리적 입찰 가능 여부입니다.
Scheduler 반영이 늦어 DB status가 잠시 OPEN이어도 endAt이 지났다면 `biddingOpen=false`, `nextBidAmount=null`로 반환합니다.

### POST /auctions/{auctionId}/cancel
판매자 전용.
- READY: 가능
- OPEN: Bid 0건일 때만 가능
- 이미 CANCELED이면 현재 상태를 그대로 반환하여 자연스럽게 멱등 처리

Response `200`: Auction 상태.

### POST /auctions/{auctionId}/relist
Header: `Idempotency-Key`

기존 Auction은 변경하지 않고 동일 Product에 새 Auction 생성.

허용 조건:
- 원 Auction.status = ENDED
- Product.status = ACTIVE
- Trade가 없으면(유찰) 허용
- Trade가 있으면 status가 DECLINED 또는 NO_RESPONSE일 때만 허용
- AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED이면 불가

불가 시 `409 AUCTION_RELIST_NOT_ALLOWED`.

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

### GET /auctions/{auctionId}/bid-policy

Response:
```json
{
  "currentPrice": 9900,
  "hasBid": true,
  "minimumBidAmount": 10000,
  "currentUnit": 100,
  "serverTime": "2026-10-03T05:00:00Z"
}
```

Bid가 0건이면 `minimumBidAmount = startPrice`.

Frontend 편의를 위한 조회이며 최종 검증은 Bid 요청 Transaction 안에서 다시 수행합니다.
논리적으로 입찰 불가능한 상태면 `409 AUCTION_NOT_OPEN` 또는 `409 AUCTION_ENDED`를 반환합니다.

---

## 3. Manual Bid

### POST /auctions/{auctionId}/bids
인증 필요.
Header: `Idempotency-Key`

Request:
```json
{
  "amount": 10000
}
```

검증:
- OPEN
- `serverNow < endAt`
- 판매자 본인 아님
- 현재 선두 아님 (`409 ALREADY_LEADING`)
- 유효 가격단위
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

### GET /auctions/{auctionId}/bids
공개 Bid 이력.

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
Header: `Idempotency-Key`

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
- OPEN / endAt 이전
- 판매자 본인 금지
- maxAmount 유효 가격단위
- Bid 0건이면 maxAmount >= startPrice
- 현재 사용자가 leader라면 maxAmount >= currentPrice
- leader가 아니라면 maxAmount >= nextValidAmount(currentPrice)

경쟁 계산:
- leader 본인의 설정·변경·재활성화는 경쟁 없이 maxAmount만 갱신
- leader가 아니면 요청한 maxAmount와 현재 leader의 상한(ACTIVE AutoBid의 maxAmount, 없으면 currentPrice)을 비교
- 요청 maxAmount가 더 크면 요청자가 선두, 같거나 작으면 기존 leader 유지 (동액 선두 우선)
- STOPPED/EXHAUSTED → ACTIVE 재활성화도 같은 규칙으로 경쟁
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
Header: `Idempotency-Key`

AutoBid를 삭제하지 않고 `STOPPED`로 전환. 이미 성립한 Bid에는 영향 없음.
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
Header: `Idempotency-Key`
- OPEN
- Bid 1건 이상
- content 1~200자

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
