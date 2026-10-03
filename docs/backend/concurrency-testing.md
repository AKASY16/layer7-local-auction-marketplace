# 경매 동시성 테스트 계획

## 목적
경매 핵심 로직을 H2가 아닌 Testcontainers 기반 MySQL 8.4에서 검증합니다.

검증 대상:
- PESSIMISTIC_WRITE 직렬화
- Bid / Auction snapshot 정합성
- AutoBid 경쟁 결과
- 경매 종료 경계시각
- Idempotency
- Scheduler 중복 실행
- UNIQUE 제약의 최종 방어선

## 테스트 계층

### 1. Unit Test
DB 없이 순수 정책을 검증합니다.
- BidIncrementPolicy.isValidAmount()
- BidIncrementPolicy.nextValidAmount()
- 가격구간 경계
- AutoBid 승자/가격 계산
- 동일 maxAmount + priorityAt

### 2. Integration Test
Testcontainers로 MySQL 8.4를 실행합니다.
- 실제 Transaction
- PESSIMISTIC_WRITE
- UNIQUE constraint
- Repository query
- Flyway schema

### 3. Concurrency Scenario Test
ExecutorService + CountDownLatch로 여러 작업을 실제로 동시에 시작합니다.
테스트 메서드 자체에는 @Transactional을 두지 않고, 각 worker가 실제 Service의 독립 Transaction을 사용합니다.

## 필수 시나리오

### C01. 가격구간 경계
- 9,900 → 10,000
- 10,000 → 10,500
- 49,500 → 50,000
- 99,000 → 100,000
- 100,000 → 105,000
- 유효하지 않은 금액은 거절

### C02. 동일 가격 동시 수동입찰
현재가 10,000원에서 여러 사용자가 10,500원을 동시에 요청합니다.

기대:
- 성공 Bid는 정확히 1건
- 동일 (auctionId, amount) 중복 없음
- currentPrice = 10,500
- leadingBidder와 성공 Bid의 bidder 일치

### C03. 서로 다른 가격 10명 동시입찰
10명이 서로 다른 유효 금액으로 동시에 요청합니다.

기대:
- 처리 순서에 따라 낮은 금액 요청은 실패할 수 있음
- 최종 currentPrice는 성공한 Bid 중 최고금액
- leadingBidder는 해당 Bid 사용자
- 유효하지 않은 중간상태 없음

### C04. 동일 Auction 100명 동시입찰
동일 경매에 100개 요청을 동시에 발생시킵니다.

검증:
- 정합성 위반 0건
- deadlock/lock timeout 관찰
- 모든 작업이 유한 시간 내 종료
- 최종 currentPrice / leadingBidder / Bid 이력 일치

이 테스트의 수치는 이후 부하테스트 결과와 구분합니다. 목적은 처리량 측정이 아니라 동시성 정합성 검증입니다.

### C05. 수동입찰 + 기존 AutoBid
A: AutoBid max 100,000원
B/C/D가 동시에 서로 다른 수동입찰을 요청.

기대:
- 모든 Transaction 종료 후 AutoBid 정책에 맞는 선두/가격
- currentPrice가 A.maxAmount를 초과하지 않음
- Auction snapshot과 마지막 실제 Bid 일치

### C06. AutoBid 여러 개 동시 설정
A max 150,000 / B max 120,000 / C max 90,000을 동시에 설정.

기대:
- 최종 leader = A
- final price = nextValidAmount(120,000) = 125,000
- worker 실행 순서와 관계없이 동일한 최종 비즈니스 결과

### C07. 동일 maxAmount 경쟁
A와 B가 모두 max 100,000.

기대:
- priorityAt이 빠른 사용자가 leader
- currentPrice = 100,000
- maxAmount 변경 시 priorityAt이 새 시각으로 갱신되어 우선순위 재계산

### C08. 입찰 vs 종료 Scheduler
endAt 경계에서 입찰 worker와 종료 worker를 동시에 실행.

시간 규칙:
- now < endAt: 입찰 가능
- now == endAt: 입찰 불가
- now > endAt: 입찰 불가

불변조건:
- ENDED 이후 새 Bid 없음
- Trade는 Auction당 최대 1개
- winningBid/currentPrice/leadingBidder 간 모순 없음

### C09. 동일 Idempotency-Key 동시 재요청
동일 사용자가 동일 key와 동일 요청으로 여러 번 동시 호출.

기대:
- 실제 명령 수행 1회
- IdempotencyRequest 1건
- 동일 요청 재전송은 기존 성공 결과 재사용

같은 key에 다른 requestHash를 보내면 409 Conflict.

### C10. Scheduler / 신뢰점수 중복 실행
동일 Auction 종료 및 동일 Trade NO_RESPONSE 처리를 여러 worker가 동시에 시도.

기대:
- Trade 1건: UNIQUE(auctionId)
- TrustHistory 1건: UNIQUE(tradeId, userId, reason)
- 신뢰점수 delta 1회만 반영
- Notification도 dedupeKey 기준 1건

## 공통 불변조건

모든 동시성 테스트 종료 후 다음을 검사합니다.

- Auction.currentPrice는 유효 가격 격자 위에 있음
- leadingBidder는 currentPrice를 만든 최종 상태와 일치
- ENDED Auction에는 종료 이후 생성된 Bid가 없음
- winningBid가 존재하면 해당 Bid.auctionId가 동일 Auction
- Trade는 Auction당 최대 1개
- Bid의 (auctionId, amount) UNIQUE 위반 없음
- 중복 명령이 비즈니스 효과를 두 번 만들지 않음

## 구현 도구
- JUnit 5
- Spring Boot Test
- Testcontainers MySQL 8.4
- ExecutorService
- CountDownLatch
- 필요 시 CompletableFuture

## 주의
- H2 결과만으로 MySQL의 lock/constraint 동작을 검증했다고 판단하지 않음
- 동시성 테스트의 worker는 각각 독립 Transaction을 사용
- flaky test를 피하기 위해 sleep 기반 동기화보다 CountDownLatch/Barrier 계열을 우선 사용
