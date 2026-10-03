# ERD / DB Schema - V1 후보

## 공통 원칙
- MySQL 8.4 / InnoDB / utf8mb4
- PK: `BIGINT AUTO_INCREMENT`
- 금액: `BIGINT`, 원 단위 정수
- 시간: `DATETIME(6)`, 애플리케이션에서는 `Instant`/UTC 기준
- Enum: Java `EnumType.STRING` + DB `VARCHAR`
- 이 문서의 컬럼명은 Java 필드 기준 camelCase이고, 실제 DB 컬럼은 snake_case ([V1 스키마 초안](V1__init_schema_draft.sql) 기준)
- 핵심 거래 이력은 물리 삭제보다 상태 전환/이력 보존 우선
- 구조적으로 변하지 않는 불변조건은 DB 제약으로도 보장
- 가격구간 규칙처럼 변경 가능한 서비스 정책은 도메인 코드에서 검증
- 트랜잭션 격리 수준은 READ COMMITTED, 직렬화는 비관적 락으로 보장 ([락 순서와 트랜잭션 규칙](locking.md))

## JPA 연관관계 원칙
- 대부분 `@ManyToOne(fetch = LAZY)` 단방향
- User / Auction에 대형 1:N 컬렉션을 두지 않음
- `Product ↔ ProductImage`만 양방향 + `cascade = ALL` + `orphanRemoval = true`
- Favorite는 별도 Entity, `@ManyToMany` 미사용
- 거래/경매 이력에 Cascade REMOVE 미사용
- Trade → Auction은 단방향 `@OneToOne(fetch = LAZY)`

---

## regions

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| regionCode | VARCHAR(20) | NOT NULL, UNIQUE |
| sidoName | VARCHAR(50) | NOT NULL |
| sigunguName | VARCHAR(50) | NOT NULL |

- MVP 지역 단위는 시·군·구
- 공식 행정구역 코드 사용

## users

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| email | VARCHAR(320) | NOT NULL, UNIQUE |
| passwordHash | VARCHAR(255) | NOT NULL |
| nickname | VARCHAR(50) | NOT NULL, UNIQUE |
| regionId | BIGINT | NOT NULL, FK → regions |
| trustScore | INT | NOT NULL, DEFAULT 0 |
| status | VARCHAR(20) | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

Status:
- ACTIVE
- WITHDRAWN

정책:
- 회원탈퇴는 물리삭제가 아니라 WITHDRAWN
- MVP에서는 탈퇴 후에도 기존 email/nickname UNIQUE를 유지하여 재사용하지 않음
- 신뢰점수는 음수 허용
- trustScore는 `trust_score = trust_score + ?` 원자 UPDATE로만 갱신

JPA:
- User → Region: ManyToOne LAZY

## products

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| sellerId | BIGINT | NOT NULL, FK → users |
| regionId | BIGINT | NOT NULL, FK → regions |
| category | VARCHAR(50) | NOT NULL |
| title | VARCHAR(120) | NOT NULL |
| description | TEXT | NOT NULL |
| condition | VARCHAR(30) | NOT NULL, DB 컬럼명 `condition_code` (`CONDITION`은 MySQL 예약어) |
| conditionDescription | VARCHAR(500) | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

Condition:
- UNOPENED
- LIKE_NEW
- GOOD
- FAIR
- DAMAGED
- NEEDS_REPAIR

Status:
- ACTIVE
- SOLD
- DELETED

Indexes:
- (regionId, status, createdAt)
- (sellerId, status, createdAt)

JPA:
- Product → User(seller): ManyToOne LAZY
- Product → Region: ManyToOne LAZY
- Product ↔ ProductImage: 양방향

## product_images

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| productId | BIGINT | NOT NULL, FK → products |
| objectKey | VARCHAR(512) | NOT NULL |
| sortOrder | INT | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |

Constraints:
- UNIQUE(productId, sortOrder)
- sortOrder >= 0
- ProductImage는 Product에 강하게 종속되므로 물리삭제 시 CASCADE 허용

## auctions

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| productId | BIGINT | NOT NULL, FK → products |
| status | VARCHAR(20) | NOT NULL |
| startPrice | BIGINT | NOT NULL |
| currentPrice | BIGINT | NOT NULL |
| leadingBidId | BIGINT | NULL, FK → bids |
| winningBidId | BIGINT | NULL, FK → bids |
| startAt | DATETIME(6) | NOT NULL |
| endAt | DATETIME(6) | NOT NULL |
| relistedFromAuctionId | BIGINT | NULL, self FK |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

Status:
- READY
- OPEN
- ENDED
- CANCELED

핵심 의미:
- 생성 시 `currentPrice = startPrice`
- 아직 Bid가 없으면 `leadingBidId = null`
- **첫 실제 Bid의 최소금액은 startPrice 자체**
- Bid가 하나라도 생긴 뒤부터 다음 최소금액은 `nextValidAmount(currentPrice)`
- `leadingBidId`: 진행 중 현재 선두를 만든 정확한 Bid
- `winningBidId`: 종료 시 확정된 낙찰 Bid
- 낙찰자가 필요하면 Bid.bidder로 추적하며 별도 winnerId/leadingBidderId를 중복 저장하지 않음
- ENDED 유찰이면 winningBidId = null
- 낙찰 종료 시 일반적으로 `winningBidId = leadingBidId`
- status는 저장 상태이며 API는 서버시간 기준 논리 상태와 finalized를 반환 ([상태 모델](auction-state.md))
- 종료 Scheduler는 `(status, endAt)` 인덱스로 `status IN (READY, OPEN) AND endAt <= now`를 조회

Checks:
- startPrice >= 100
- currentPrice >= startPrice
- startAt < endAt
- relistedFromAuctionId IS NULL OR relistedFromAuctionId <> id

Indexes:
- (status, startAt)
- (status, endAt)
- (productId, status)
- (productId, createdAt)
- relistedFromAuctionId

동일 Product에 READY/OPEN Auction이 동시에 둘 이상 존재하지 않도록:
1. Product row를 PESSIMISTIC_WRITE로 잠금
2. (productId, status)로 READY/OPEN 존재여부 확인
3. 없을 때만 새 Auction 생성

MySQL의 단순 UNIQUE만으로 부분조건 UNIQUE를 표현하려고 복잡도를 높이지 않음. 작업별 락 대상과 순서는 [락 순서와 트랜잭션 규칙](locking.md)을 따름.

JPA:
- Auction → Product: ManyToOne LAZY
- Auction → Bid(leadingBid): OneToOne/ManyToOne LAZY 단방향
- Auction → Bid(winningBid): OneToOne/ManyToOne LAZY 단방향
- Auction → Auction(relistedFrom): ManyToOne LAZY
- Auction.bids / Auction.autoBids 컬렉션 없음

주의:
- leadingBid/winningBid가 반드시 자기 Auction의 Bid여야 한다는 교차행 불변조건은 Service 검증 + 통합테스트로 보장

## auto_bids

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| auctionId | BIGINT | NOT NULL, FK → auctions |
| bidderId | BIGINT | NOT NULL, FK → users |
| maxAmount | BIGINT | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

Status:
- ACTIVE
- STOPPED
- EXHAUSTED

Constraints:
- UNIQUE(auctionId, bidderId)
- maxAmount >= 100

Index:
- 현재 선두의 AutoBid는 leadingBid의 bidder로 `UNIQUE(auctionId, bidderId)`를 통해 조회하므로 경쟁용 별도 인덱스를 두지 않음

도메인 정책:
- maxAmount는 BidIncrementPolicy의 유효 가격 격자여야 함
- 사용자는 상승폭을 설정하지 않음
- 경매당 ACTIVE AutoBid는 최대 1개이며 있다면 현재 선두의 것
- 동액 우선순위는 현재 선두 우선 규칙으로 처리하며 별도 우선순위 시각을 저장하지 않음

## bids

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| auctionId | BIGINT | NOT NULL, FK → auctions |
| bidderId | BIGINT | NOT NULL, FK → users |
| amount | BIGINT | NOT NULL |
| type | VARCHAR(20) | NOT NULL |
| autoBidId | BIGINT | NULL, FK → auto_bids |
| createdAt | DATETIME(6) | NOT NULL |

Type:
- MANUAL
- AUTO

Constraints:
- UNIQUE(auctionId, amount)
- amount >= 100
- MANUAL이면 autoBidId IS NULL
- AUTO이면 autoBidId IS NOT NULL

Indexes:
- (auctionId, createdAt)
- (bidderId, createdAt)

정책:
- Bid는 append-only
- 성립한 Bid는 수정/삭제/철회하지 않음
- 금액은 경매 안에서 id 순으로 엄격히 증가하며 leadingBid는 항상 최고 금액 Bid
- 한 경쟁 이벤트에서 저장되는 Bid는 최대 2건(패자가 버틴 금액, 승자 최종가)이므로 이력 정렬은 id 기준

## product_appends

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| auctionId | BIGINT | NOT NULL, FK → auctions |
| content | VARCHAR(200) | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |

변경점:
- 기존 `productId + auctionId` 이중 참조에서 productId 제거
- Product는 `auction.productId`로 유일하게 결정 가능
- 두 FK가 서로 다른 Product/Auction을 가리키는 불일치 가능성을 제거

Index:
- (auctionId, createdAt)

## trades

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| auctionId | BIGINT | NOT NULL, UNIQUE, FK → auctions |
| sellerId | BIGINT | NOT NULL, FK → users |
| buyerId | BIGINT | NOT NULL, FK → users |
| status | VARCHAR(30) | NOT NULL |
| responseDeadline | DATETIME(6) | NOT NULL |
| tradeDeadline | DATETIME(6) | NOT NULL |
| completionRequestedBy | BIGINT | NULL, FK → users |
| completionRequestedAt | DATETIME(6) | NULL |
| completionDeadline | DATETIME(6) | NULL |
| completedAt | DATETIME(6) | NULL |
| canceledBy | BIGINT | NULL, FK → users |
| canceledAt | DATETIME(6) | NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

Status:
- AWAITING_RESPONSE
- IN_PROGRESS
- COMPLETION_REQUESTED
- COMPLETED
- DECLINED
- NO_RESPONSE
- CANCELED
- EXPIRED

Checks:
- sellerId <> buyerId
- responseDeadline < tradeDeadline
- completionRequestedBy / completionRequestedAt / completionDeadline은 모두 NULL 또는 모두 NOT NULL
- canceledBy / canceledAt은 둘 다 NULL 또는 둘 다 NOT NULL

Index:
- (status, responseDeadline)
- (status, tradeDeadline)
- (status, completionDeadline)
- (sellerId, createdAt)
- (buyerId, createdAt)

정책:
- responseDeadline = Auction.endAt + 24h
- tradeDeadline = Auction.endAt + 7d
- completionDeadline = max(tradeDeadline, completionRequestedAt + 24h). 완료 요청 시 저장하고 거절 시 clear. 계산식이 아니라 컬럼으로 두어 Scheduler가 인덱스로 조회
- seller/buyer가 실제 Auction 당사자인지는 Service에서 검증

## trust_histories

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| tradeId | BIGINT | NOT NULL, FK → trades |
| delta | INT | NOT NULL |
| reason | VARCHAR(40) | NOT NULL |
| scoreAfter | INT | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |

Reason:
- TRADE_COMPLETED
- WINNER_DECLINED
- WINNER_NO_RESPONSE
- TRADE_CANCELED

Constraints:
- UNIQUE(tradeId, userId, reason)
- delta <> 0

Index:
- (userId, createdAt)

append-only.

연속 실패 판정(이용 정지)은 이 테이블에서 마지막 TRADE_COMPLETED와 마지막 자동 정지 이후의 실패 reason 수로 계산합니다.

## user_restrictions

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| type | VARCHAR(30) | NOT NULL |
| reason | VARCHAR(50) | NOT NULL |
| source | VARCHAR(20) | NOT NULL |
| triggerTradeId | BIGINT | NULL, UNIQUE, FK → trades |
| startsAt | DATETIME(6) | NOT NULL |
| endsAt | DATETIME(6) | NULL |
| liftedAt | DATETIME(6) | NULL |
| createdAt | DATETIME(6) | NOT NULL |

Type:
- TRADING: 수동입찰, AutoBid 설정·변경·재활성화, 경매 생성·재경매 금지

Reason:
- CONSECUTIVE_FAILURES
- ADMIN_ACTION

Source:
- SYSTEM
- ADMIN

Constraints:
- UNIQUE(triggerTradeId): 같은 실패로 자동 정지가 두 번 생기지 않음. 수동 정지는 NULL
- endsAt IS NULL OR startsAt < endsAt
- SYSTEM이면 triggerTradeId와 endsAt NOT NULL

Index:
- (userId, createdAt)

정책:
- 정지 여부 = `liftedAt IS NULL AND startsAt <= now AND (endsAt IS NULL OR endsAt > now)`
- 해제는 Scheduler 없이 서버시간으로 판정
- users.status(ACTIVE/WITHDRAWN)는 로그인 판정용이므로 정지와 섞지 않음
- MVP의 수동 정지는 운영자가 ADMIN 기록을 DB에 직접 생성

## notifications

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| type | VARCHAR(50) | NOT NULL |
| message | VARCHAR(500) | NOT NULL |
| productId | BIGINT | NULL, FK → products |
| auctionId | BIGINT | NULL, FK → auctions |
| tradeId | BIGINT | NULL, FK → trades |
| readAt | DATETIME(6) | NULL |
| dedupeKey | VARCHAR(200) | NOT NULL, UNIQUE |
| createdAt | DATETIME(6) | NOT NULL |

Index:
- (userId, readAt, createdAt)

Notification 저장은 비즈니스 상태변경 Transaction 안에서 처리하고 실제 WebSocket/Web Push 전송은 AFTER_COMMIT.

## push_subscriptions

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| endpoint | TEXT | NOT NULL |
| endpointHash | CHAR(64) | NOT NULL, UNIQUE |
| p256dh | VARCHAR(255) | NOT NULL |
| auth | VARCHAR(255) | NOT NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

- 긴 Web Push endpoint 자체를 UNIQUE index로 잡지 않고 SHA-256 endpointHash로 중복 구독 방지
- endpointHash는 애플리케이션에서 계산

Index:
- (userId, createdAt)

## favorites

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| productId | BIGINT | NOT NULL, FK → products |
| createdAt | DATETIME(6) | NOT NULL |

Constraints:
- UNIQUE(userId, productId)

Index:
- (userId, createdAt)

## idempotency_requests

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | BIGINT | PK |
| userId | BIGINT | NOT NULL, FK → users |
| scope | VARCHAR(50) | NOT NULL |
| idempotencyKey | VARCHAR(100) | NOT NULL |
| requestHash | CHAR(64) | NOT NULL |
| resourceType | VARCHAR(40) | NULL |
| resourceId | BIGINT | NULL |
| responseStatus | SMALLINT | NULL |
| responseBody | JSON | NULL |
| createdAt | DATETIME(6) | NOT NULL |
| updatedAt | DATETIME(6) | NOT NULL |

상태 컬럼을 두지 않습니다. 기록은 비즈니스 트랜잭션 안에서 INSERT되고 같은 트랜잭션에서 응답 snapshot이 채워지므로, 커밋되어 다른 트랜잭션에 보이는 기록은 항상 성공한 요청입니다. responseStatus/responseBody가 NULL인 상태는 트랜잭션 내부에서만 존재합니다.

Constraints:
- UNIQUE(userId, scope, idempotencyKey)
- resourceType/resourceId는 둘 다 NULL 또는 둘 다 NOT NULL

Index:
- createdAt: 24시간 지난 기록 정리 배치용

정책:
- 동일 key + 동일 requestHash는 기존 결과 재사용
- 성공한 요청의 HTTP status/body snapshot을 저장해 재요청에 동일한 논리적 결과 반환
- 실패한 요청은 롤백과 함께 기록도 사라지므로 같은 key로 재시도하면 다시 실행
- 재전송 응답에는 `Idempotency-Replayed: true` 헤더 사용
- 동일 key + 다른 requestHash는 409 Conflict
- 처리 방식 상세: [API 명세 공통 규칙](../05-api-spec.md#idempotency)

---

## FK / 삭제 원칙

기본:
- 핵심 거래/이력 관계는 ON DELETE RESTRICT
- User / Product는 상태 기반 soft delete
- ProductImage만 Product의 강한 종속 데이터이므로 ON DELETE CASCADE 허용
- 나머지 연쇄 물리삭제는 사용하지 않음

## DB CHECK와 Domain 검증의 경계

DB CHECK:
- 양수 금액
- startAt < endAt
- enum 문자열 허용값
- 타입과 nullable 조합
- seller != buyer
- pair nullable 일관성

Domain:
- 가격구간별 유효 금액
- 첫 Bid = startPrice 규칙
- seller self-bid 금지
- Auction 상태 전이
- AutoBid 경쟁 계산
- leadingBid/winningBid가 해당 Auction의 Bid인지
- READY/OPEN Auction의 Product당 단일성
- Trade 당사자 일치

## V1에서 확정한 주요 변경

1. `leadingBidderId` → `leadingBidId`
   - 현재 선두를 만든 정확한 Bid를 추적하고 bidder는 Bid에서 파생

2. 첫 입찰 규칙 확정
   - Bid가 0건이면 첫 입찰 최소금액 = startPrice
   - 이후부터 `nextValidAmount(currentPrice)`

3. `ProductAppend.productId` 제거
   - Auction을 통해 Product가 이미 결정되므로 중복 FK 제거

4. PushSubscription endpoint 중복검사
   - 긴 URL 자체 대신 `endpointHash` UNIQUE 사용

5. Product당 READY/OPEN Auction 단일성
   - Product row lock + 존재검사 + (productId,status) index로 보장

6. `AutoBid.priorityAt` 제거
   - 동액이면 현재 선두 우선 규칙으로 처리하므로 우선순위 시각과 경쟁용 인덱스가 필요 없음

7. Trade 기한·취소 컬럼
   - tradeDeadline, completionDeadline, canceledBy, canceledAt 추가
   - CANCELED / EXPIRED 상태 추가

8. `user_restrictions` 추가
   - 신뢰점수와 분리된 기간제 거래 참여 정지
