# Auction / Bid / AutoBid API

## 1. Auction

### POST /products/{productId}/auctions
판매자 전용.

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
- 동일 Product에 READY/OPEN Auction이 이미 있으면 409

Response `201`:
```json
{
  "id": 40,
  "productId": 30,
  "status": "OPEN",
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

### POST /auctions/{auctionId}/cancel
판매자 전용.
- READY: 가능
- OPEN: Bid 0건일 때만 가능
- 이미 CANCELED이면 현재 상태를 그대로 반환하여 자연스럽게 멱등 처리

Response `200`: Auction 상태.

### POST /auctions/{auctionId}/relist
Header: `Idempotency-Key`

기존 Auction은 변경하지 않고 동일 Product에 새 Auction 생성.

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

### GET /auctions/{auctionId}/bids
공개 Bid 이력.

다른 사용자의 AutoBid 설정 상한은 노출하지 않고 실제 성립한 Bid만 반환.

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
  "priorityAt": "2026-10-03T05:00:00Z",
  "currentUserLeading": true
}
```

### PUT /auctions/{auctionId}/auto-bid
신규 설정 또는 기존 maxAmount 변경/재활성화.
Header: `Idempotency-Key`

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

priorityAt:
- 최초 생성: now
- 실제 maxAmount 변경: now
- STOPPED/EXHAUSTED → ACTIVE 재활성화: now
- ACTIVE 상태에서 동일 maxAmount 재요청: 기존 priorityAt 유지

Response `200`:
```json
{
  "autoBid": {
    "id": 501,
    "maxAmount": 100000,
    "status": "ACTIVE",
    "priorityAt": "2026-10-03T05:00:00Z"
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
  }
}
```

### DELETE /auctions/{auctionId}/auto-bid
Header: `Idempotency-Key`

AutoBid를 삭제하지 않고 `STOPPED`로 전환. 이미 성립한 Bid에는 영향 없음.

Response `200`: AutoBid 상태.

---

## 5. ProductAppend

### POST /auctions/{auctionId}/appends
판매자 전용.
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
