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
- [락 순서와 트랜잭션 규칙](locking.md) (READ COMMITTED, 전역 락 순서, 락 후 재검증)

## 테스트 계층

### 1. Unit Test
DB 없이 순수 정책을 검증합니다.
- BidIncrementPolicy.isValidAmount()
- BidIncrementPolicy.nextValidAmount()
- 가격구간 경계
- 도전자 대 현재 선두 승패/가격 계산
- 동액 현재 선두 우선
- Bid 저장 규칙 (패자 금액 생략 조건 포함)

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
- deadlock/lock timeout 관찰. 락 대기 초과는 `503 RESOURCE_BUSY`로 끝나고 효과를 남기지 않음
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
- worker 실행 순서와 관계없이 검증하는 값은 최종 leader와 currentPrice뿐
- 저장 Bid 수와 C의 결과는 순서에 따라 다름. C가 먼저 처리되면 Bid를 남기고 EXHAUSTED, A가 먼저 선두가 된 뒤라면 `409 AUTO_BID_MAX_TOO_LOW`

### C07. 동액 경쟁
A가 AutoBid max 100,000원으로 선두.

기대:
- B가 AutoBid max 100,000원 설정 → A 선두 유지, currentPrice = 100,000, B EXHAUSTED, B의 Bid 없음
- B가 100,000원 수동입찰 → 같은 결과, 응답은 `200` + `acceptedBid: null`
- Bid 0건에서 A와 B가 동시에 max 100,000원을 설정하면 먼저 락을 잡은 쪽이 선두이고 currentPrice = 100,000

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

### C08-1. 시작 경계와 Scheduler 지연
저장 status가 READY로 남은 채 startAt이 지난 경매에 입찰 worker와 시작 Scheduler를 동시에 실행.

기대:
- now >= startAt이면 입찰 성공, 저장 status는 OPEN
- 시작 Scheduler가 나중에 실행돼도 중복 전이·중복 상태 이벤트 없음
- now < startAt이면 `409 AUCTION_NOT_OPEN`
- API 응답 status는 저장값과 관계없이 논리 상태

### C09. 동일 Idempotency-Key 동시 재요청
동일 사용자가 동일 key와 동일 요청으로 여러 번 동시 호출.

기대:
- 실제 명령 수행 1회
- IdempotencyRequest 1건
- 동일 요청 재전송은 기존 성공 결과 재사용 (`Idempotency-Replayed: true`)
- 앞선 요청이 실패해 롤백되면 대기하던 요청이 그대로 실행되고 기록은 그 결과로 1건

같은 key에 다른 requestHash를 보내면 409 Conflict. 같은 key와 같은 body로 다른 경매에 입찰해도 경로가 달라 409.

### C10. Scheduler / 신뢰점수 중복 실행
동일 Auction 종료 및 동일 Trade NO_RESPONSE 처리를 여러 worker가 동시에 시도.

기대:
- Trade 1건: UNIQUE(auctionId)
- TrustHistory 1건: UNIQUE(tradeId, userId, reason)
- 신뢰점수 delta 1회만 반영
- Notification도 dedupeKey 기준 1건
- EXPIRED / 자동 완료 처리도 같은 Trade에 대해 효과 1회
- 자동 이용 정지 1건: UNIQUE(triggerTradeId)

### C11. 완료 응답 기한 경계
completionDeadline 경계에서 상대방의 확인/거절 worker와 기한 Scheduler를 동시에 실행.

기대:
- now < completionDeadline: 확인/거절 가능
- now >= completionDeadline: 확인/거절 거절, Scheduler가 자동 완료
- 최종 상태는 정확히 하나 (COMPLETED 또는 IN_PROGRESS/EXPIRED)
- TRADE_COMPLETED TrustHistory 중복 없음
- tradeDeadline 이후 연장 구간의 거절은 IN_PROGRESS가 아니라 EXPIRED

### C12. 연속 실패 3회째 동시 발생
실패 2회가 누적된 사용자에게 서로 다른 Trade의 포기와 미응답 처리가 동시에 일어남.

기대:
- 두 실패 모두 TrustHistory로 반영
- 자동 정지는 정확히 1건
- 정지 이후 입찰·AutoBid 설정·경매 생성은 `403 USER_RESTRICTED`

### C13. 상품 수정 vs 시작·첫 입찰
startAt 경계에서 상품 수정 worker와 입찰 worker를 동시에 실행.

기대:
- 입찰이 먼저 커밋되면 상품 수정은 `409 PRODUCT_LOCKED_AUCTION_STARTED`
- 상품 수정이 먼저 커밋되면 입찰은 수정된 내용 이후에 성립
- 입찰이 성립한 뒤 상품 내용이 바뀐 상태는 존재하지 않음

### C14. 회원탈퇴 vs 입찰
같은 사용자의 탈퇴 요청과 입찰·AutoBid 설정을 동시에 실행.

기대:
- WITHDRAWN 사용자가 선두이거나 ACTIVE AutoBid를 가진 상태는 존재하지 않음
- 탈퇴가 먼저면 입찰은 `403 ACCOUNT_WITHDRAWN`
- 입찰이 먼저 커밋되어 선두가 되면 탈퇴는 `409 USER_WITHDRAWAL_BLOCKED`. 입찰 직후 AutoBid에 밀려 선두가 아니라면 탈퇴는 성공할 수 있음

### C15. 같은 사용자 신뢰점수 동시 반영
사용자 X가 판매자인 거래의 완료 확인과, X가 구매자인 다른 거래의 미응답 처리를 동시에 실행.

기대:
- 최종 trustScore = 초기값 + 모든 delta의 합 (갱신 유실 없음)
- 각 TrustHistory.scoreAfter가 적용 순서와 일치
- 두 사용자를 갱신하는 트랜잭션끼리 데드락 없음 (id 오름차순 갱신)

## 공통 불변조건

모든 동시성 테스트 종료 후 다음을 검사합니다.

- Auction.currentPrice는 유효 가격 격자 위에 있음
- leadingBidder는 currentPrice를 만든 최종 상태와 일치
- ACTIVE AutoBid는 경매당 최대 1개이며 있다면 leader의 것
- Bid 금액은 id 순으로 엄격히 증가하고 leadingBid는 최고 금액 Bid
- ENDED Auction에는 종료 이후 생성된 Bid가 없음
- finalized가 아닌 Auction에는 Trade와 winningBid가 없음
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
- 테스트도 운영과 같은 READ COMMITTED 격리 수준으로 실행
- 동시성 테스트의 worker는 각각 독립 Transaction을 사용
- flaky test를 피하기 위해 sleep 기반 동기화보다 CountDownLatch/Barrier 계열을 우선 사용
