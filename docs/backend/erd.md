# ERD / DB Schema - 1차 초안

## 공통 원칙
- PK: BIGINT
- 금액: BIGINT, 원 단위 정수
- 시간: DATETIME(6)
- Enum: 애플리케이션 Enum + DB 문자열 저장
- 핵심 거래 이력은 물리 삭제보다 상태 전환/이력 보존 우선

## users
- id PK
- email UNIQUE NOT NULL
- passwordHash NOT NULL
- nickname UNIQUE NOT NULL
- regionId FK NOT NULL
- trustScore NOT NULL DEFAULT 0
- status: ACTIVE / WITHDRAWN
- createdAt / updatedAt

## regions
- id PK
- regionCode UNIQUE
- sidoName
- sigunguName

## products
- id PK
- sellerId FK
- regionId FK
- category
- title
- description
- condition
- conditionDescription VARCHAR(500) NOT NULL
- status: ACTIVE / SOLD / DELETED
- createdAt / updatedAt

ProductCondition:
- UNOPENED
- LIKE_NEW
- GOOD
- FAIR
- DAMAGED
- NEEDS_REPAIR

## product_images
- id PK
- productId FK
- objectKey
- sortOrder
- createdAt
- UNIQUE(productId, sortOrder)

## product_appends
- id PK
- productId FK
- auctionId FK
- content VARCHAR(200)
- createdAt

## auctions
- id PK
- productId FK
- status: READY / OPEN / ENDED / CANCELED
- startPrice BIGINT
- minBidIncrement BIGINT
- currentPrice BIGINT
- leadingBidderId FK nullable
- startAt
- endAt
- relistedFromAuctionId self FK nullable
- createdAt / updatedAt

Indexes:
- (status, startAt)
- (status, endAt)
- (productId, createdAt)

## bids
- id PK
- auctionId FK
- bidderId FK
- amount BIGINT
- type: MANUAL / AUTO
- autoBidId FK nullable
- createdAt
- UNIQUE(auctionId, amount)

## auto_bids
- id PK
- auctionId FK
- bidderId FK
- maxAmount BIGINT
- incrementAmount BIGINT
- status: ACTIVE / STOPPED / EXHAUSTED
- priorityAt
- createdAt / updatedAt
- UNIQUE(auctionId, bidderId)
- INDEX(auctionId, status, maxAmount, priorityAt)

## trades
- id PK
- auctionId FK UNIQUE
- sellerId FK
- buyerId FK
- status
- responseDeadline
- completionRequestedBy FK nullable
- completionRequestedAt nullable
- completedAt nullable
- createdAt / updatedAt
- INDEX(status, responseDeadline)

## trust_histories
- id PK
- userId FK
- tradeId FK
- delta
- reason
- scoreAfter
- createdAt
- UNIQUE(tradeId, userId, reason)

## notifications
- id PK
- userId FK
- type
- message
- productId nullable
- auctionId nullable
- tradeId nullable
- readAt nullable
- dedupeKey UNIQUE
- createdAt

## push_subscriptions
- id PK
- userId FK
- endpoint UNIQUE
- p256dh
- auth
- createdAt / updatedAt

## favorites
- id PK
- userId FK
- productId FK
- createdAt
- UNIQUE(userId, productId)

## 삭제 원칙
거래 이력이 연결된 핵심 엔티티는 ON DELETE RESTRICT를 기본 방향으로 사용합니다.
