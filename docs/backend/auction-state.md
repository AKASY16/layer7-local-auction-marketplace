# Auction / Trade 상태 모델

## Auction

상태는 `READY / OPEN / ENDED / CANCELED`입니다.

```text
READY
  │ startAt 도달
  ▼
OPEN
  │ endAt 도달
  ▼
ENDED

READY ───────────────→ CANCELED
OPEN ── 입찰 0건 ───→ CANCELED
```

- 예약경매를 MVP에 포함합니다.
- startAt 이전에는 입찰할 수 없습니다.
- Scheduler가 READY → OPEN, OPEN → ENDED 전이를 처리합니다.
- Auction별 Timer/Thread를 유지하지 않고 `status + startAt/endAt` 조건으로 전이 대상을 조회합니다.
- 입찰 처리와 종료 Scheduler는 동일 Auction row에 대해 쓰기 락 규칙을 공유해 경계시각 경쟁 상태를 직렬화합니다.
- 논리적 입찰 가능 시간은 `startAt <= now < endAt`입니다.
- 서버가 Auction 쓰기 락을 획득한 뒤의 현재시각을 기준으로 판정합니다.
- `status = OPEN`이어도 `now >= endAt`이면 입찰할 수 없습니다.
- Scheduler의 실제 상태 전환이 약간 늦어져도 endAt 이후 입찰은 허용되지 않습니다.
- 애플리케이션 시간 판정은 주입된 `Clock`과 `Instant` 기준으로 통일합니다.
- ENDED + leadingBidderId == null 이면 유찰입니다.
- ENDED + leadingBidderId != null 이면 낙찰입니다.
- 낙찰 시에만 Trade를 생성합니다.
- 낙찰 Trade의 responseDeadline은 `Auction.endAt + 24시간`으로 계산합니다.

## Trade

상태는 `AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED / DECLINED / NO_RESPONSE / CANCELED / EXPIRED`입니다.

```text
AWAITING_RESPONSE
  ├─ 낙찰자 거래 진행 ──────────→ IN_PROGRESS
  ├─ 낙찰자 거래 포기 ──────────→ DECLINED
  ├─ 판매자 취소 ───────────────→ CANCELED
  └─ responseDeadline 도달 ─────→ NO_RESPONSE

IN_PROGRESS
  ├─ 한쪽이 완료 요청 ──────────→ COMPLETION_REQUESTED
  ├─ 한쪽이 취소 ───────────────→ CANCELED
  └─ tradeDeadline 도달 ────────→ EXPIRED

COMPLETION_REQUESTED
  ├─ 상대방 확인 ───────────────→ COMPLETED
  ├─ completionDeadline 도달 ───→ COMPLETED (자동)
  ├─ 상대방 거절 ───────────────→ IN_PROGRESS (tradeDeadline 이후면 EXPIRED)
  └─ 한쪽이 취소 ───────────────→ CANCELED (tradeDeadline 이전만)
```

- `responseDeadline = endAt + 24시간`, `tradeDeadline = endAt + 7일`, `completionDeadline = max(tradeDeadline, completionRequestedAt + 24시간)`입니다.
- 완료 요청을 받은 상대방은 요청 시점부터 최소 24시간을 보장받으므로 가장 긴 거래 기간은 endAt + 8일입니다.
- 완료 요청자는 seller 또는 buyer 중 한 명입니다.
- 본인이 생성한 완료 요청을 본인이 승인할 수 없습니다.
- COMPLETED 시 판매자와 구매자 모두 신뢰점수 +2입니다.
- DECLINED 시 구매자 -5, NO_RESPONSE 시 구매자 -10, CANCELED 시 취소한 쪽 -5입니다. EXPIRED는 변동이 없습니다.
- DECLINED / NO_RESPONSE / 본인 CANCELED가 COMPLETED 없이 3회 연속되면 7일간 거래 참여 정지입니다.

## 재경매

거래가 DECLINED / NO_RESPONSE / CANCELED / EXPIRED로 실패하면 기존 Auction은 ENDED 상태로 보존합니다.

판매자가 재경매를 선택하면 동일 Product에 새 Auction을 생성하고 `relistedFromAuctionId`로 이전 Auction을 참조합니다.
