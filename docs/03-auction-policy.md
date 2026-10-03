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

## 금액 상한과 경매 기간

- startPrice, 수동입찰 금액, AutoBid maxAmount는 모두 10,000,000원 이하
  - 일상·생활용품 중심 서비스 기준의 상한이며, 장난성 고액 AutoBid로 경매를 망치는 것을 막기 위함
- 경매 기간(`endAt - 실제 startAt`)은 1시간 이상 7일 이하
- 예약 시작 `startAt`은 생성 시점부터 7일 이내
- 재경매에도 같은 제한을 적용
- 변경 가능한 서비스 정책이므로 DB CHECK가 아니라 도메인 코드에서 검증

## 시작가

- 판매자가 입력한 startPrice도 가격단위표에 맞는 유효 금액이어야 함
- 유효하지 않은 금액은 등록 단계에서 거절
- Frontend는 입력 중 현재 가격구간의 단위를 안내
- 최종 판단은 Backend가 수행

## 수동입찰

수동입찰 금액은 다음 조건을 모두 만족해야 함:
1. Auction이 논리적으로 OPEN: 저장 status가 READY/OPEN이고 `startAt <= now < endAt`
2. 판매자 본인 입찰이 아님
3. 현재 선두가 아님
4. `isValidAmount(amount) == true`
5. 아직 Bid가 없다면 `amount >= startPrice`
6. Bid가 하나 이상이면 `amount >= nextValidAmount(currentPrice)`

따라서 **첫 실제 Bid는 startPrice 자체로 입찰 가능**합니다. 첫 Bid 이후에는 현재가보다 다음 유효 금액 이상이어야 하며, 사용자는 유효한 단위에 맞는 더 높은 금액으로 건너뛸 수 있습니다.

현재 선두는 수동입찰로 자기 가격을 올릴 수 없습니다. 상한을 올리고 싶다면 AutoBid를 사용합니다. 선두가 경쟁자 없이 가격만 올리는 상황을 막고, 아래 AutoBid 경쟁 처리의 불변조건을 유지하기 위한 규칙입니다.

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
- AutoBid 설정/변경 요청이 성공하면 같은 Transaction 안에서 즉시 경쟁에 참여
- Bid가 0건일 때 첫 AutoBid가 설정되면 startPrice의 실제 AUTO Bid를 생성
- 경매가 OPEN인 동안 AutoBid가 지속적으로 CPU/Thread를 점유하지 않음
- 서비스 가격단위표를 기준으로 필요한 최소 금액만 자동입찰
- maxAmount를 초과하지 않음
- 도전자의 금액이 현재 선두의 상한과 같으면 현재 선두가 우선 (아래 AutoBid 경쟁 처리 참고)
- AutoBid는 경매가 OPEN일 때만 설정 가능하며 READY 중 사전 등록은 지원하지 않음
- 최대금액 상향 가능
- 하향은 이미 성립한 currentPrice 미만으로 불가
- 자동입찰 중지 가능
- 이미 성립한 Bid는 설정 변경/중지 후에도 유지
- 현재 선두가 AutoBid를 중지해도 leadingBid와 currentPrice는 내려가지 않음
- 현재 선두가 아니고 maxAmount로 다음 유효 입찰가를 만들 수 없게 되면 EXHAUSTED
- 선두 상태에서 currentPrice == maxAmount인 경우에는 ACTIVE 유지, 이후 상회되면 EXHAUSTED

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

### 불변조건

모든 경쟁 이벤트는 Auction row 락 안에서 직렬화되므로, 각 트랜잭션이 커밋된 시점에는 다음이 항상 성립함.
- ACTIVE AutoBid는 0개 또는 1개이며, 있다면 현재 선두의 것
- Bid 금액은 경매 안에서 엄격히 증가하고, leadingBid는 항상 최고 금액 Bid

선두가 아닌 AutoBid가 다음 유효 입찰가를 만들 수 있었다면 그 트랜잭션 안에서 이미 반응했을 것이고, 만들 수 없다면 EXHAUSTED가 되기 때문입니다. 따라서 경쟁 계산은 항상 **도전자 1명과 현재 선두 1명**의 비교로 끝나며, 여러 AutoBid를 maxAmount 순으로 정렬할 필요가 없습니다.

READY 중 AutoBid 사전 등록을 허용하면 startAt 시점에 ACTIVE AutoBid가 여러 개 생겨 이 불변조건이 깨집니다. 사전 등록을 도입한다면 경쟁 계산과 동액 우선순위를 다시 설계해야 합니다.

### 판정

- 도전자 금액 `a`: 수동입찰이면 입찰 금액 X, AutoBid 설정·변경이면 maxAmount M
- 선두 상한 `C`: 현재 선두에게 ACTIVE AutoBid가 있으면 그 maxAmount, 없으면 현재 leadingBid 금액(= currentPrice). 선두가 거래 참여 정지 중이면 그 AutoBid를 이 트랜잭션에서 STOPPED로 바꾸고 currentPrice로 취급 (아래 이용 정지 참고)
- `a > C`면 도전자 승, `a <= C`면 현재 선두 승
- Bid가 0건이면 선두가 없으므로 도전자가 바로 선두

동액(`a == C`)이면 현재 선두가 이깁니다. 선두의 상한은 항상 도전자보다 먼저 확정된 약속이므로, "먼저 확정한 쪽 우선" 원칙이 AutoBid끼리든 수동입찰 대 AutoBid든 같은 규칙으로 적용됩니다. 별도의 우선순위 시각(priorityAt)은 저장하지 않습니다.

### Bid 저장 규칙

패자가 실제로 버틴 금액과 승자의 최종가, 이 두 개만 Bid로 저장합니다. 단, 패자 금액이 이미 currentPrice와 같거나(이미 Bid가 있음) 승자 금액과 같으면 생략합니다. 저장 순서는 패자 → 승자입니다.

| 이벤트 | 조건 | 저장 Bid | 결과 |
|---|---|---|---|
| 수동 X | Bid 0건 | 도전자 MANUAL X | 도전자 선두 |
| 수동 X | X > C | (C > currentPrice일 때만) 선두 AUTO C → 도전자 MANUAL X | 도전자 선두, 기존 선두 AutoBid EXHAUSTED |
| 수동 X | X == C | 선두 AUTO C | 선두 유지, 도전자 Bid 없음 |
| 수동 X | X < C | 도전자 MANUAL X → 선두 AUTO nextValidAmount(X) | 선두 유지 |
| AutoBid M | Bid 0건 | 도전자 AUTO startPrice | 도전자 선두 |
| AutoBid M | M > C | (C > currentPrice일 때만) 선두 AUTO C → 도전자 AUTO nextValidAmount(C) | 도전자 선두, 기존 선두 AutoBid EXHAUSTED |
| AutoBid M | M == C | 선두 AUTO C | 선두 유지, 도전자 AutoBid EXHAUSTED |
| AutoBid M | M < C | 도전자 AUTO M → 선두 AUTO nextValidAmount(M) | 선두 유지, 도전자 AutoBid EXHAUSTED |
| 선두 본인의 AutoBid 설정·변경·중지 | - | 없음 | 가격 변화 없음 |

- C, X, M은 모두 같은 가격 격자 위에 있으므로 `C > X`이면 항상 `C >= nextValidAmount(X)`이고, 선두의 응답 금액이 상한을 넘지 않음
- 한 이벤트에서 생기는 Bid는 최대 2건
- 같은 트랜잭션 안의 Bid 순서를 보존하기 위해 이력은 id 순으로 정렬

### 예시

startPrice 9,000원에서 C(max 90,000원) → B(max 120,000원) → A(max 150,000원) 순서로 설정:
- C 설정: Bid 0건 → C AUTO 9,000, C 선두
- B 설정: 120,000 > C 상한 90,000 → C AUTO 90,000 → B AUTO 91,000, C EXHAUSTED
- A 설정: 150,000 > B 상한 120,000 → B AUTO 120,000 → A AUTO 125,000, B EXHAUSTED

설정 순서가 달라지면 저장되는 Bid와 bidCount는 달라지지만, 최종 선두(A)와 currentPrice(125,000원)는 같습니다. A가 먼저 선두가 된 뒤라면 C의 90,000원은 `nextValidAmount(currentPrice)`에 못 미쳐 설정 단계에서 거절됩니다.

동액:
- A가 AutoBid max 100,000원으로 선두
- B가 AutoBid max 100,000원 설정 → 동액이므로 A AUTO 100,000 저장, A 선두 유지, B EXHAUSTED
- B가 수동으로 100,000원을 입찰해도 결과는 같음. B의 Bid는 남지 않고 A가 100,000원으로 선두

### 수동입찰 직후 AutoBid

예:
- 기존 A AutoBid max 100,000원, A 선두, 현재가 50,000원
- B가 70,000원을 수동입찰
- 70,000 < A 상한 100,000 → B MANUAL 70,000 → A AUTO 71,000
- 최종 currentPrice = 71,000원

수동입찰도 유효 단위만 허용하므로 비정상 중간금액 예외처리가 필요 없음.

## Bid 이력 저장

- DB에서 가격단위마다 반복 INSERT하며 가상 핑퐁하지 않음
- 한 트랜잭션 안에서 최종 경쟁 결과를 계산
- 위 Bid 저장 규칙에 따라 패자가 버틴 금액과 승자의 최종가만 저장
- 가상의 중간 자동입찰 단계는 Bid 이력으로 만들지 않음
- bidCount는 저장된 Bid row 수
- 계산이 끝나고 Commit되면 WebSocket / Push 전달

## 동시성 처리

동일 Auction의 다음 작업은 모두 Auction row 기준으로 직렬화:
- 수동입찰
- AutoBid 신규 설정
- AutoBid maxAmount 변경
- AutoBid 중지
- 판매자 경매 취소
- ProductAppend 등록
- 경매 시작·종료 Scheduler

경매 생성과 재경매는 아직 Auction row가 없으므로 Product row 락으로 직렬화합니다. 작업별 락 대상, 전역 락 순서(Product → Auction → Trade → User), 락 전 조회 규칙, 격리 수준(READ COMMITTED)은 [락 순서와 트랜잭션 규칙](backend/locking.md)을 따릅니다.

1차 구현은 `PESSIMISTIC_WRITE` 사용.

개념 흐름:
```text
BEGIN
  → Auction SELECT ... FOR UPDATE
  → 입찰자 User SELECT ... FOR SHARE (탈퇴·정지 여부)
  → 상태/시간/금액단위 검증
  → 수동 Bid 또는 AutoBid 설정 반영
  → AutoBid 경쟁 계산
  → 필요한 Bid 저장
  → Auction.currentPrice / leadingBid 갱신
COMMIT
  → AFTER_COMMIT WebSocket / Push
```

## Idempotency / 중복 요청 처리

### HTTP 명령
다음과 같이 중복 실행 시 부작용이 생길 수 있는 명령형 API는 `Idempotency-Key`를 사용:
- 경매 생성
- 수동입찰
- AutoBid 신규 설정 / maxAmount 변경
- AutoBid 중지
- 거래 진행
- 거래 포기
- 거래 취소
- 거래 완료 요청
- 거래 완료 확인
- 거래 완료 거절
- 재경매 생성
- ProductAppend 등록

규칙:
- Frontend는 사용자 액션 1회마다 UUID 기반 `Idempotency-Key` 생성
- 동일 사용자의 동일 scope에서 같은 key가 재전송되면 원래 요청을 다시 실행하지 않음
- 같은 key로 요청 내용이 달라지면 잘못된 key 재사용으로 간주하고 `409 Conflict`
- 요청 주요 필드로 `requestHash`를 만들어 같은 key의 동일 요청인지 검증
- Frontend의 버튼 비활성화는 UX 보조 수단이며, 최종 보장은 Backend/DB가 담당
- 트랜잭션 경계, 실패한 요청의 재시도, 보관 기간은 [API 명세 공통 규칙](05-api-spec.md#idempotency)을 따름

### Scheduler / 도메인 이벤트
Scheduler나 내부 이벤트에는 HTTP용 Idempotency-Key를 사용하지 않음.
대신 다음 조합으로 중복 실행 방지:
- Auction 종료: Auction 상태검사 + PESSIMISTIC_WRITE
- Trade 생성: `UNIQUE(auctionId)`
- Trade 기한 처리: Trade 상태검사 + PESSIMISTIC_WRITE
- 신뢰점수 반영: `UNIQUE(tradeId, userId, reason)`
- 자동 이용 정지: `UNIQUE(triggerTradeId)`
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
- 저장된 status는 Scheduler가 뒤따라 맞추는 값이고, 시간 경계의 기준은 startAt/endAt. 판정과 API 응답은 서버시간 기준 논리 상태를 사용 ([Auction / Trade 상태 모델](backend/auction-state.md))
- 입찰 가능 시간은 서버 기준 `startAt <= now < endAt`
- 클라이언트가 버튼을 누른 시각이나 브라우저 카운트다운은 판정 근거로 사용하지 않음
- 입찰 처리 시 Auction 쓰기 락을 획득한 뒤 서버 현재시각을 다시 읽어 판정
- 저장 status가 아직 READY여도 `now >= startAt`이면 입찰 가능. 부작용이 없는 전이이므로 그 트랜잭션에서 OPEN으로 바꿈
- 저장 status가 아직 OPEN이어도 `now >= endAt`이면 입찰 거절. 종료 전이는 winningBid·Trade·알림이 따라붙으므로 종료 Scheduler만 수행
- Scheduler가 실제로 ENDED 상태를 기록하는 시점은 endAt보다 조금 늦을 수 있으나, 논리적 종료시점은 항상 endAt
- 애플리케이션 시간 조회는 직접 `now()`를 흩어 쓰지 않고 주입된 `Clock`을 사용
- 애플리케이션 내부 시간 기준은 `Instant`/UTC로 통일하고 화면에서 사용자 지역시간으로 변환

## 상품 내용

- 핵심 상품정보와 이미지는 경매가 논리적으로 시작되기 전이고 과거 Bid가 0건일 때만 수정 가능
- OPEN 경매는 입찰이 없어도 수정 불가. 고치려면 경매를 취소한 뒤 수정하고 새로 등록
- 입찰 1건 이상이 발생한 Product는 이후에도 핵심 상품정보 수정/삭제 불가
- 판매자는 기존 내용을 덮어쓰지 않고 `ProductAppend` 등록
- 1회 최대 200자

## 낙찰

- 차순위 승계 없음
- 입찰자가 없으면 유찰, Trade 생성 안 함
- 낙찰자가 있으면 Trade 생성
- 낙찰자 응답 기한 24시간
- Trade.responseDeadline은 Scheduler 실제 처리시각이 아니라 `Auction.endAt + 24시간`으로 계산

## 거래 기한과 취소

- 거래 기한 `tradeDeadline = Auction.endAt + 7일`. 거래 진행 중의 완료 요청과 취소는 이 기한 안에서만 가능
- 완료 요청을 받은 상대방은 요청 시점부터 최소 24시간을 보장받음: `completionDeadline = max(tradeDeadline, completionRequestedAt + 24시간)`
- tradeDeadline 이후에는 완료 요청을 받은 상대방의 확인/거절만 허용
- 가장 긴 거래 기간은 endAt + 8일. 기한 직전에 요청과 거절을 반복해도 마지막 요청 하나만 연장됨
- 기한 처리 (Scheduler):
  - IN_PROGRESS가 tradeDeadline에 도달 → `EXPIRED`, 신뢰점수 변동 없음
  - COMPLETION_REQUESTED가 completionDeadline에 도달 → 자동 `COMPLETED`. 요청자가 완료를 주장했고 상대방이 기한 안에 거절하지 않았다고 봄
  - tradeDeadline 이후 연장 구간에서 거절하면 IN_PROGRESS로 돌아가지 않고 바로 `EXPIRED`
- 일방 취소:
  - 판매자: AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED에서 가능
  - 구매자: IN_PROGRESS / COMPLETION_REQUESTED에서 가능 (AWAITING_RESPONSE에서는 거래 포기 사용)
  - 결과는 `CANCELED`, 취소한 쪽 신뢰점수 -5
- EXPIRED는 귀책을 가릴 수단이 없어 페널티를 주지 않음. 거래 진행 후 응답하지 않는 상대를 점수로 제재할 수 없다는 한계가 있으며, 채팅 기록·신고 기능이 생기면 다시 검토

## 이용 정지

- 신뢰점수는 표시용 지표이며 점수만으로 입찰을 막지 않음
- 본인 책임의 거래 실패가 3회 연속되면 7일간 거래 참여 정지
  - 실패: 낙찰 포기(DECLINED), 낙찰 미응답(NO_RESPONSE), 본인이 한 거래 취소(CANCELED)
  - 연속: 그 사이에 본인이 당사자인 거래 완료(COMPLETED)가 없음. EXPIRED는 실패로도 완료로도 세지 않음
  - 정지가 걸리면 실패 횟수는 0부터 다시 셈
- 정지 중 불가: 수동입찰, AutoBid 설정·변경·재활성화, 경매 생성·재경매
- 정지 중 허용: AutoBid 중지, 진행 중 거래의 모든 명령, 상품 수정·내용 추가 등 기존 의무 이행. 이미 성립한 선두 Bid는 유지
- 정지된 사용자의 ACTIVE AutoBid는 정지 시점에 바로 끄지 않음. 정지를 거는 트랜잭션은 거래를 처리하는 중이라 다른 경매의 Auction 락을 잡지 않기 때문. 대신 다음 경쟁 이벤트에서 현재 선두가 정지 상태면 그 AutoBid를 STOPPED로 바꾸고 선두 상한을 currentPrice로 취급
- 정지 해제는 Scheduler 없이 endsAt과 서버시간으로 판정
- 자동 정지는 실패를 만든 트랜잭션 안에서 생성하고, 원인 Trade 기준 UNIQUE로 중복 생성을 막음
- 수동 정지: MVP에는 관리자 API를 두지 않음. 운영자가 DB에 `source = ADMIN` 기록을 직접 생성하며, 신고·관리자 기능과 함께 추후 확장
- 한계: 정지 기준에 닿기 전까지의 실패와 재가입을 통한 초기화는 막지 못함

## 재경매

- 기존 Auction을 다시 OPEN으로 되돌리지 않음
- 판매자가 새 Auction 생성
- `relistedFromAuctionId`로 이전 경매 참조
- 기존 Bid / AutoBid / Trade 이력은 변경하지 않음
- 원 Auction이 finalized ENDED이고 Product가 ACTIVE일 때만 가능 (정산 전에는 Trade가 아직 없으므로 유찰로 판단하지 않음)
- Trade가 없으면 유찰로 재경매 가능
- Trade가 있으면 DECLINED / NO_RESPONSE / CANCELED / EXPIRED일 때만 가능
- AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED 상태에서는 재경매 불가
- 거래 참여 정지 중에는 재경매 불가

## 즉시구매

MVP 제외.
