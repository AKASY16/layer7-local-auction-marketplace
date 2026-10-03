# 경매 정책 및 비즈니스 규칙

## 입찰

- 수동 입찰과 자동 입찰 모두 지원
- 성립한 Bid는 수정·삭제·철회하지 않음
- 입찰 전 최종 금액과 철회 불가 정책을 명확하게 표시
- 판매자는 본인 경매에 입찰할 수 없음
- 시작가, 수동입찰 금액, AutoBid의 maxAmount는 모두 **서비스 공통 가격단위표의 유효 금액**이어야 함
- 가격단위표는 판매자나 입찰자가 직접 변경하지 않음

## 가격구간별 유효 입찰단위

MVP 기본 정책:

| 가격 구간 | 유효 금액 단위 |
|---|---:|
| 100 ~ 9,999원 | 100원 |
| 10,000 ~ 49,999원 | 500원 |
| 50,000 ~ 99,999원 | 1,000원 |
| 100,000 ~ 499,999원 | 5,000원 |
| 500,000 ~ 999,999원 | 10,000원 |
| 1,000,000원 이상 | 20,000원 |

유효 금액 예시:
- 9,800원 / 9,900원 / 10,000원 / 10,500원
- 49,500원 / 50,000원 / 51,000원
- 99,000원 / 100,000원 / 105,000원

유효하지 않은 금액 예시:
- 9,350원
- 10,300원
- 99,800원
- 103,000원

서버의 `BidIncrementPolicy`는 다음 두 기능을 제공:
- `isValidAmount(amount)`: 해당 금액이 가격단위표에 맞는지 검증
- `nextValidAmount(currentPrice)`: 현재가보다 큰 가장 가까운 유효 입찰금액 계산

경계 처리 예:
- 현재가 9,900원 → 다음 유효 금액 10,000원
- 현재가 10,000원 → 다음 유효 금액 10,500원
- 현재가 49,500원 → 다음 유효 금액 50,000원
- 현재가 99,000원 → 다음 유효 금액 100,000원
- 현재가 100,000원 → 다음 유효 금액 105,000원

## 시작가

- 판매자가 입력한 startPrice도 가격단위표에 맞는 유효 금액이어야 함
- 유효하지 않은 금액은 등록 단계에서 거절
- Frontend는 입력 중 현재 가격구간의 단위를 안내
- 최종 판단은 Backend가 수행

## 수동입찰

수동입찰 금액은 다음 조건을 모두 만족해야 함:
1. Auction이 OPEN
2. 서버 현재시각이 endAt 이전
3. 판매자 본인 입찰이 아님
4. `isValidAmount(amount) == true`
5. 아직 Bid가 없다면 `amount >= startPrice`
6. Bid가 하나 이상이면 `amount >= nextValidAmount(currentPrice)`

따라서 **첫 실제 Bid는 startPrice 자체로 입찰 가능**합니다. 첫 Bid 이후에는 현재가보다 다음 유효 금액 이상이어야 하며, 사용자는 유효한 단위에 맞는 더 높은 금액으로 건너뛸 수 있습니다.

예:
- startPrice 9,000원 / Bid 0건 → 9,000원 첫 입찰 허용
- 첫 Bid 이후 현재가 9,000원 → 다음 최소 유효 금액 9,100원
- 9,100원 → 허용
- 9,500원 → 허용
- 10,000원 → 허용
- 9,350원 → 거절

## 자동입찰

사용자 설정값:
- `maxAmount`: 사용자가 지불할 의사가 있는 최대 입찰 가격

규칙:
- maxAmount 역시 가격단위표에 맞는 유효 금액이어야 함
- 사용자는 상승폭을 직접 설정하지 않음
- 다른 유효 입찰 또는 AutoBid 설정/변경 이벤트가 발생했을 때만 자동입찰 계산
- 경매가 OPEN인 동안 AutoBid가 지속적으로 CPU/Thread를 점유하지 않음
- 서비스 가격단위표를 기준으로 필요한 최소 금액만 자동입찰
- maxAmount를 초과하지 않음
- 같은 maxAmount면 `priorityAt`이 빠른 사용자가 우선
- 최초 등록 시 `priorityAt = now`
- maxAmount 변경 시 `priorityAt = now`
- 최대금액 상향 가능
- 하향은 이미 성립한 currentPrice 미만으로 불가
- 자동입찰 중지 가능
- 이미 성립한 Bid는 설정 변경/중지 후에도 유지

### maxAmount와 가격단위

maxAmount도 유효 단위만 허용하므로 별도의 "마지막 예외 금액" 규칙을 두지 않음.

예:
- 현재가 99,000원 → 다음 유효 금액 100,000원
- AutoBid maxAmount 99,500원 → 애초에 유효하지 않은 설정이므로 거절
- AutoBid maxAmount 100,000원 → 정상
- 현재가 100,000원 → 다음 유효 금액 105,000원
- maxAmount 103,000원 → 유효하지 않아 설정 자체를 거절

이 규칙으로 인해 모든 실제 Bid 금액은 항상 동일한 가격 격자 위에 존재함.

### 설정 UX

자동입찰 설정/변경 전:
- maxAmount를 명확하게 표시
- 현재 가격구간의 유효 단위와 다음 최소 입찰가 표시
- 서비스가 필요한 최소 유효 금액만 자동으로 올린다는 점 안내
- 입력 금액이 유효 단위에 맞지 않으면 즉시 보정 안내
- 사용자가 확인한 뒤 AutoBid 활성화

## AutoBid 경쟁 처리

AutoBid는 이벤트 발생 시 한 번 계산하고 종료함.

### 기본 계산

AutoBid 후보를:
1. maxAmount 내림차순
2. maxAmount가 같으면 priorityAt 오름차순

으로 비교.

최고 maxAmount 사용자를 winner candidate로 선정하고, 두 번째로 강한 경쟁자의 maxAmount를 기준으로 실제 현재가를 계산.

서로 다른 maxAmount:
- `requiredPrice = nextValidAmount(secondHighest.maxAmount)`
- winner.maxAmount는 유효 금액이므로 winner.maxAmount > secondHighest.maxAmount라면 항상 `winner.maxAmount >= requiredPrice`
- 최종가격은 `requiredPrice`

동일 maxAmount:
- priorityAt이 빠른 사용자가 승자
- 최종가격은 동일한 maxAmount

예:
- A max 150,000원
- B max 120,000원
- C max 90,000원
- nextValidAmount(120,000) = 125,000원
- A가 125,000원으로 선두

예:
- A max 100,000원 / priorityAt 12:00
- B max 100,000원 / priorityAt 12:05
- A가 선두, 현재가는 100,000원

### 수동입찰 직후 AutoBid

예:
- 기존 A AutoBid max 100,000원
- 현재가 50,000원
- B가 70,000원을 수동입찰
- nextValidAmount(70,000) = 71,000원
- A max가 충분하므로 A AUTO 71,000원
- 최종 currentPrice = 71,000원

수동입찰도 유효 단위만 허용하므로 비정상 중간금액 예외처리가 필요 없음.

## Bid 이력 저장

- DB에서 가격단위마다 반복 INSERT하며 가상 핑퐁하지 않음
- 한 트랜잭션 안에서 최종 경쟁 결과를 계산
- 가격 결정에 실제로 필요한 Bid만 저장
- 가상의 중간 자동입찰 단계는 모두 Bid 이력으로 만들지 않음
- 계산이 끝나고 Commit되면 WebSocket / Push 전달

## 동시성 처리

동일 Auction의 다음 작업은 모두 Auction row 기준으로 직렬화:
- 수동입찰
- AutoBid 신규 설정
- AutoBid maxAmount 변경
- AutoBid 중지
- 종료 Scheduler

1차 구현은 `PESSIMISTIC_WRITE` 사용.

개념 흐름:
```text
BEGIN
  → Auction SELECT ... FOR UPDATE
  → 상태/시간/금액단위 검증
  → 수동 Bid 또는 AutoBid 설정 반영
  → AutoBid 경쟁 계산
  → 필요한 Bid 저장
  → Auction.currentPrice / leadingBidder 갱신
COMMIT
  → AFTER_COMMIT WebSocket / Push
```

## Idempotency / 중복 요청 처리

### HTTP 명령
다음과 같이 중복 실행 시 부작용이 생길 수 있는 명령형 API는 `Idempotency-Key`를 사용:
- 수동입찰
- AutoBid 신규 설정
- AutoBid maxAmount 변경
- AutoBid 중지
- 거래 진행
- 거래 포기
- 거래 완료 요청
- 거래 완료 확인
- 재경매 생성

규칙:
- Frontend는 사용자 액션 1회마다 UUID 기반 `Idempotency-Key` 생성
- 동일 사용자의 동일 scope에서 같은 key가 재전송되면 원래 요청을 다시 실행하지 않음
- 같은 key로 요청 내용이 달라지면 잘못된 key 재사용으로 간주하고 `409 Conflict`
- 요청 주요 필드로 `requestHash`를 만들어 같은 key의 동일 요청인지 검증
- Frontend의 버튼 비활성화는 UX 보조 수단이며, 최종 보장은 Backend/DB가 담당

### Scheduler / 도메인 이벤트
Scheduler나 내부 이벤트에는 HTTP용 Idempotency-Key를 사용하지 않음.
대신 다음 조합으로 중복 실행 방지:
- Auction 종료: Auction 상태검사 + PESSIMISTIC_WRITE
- Trade 생성: `UNIQUE(auctionId)`
- 신뢰점수 반영: `UNIQUE(tradeId, userId, reason)`
- Notification 생성: `dedupeKey UNIQUE`

## 판매자 취소

- `READY`: 취소 가능
- `OPEN`: 입찰 0건이면 취소 가능
- 한 건이라도 입찰이 발생하면 임의 취소 불가

## 예약 및 종료

- 예약경매 지원
- `startAt` 전 `READY`
- `startAt` 도달 시 `OPEN`
- `endAt` 도달 시 `ENDED`
- 종료 직전 입찰에 따른 시간 연장 없음
- 경매 종료를 위해 Auction별 Thread/Timer를 점유하지 않음
- Scheduler가 `status + startAt/endAt` 인덱스를 기준으로 전이 대상 Auction을 조회
- 입찰과 종료 Scheduler는 동일 Auction에 대해 같은 쓰기 락 규칙을 사용
- 입찰 가능 시간은 서버 기준 `startAt <= now < endAt`
- 클라이언트가 버튼을 누른 시각이나 브라우저 카운트다운은 판정 근거로 사용하지 않음
- 입찰 처리 시 Auction 쓰기 락을 획득한 뒤 서버 현재시각을 다시 읽어 마감 여부를 검증
- DB status가 아직 OPEN이어도 `now >= endAt`이면 입찰 거절
- Scheduler가 실제로 ENDED 상태를 기록하는 시점은 endAt보다 조금 늦을 수 있으나, 논리적 종료시점은 항상 endAt
- 애플리케이션 시간 조회는 직접 `now()`를 흩어 쓰지 않고 주입된 `Clock`을 사용
- 애플리케이션 내부 시간 기준은 `Instant`/UTC로 통일하고 화면에서 사용자 지역시간으로 변환

## 상품 내용

- 입찰 1건 이상이면 기존 핵심 상품정보 수정/삭제 불가
- 판매자는 기존 내용을 덮어쓰지 않고 `ProductAppend` 등록
- 1회 최대 200자

## 낙찰

- 차순위 승계 없음
- 입찰자가 없으면 유찰, Trade 생성 안 함
- 낙찰자가 있으면 Trade 생성
- 낙찰자 응답 기한 24시간
- Trade.responseDeadline은 Scheduler 실제 처리시각이 아니라 `Auction.endAt + 24시간`으로 계산

## 재경매

- 기존 Auction을 다시 OPEN으로 되돌리지 않음
- 판매자가 새 Auction 생성
- `relistedFromAuctionId`로 이전 경매 참조
- 기존 Bid / AutoBid / Trade 이력은 변경하지 않음

## 즉시구매

MVP 제외.
