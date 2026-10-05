# 락 순서와 트랜잭션 규칙

경매·상품·거래·사용자 데이터를 바꾸는 쓰기 작업의 락 획득 규칙입니다. 동시성 버그와 데드락은 대부분 작업마다 "어떤 락을 어떤 순서로 잡는가"가 달라서 생기므로, 모든 쓰기 경로는 이 문서의 규칙을 따릅니다.

## 격리 수준

애플리케이션 트랜잭션 격리 수준은 `READ COMMITTED`를 사용합니다.

- MySQL 기본값인 REPEATABLE READ는 트랜잭션의 첫 일반 SELECT 시점에 스냅샷을 고정합니다. 락을 잡기 전에 한 번이라도 조회하면, 락을 잡은 뒤 잠그지 않은 다른 테이블을 일반 SELECT로 읽을 때 락 이전 데이터를 보게 됩니다.
- READ COMMITTED는 문장마다 최신 커밋을 읽으므로 "락 후 재검증"이 항상 최신 상태를 봅니다.
- 직렬화와 정합성은 격리 수준이 아니라 아래 비관적 락이 보장합니다.
- gap lock이 줄어 UNIQUE 검사나 범위 조회에서 생기는 데드락도 줄어듭니다.
- MySQL 8.4의 기본 binlog 형식은 ROW라 READ COMMITTED 사용에 제약이 없습니다.
- Testcontainers 통합·동시성 테스트도 같은 격리 수준으로 실행합니다.

## 전역 락 순서

```text
Product → Auction → Trade → User (여러 명이면 id 오름차순)
```

- 뒤 순서의 락을 쥔 채로 앞 순서의 락을 요청하지 않습니다.
- 락은 `SELECT ... FOR UPDATE`(PESSIMISTIC_WRITE) 또는 `SELECT ... FOR SHARE`로 잡고 트랜잭션 끝까지 유지합니다.

## 작업별 락

| 작업 | 잡는 락 |
|---|---|
| 경매 생성·재경매 | Product |
| 상품 수정·이미지 추가/삭제/순서 변경 | Product → 그 상품의 READY/OPEN Auction |
| 상품 삭제 | Product |
| 수동입찰·AutoBid 설정/변경 | Auction → 입찰자 User(FOR SHARE) |
| AutoBid 중지·판매자 경매 취소·ProductAppend | Auction |
| 경매 시작·종료 Scheduler | Auction (Trade는 INSERT만) |
| Trade 명령·Trade 기한 Scheduler | Product → Trade → (신뢰점수·정지가 바뀌면) 당사자 User |
| 회원탈퇴 | User |

Trade 명령은 Product를 바꾸지 않는 경우(진행, 포기 등)에도 Product부터 잡습니다. 완료 시 Product를 SOLD로 바꾸는 경로와 같은 순서를 쓰게 해서 규칙을 하나로 유지하기 위함입니다.

Scheduler는 대상 하나마다 별도 트랜잭션으로 처리합니다. 여러 Auction이나 Trade를 한 트랜잭션에서 처리하면 락을 오래 쥐게 되고, 하나의 실패가 전체를 롤백합니다.

## 락 전 조회와 락 후 재검증

락 순서를 지키려면 요청에 없는 상위 ID를 먼저 찾아야 할 때가 있습니다. 예를 들어 Trade 명령은 tradeId만 받지만 Product부터 잠가야 합니다.

- 락 전 조회는 상위 ID를 찾는 용도로만 사용하고, 그 결과로 판단하지 않습니다.
- 락 전 조회는 ID만 반환하는 프로젝션 쿼리로 합니다. 엔티티로 조회하면 영속성 컨텍스트에 올라가고, 이후 같은 엔티티를 `@Lock`으로 조회해도 Hibernate는 이미 관리 중인 엔티티의 필드를 DB 값으로 다시 채우지 않아 재검증이 옛 값을 보게 됩니다. 불가피하게 엔티티를 먼저 읽었다면 락과 함께 refresh합니다.
- 상태·권한·기한 등 모든 판단은 락을 잡은 뒤 다시 읽은 값으로 합니다.
- 락 전에 찾은 ID 관계는 바뀌지 않는 관계여야 합니다. `trade.auctionId`, `auction.productId`는 생성 후 바뀌지 않으므로 사용할 수 있습니다. "상품의 현재 READY/OPEN Auction"처럼 바뀔 수 있는 관계는 상위 락(Product)을 잡은 뒤에 찾습니다.

예: Trade 완료 확인

```text
1. tradeId → auctionId → productId를 ID 프로젝션으로 조회
2. Product FOR UPDATE
3. Trade FOR UPDATE, 상태·당사자·기한 재검증
4. COMPLETED 전이, Product SOLD
5. seller/buyer 신뢰점수를 id 오름차순으로 원자 갱신
```

## 작업별 세부 규칙

### 상품 수정

- 핵심정보와 이미지는 해당 Product에 논리적으로 시작된 경매가 없고, 과거 Bid가 0건일 때만 수정할 수 있습니다.
  - 논리적으로 시작된 경매: 저장 status가 OPEN이거나, READY이면서 `now >= startAt`
- Product 락으로 새 경매 생성을 막고, READY/OPEN Auction 락으로 첫 입찰·시작 전이와 직렬화합니다.
- 락은 트랜잭션이 겹치는 순간만 막을 뿐, 구매자가 페이지를 연 뒤 입찰하기까지의 사이에 내용이 바뀌는 것은 막지 못합니다. 그래서 "진행 중인 경매의 내용은 바뀌지 않는다"를 정책으로 둡니다. OPEN이면서 입찰 0건인 경매를 고치려면 경매를 취소한 뒤 수정하고 새로 등록합니다.

### 상품 삭제

- ACTIVE 상품만 삭제할 수 있습니다. SOLD 상품은 거래 기록 보존을 위해 삭제하지 않습니다.
- Product 락을 잡은 뒤 READY/OPEN Auction과 진행 중 Trade(AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED)가 없는지 확인합니다.
- Trade 명령도 Product부터 잡으므로, 거래 진행 중인 상품이 삭제되는 경쟁은 생기지 않습니다.

### 입찰과 회원탈퇴

- 입찰·AutoBid 설정은 Auction 락을 잡은 뒤 입찰자 User를 FOR SHARE로 읽어 ACTIVE 여부와 거래 참여 정지 여부를 확인합니다.
- 회원탈퇴는 User를 FOR UPDATE로 잡은 뒤 진행 중 의무(선두 Bid, ACTIVE AutoBid, 진행 중 Trade 등)를 검사합니다.
- 탈퇴가 먼저 락을 잡으면 입찰은 대기한 뒤 WITHDRAWN을 보고 거절되고, 입찰이 먼저면 탈퇴는 대기한 뒤 새로 커밋된 Bid를 보고 거절됩니다.

### 신뢰점수와 이용 정지

- 신뢰점수는 `UPDATE users SET trust_score = trust_score + ? WHERE id = ?` 원자 갱신으로 반영하고, 같은 트랜잭션에서 다시 읽어 TrustHistory.scoreAfter를 기록합니다. 엔티티 필드를 읽고 더해서 저장하면 같은 사용자의 다른 거래가 동시에 처리될 때 갱신이 유실됩니다.
- 두 사용자를 갱신할 때는 id 오름차순으로 갱신합니다.
- 연속 실패 판정과 자동 정지 생성은 원자 갱신이 잡은 User row 락을 쥔 상태에서 수행합니다. 같은 사용자의 실패가 동시에 처리돼도 정지는 한 번만 생깁니다.
- 정지를 거는 트랜잭션은 Trade 락을 쥐고 있으므로 다른 경매의 AutoBid를 끄지 않습니다. 거기서 Auction 락을 잡으면 전역 순서를 거스르게 됩니다. 정지된 사용자의 AutoBid는 다음 경쟁 이벤트에서 Auction 락 안에서 STOPPED로 바꿉니다.

## 검증

[동시성 테스트 계획](concurrency-testing.md)의 C13~C15가 이 문서의 규칙을 검증합니다.
