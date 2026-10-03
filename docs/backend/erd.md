# ERD / DB Schema - 1차 초안

## 공통 원칙
- PK: BIGINT
- 금액: BIGINT, 원 단위 정수
- 시간: DATETIME(6)
- Enum: 애플리케이션 Enum + DB 문자열 저장
- 핵심 거래 이력은 물리 삭제보다 상태 전환/이력 보존 우선
- 경매 정합성, 추적 가능성, 동시성 검증을 설계 우선순위로 둡니다.

## JPA 연관관계 원칙
- 대부분의 관계는 `@ManyToOne(fetch = LAZY)` 단방향으로 설계합니다.
- DB의 1:N 관계라고 해서 부모 Entity에 무조건 `List<...>`를 만들지 않습니다.
- User에는 Product/Bid/Trade/Notification 등의 대형 컬렉션을 두지 않습니다.
- Auction에도 Bid/AutoBid 컬렉션을 두지 않고 Repository 조회로 처리합니다.
- `Product ↔ ProductImage`만 생명주기가 강하게 결합되어 있어 양방향 관계를 허용합니다.
- ProductImage에는 `cascade = ALL`, `orphanRemoval = true`를 사용합니다.
- Favorite는 `@ManyToMany` 대신 별도 Entity로 유지합니다.
- Trade → Auction은 단방향 `@OneToOne(fetch = LAZY)`로 둡니다.
- 재경매는 Auction → Auction 단방향 self reference로 둡니다.
- 거래/경매 이력에 대한 Cascade REMOVE는 사용하지 않습니다.

## users
- id PK
- email UNIQUE NOT NULL
- passwordHash NOT NULL
- nickname UNIQUE NOT NULL
- regionId FK NOT NULL
- trustScore NOT NULL DEFAULT 0
- status: ACTIVE / WITHDRAWN
- createdAt / updatedAt

JPA:
- User → Region: ManyToOne LAZY

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

JPA:
- Product → User(seller): ManyToOne LAZY
- Product → Region: ManyToOne LAZY
- Product ↔ ProductImage: OneToMany / ManyToOne 양방향

## product_images
- id PK
- productId FK
- objectKey
- sortOrder
- createdAt
- UNIQUE(productId, sortOrder)

JPA:
- ProductImage → Product: ManyToOne LAZY
- Product.images: cascade ALL + orphanRemoval

## product_appends
- id PK
- productId FK
- auctionId FK
- content VARCHAR(200)
- createdAt

JPA:
- ProductAppend → Product: ManyToOne LAZY
- ProductAppend → Auction: ManyToOne LAZY

## auctions
- id PK
- productId FK
- status: READY / OPEN / ENDED / CANCELED
- startPrice BIGINT
- minBidIncrement BIGINT
- currentPrice BIGINT
- leadingBidderId FK nullable
- winningBidId FK → bids.id nullable
- startAt
- endAt
- relistedFromAuctionId self FK nullable
- createdAt / updatedAt

의미:
- `currentPrice + leadingBidderId`: 진행 중 빠른 조회를 위한 현재 상태 snapshot
- `winningBidId`: 종료 시 확정된 낙찰의 실제 Bid 근거
- 별도 winnerId는 두지 않으며 winningBid.bidder로 추적
- 유찰이면 winningBidId = null

Indexes:
- (status, startAt)
- (status, endAt)
- (productId, createdAt)
- relistedFromAuctionId

JPA:
- Auction → Product: ManyToOne LAZY
- Auction → User(leadingBidder): ManyToOne LAZY
- Auction → Bid(winningBid): OneToOne LAZY 또는 ManyToOne LAZY + UNIQUE FK 검토
- Auction → Auction(relistedFrom): ManyToOne LAZY
- Auction.bids / Auction.autoBids 컬렉션은 두지 않음

## bids
- id PK
- auctionId FK
- bidderId FK
- amount BIGINT
- type: MANUAL / AUTO
- autoBidId FK nullable
- createdAt
- UNIQUE(auctionId, amount)

JPA:
- Bid → Auction: ManyToOne LAZY
- Bid → User(bidder): ManyToOne LAZY
- Bid → AutoBid: ManyToOne LAZY, nullable

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

JPA:
- AutoBid → Auction: ManyToOne LAZY
- AutoBid → User(bidder): ManyToOne LAZY

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

JPA:
- Trade → Auction: OneToOne LAZY
- Trade → User(seller): ManyToOne LAZY
- Trade → User(buyer): ManyToOne LAZY
- Trade → User(completionRequestedBy): ManyToOne LAZY, nullable

## trust_histories
- id PK
- userId FK
- tradeId FK
- delta
- reason
- scoreAfter
- createdAt
- UNIQUE(tradeId, userId, reason)

JPA:
- TrustHistory → User: ManyToOne LAZY
- TrustHistory → Trade: ManyToOne LAZY

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

JPA:
- Notification → User: ManyToOne LAZY
- Notification → Product/Auction/Trade: ManyToOne LAZY, nullable

## push_subscriptions
- id PK
- userId FK
- endpoint UNIQUE
- p256dh
- auth
- createdAt / updatedAt

JPA:
- PushSubscription → User: ManyToOne LAZY

## favorites
- id PK
- userId FK
- productId FK
- createdAt
- UNIQUE(userId, productId)

JPA:
- Favorite → User: ManyToOne LAZY
- Favorite → Product: ManyToOne LAZY
- @ManyToMany 사용하지 않음

## 삭제 원칙
- 거래 이력이 연결된 핵심 엔티티는 ON DELETE RESTRICT를 기본 방향으로 사용합니다.
- 회원탈퇴는 User 삭제가 아니라 WITHDRAWN 상태 전환입니다.
- Product 삭제도 일반적으로 DELETED 상태 전환으로 처리합니다.
- Auction / Bid / Trade / TrustHistory는 비즈니스 이력 보존을 우선합니다.
- 연쇄 삭제는 ProductImage 같은 강한 종속 데이터에만 제한적으로 사용합니다.

## 백엔드 기술 검증 핵심
이 프로젝트의 백엔드 기술 중심은 단순 CRUD 기능 수보다 다음 문제를 실제 코드와 테스트로 해결하는 것입니다.

1. 동시 입찰에서 Auction.currentPrice / leadingBidder / Bid 이력 정합성
2. 여러 AutoBid의 경쟁과 동가 우선순위
3. 경매 종료 Scheduler와 마지막 입찰의 race condition
4. 중복 요청 / Scheduler 중복 실행에 대한 멱등성
5. DB commit 이후 WebSocket / Push 전달
6. 낙찰 근거 winningBid 추적
7. Testcontainers + MySQL 기반 동시성 통합테스트
8. 부하 테스트와 운영 지표를 통한 병목 확인
