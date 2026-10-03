# Scheduler

경매 시작·종료와 거래 기한을 처리하는 Scheduler의 실행 규칙입니다. 정합성은 논리 시간 판정과 락이 보장하므로, Scheduler가 늦게 실행되어도 결과가 틀리지는 않습니다. 실행 주기는 "논리적으로 끝난 뒤 후처리가 반영되기까지 사용자가 얼마나 기다리는가"를 정하는 값입니다.

## 작업 목록

| 작업 | 조회 조건 | 주기 | 처리 |
|---|---|---|---|
| 경매 시작 | `status = READY AND startAt <= now AND endAt > now` | 1초 | READY → OPEN. 쓰기 요청이 먼저 바꿨으면 건너뜀 |
| 경매 종료 | `status IN (READY, OPEN) AND endAt <= now` | 1초 | ENDED, winningBid 확정, Trade 생성, 알림 |
| 낙찰 미응답 | `status = AWAITING_RESPONSE AND responseDeadline <= now` | 1분 | NO_RESPONSE, 신뢰점수, 연속 실패·정지 판정 |
| 거래 기한 만료 | `status = IN_PROGRESS AND tradeDeadline <= now` | 1분 | EXPIRED |
| 완료 자동 확정 | `status = COMPLETION_REQUESTED AND completionDeadline <= now` | 1분 | COMPLETED, 신뢰점수, 상품 SOLD |
| 기한 임박 알림 | 아래 "기한 임박 알림" 참고 | 10분 | TRADE_DEADLINE_SOON |
| 정리 배치 | 24시간 지난 Idempotency 기록, 만료된 Refresh Token | 1시간 | 삭제 |

## 실행 규칙

- 조회는 인덱스를 타는 조건으로 하고 한 번에 최대 100건씩 가져옵니다.
- 대상 하나마다 별도 트랜잭션으로 처리합니다. 락을 잡은 뒤 상태와 시간을 다시 확인하고, 이미 처리된 대상은 건너뜁니다 ([락 순서와 트랜잭션 규칙](locking.md)).
- 한 대상의 실패가 다른 대상의 처리를 막지 않도록 예외는 대상 단위로 기록하고 다음 대상으로 넘어갑니다.
- 이전 실행이 끝나기 전에 다음 실행이 시작되지 않도록 fixedDelay로 실행합니다.
- 처리 지연(`now - endAt` 등)과 처리 건수를 메트릭으로 기록합니다.

## 기한 임박 알림

- 낙찰 응답 기한 3시간 전
- 거래 기한 24시간 전 (IN_PROGRESS / COMPLETION_REQUESTED)
- 완료 응답 기한 3시간 전 (COMPLETION_REQUESTED)
- `dedupeKey = TRADE_DEADLINE_SOON:{tradeId}:{기한 종류}:{기한 시각}`으로 한 번만 생성합니다. 완료 요청이 거절된 뒤 다시 오면 기한 시각이 달라지므로 새로 생성됩니다.

## 서버를 여러 대로 늘릴 때

MVP는 단일 서버를 전제로 합니다. 여러 대에서 같은 Scheduler가 돌아도 락과 상태 확인 덕분에 효과는 한 번만 반영되지만, 같은 대상을 중복으로 조회하는 낭비가 생깁니다. 서버를 늘릴 때 `FOR UPDATE SKIP LOCKED`로 대상을 나눠 가져가거나 ShedLock 같은 실행 잠금을 도입합니다.
