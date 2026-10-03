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
- ENDED + leadingBidderId == null 이면 유찰입니다.
- ENDED + leadingBidderId != null 이면 낙찰입니다.
- 낙찰 시에만 Trade를 생성합니다.

## Trade

상태는 `AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED / DECLINED / NO_RESPONSE`입니다.

```text
AWAITING_RESPONSE
      │
      ├─ 거래 진행 ──→ IN_PROGRESS
      │                   │
      │                   └─ 판매자/구매자 중 한 명이 완료 요청
      │                               ▼
      │                     COMPLETION_REQUESTED
      │                               │
      │                               ├─ 상대방 확인 ──→ COMPLETED
      │                               └─ 미완료 판단 ─→ IN_PROGRESS
      │
      ├─ 거래 포기 ──→ DECLINED
      └─ 24시간 경과 ─→ NO_RESPONSE
```

- 완료 요청자는 seller 또는 buyer 중 한 명입니다.
- 본인이 생성한 완료 요청을 본인이 승인할 수 없습니다.
- COMPLETED 시 판매자와 구매자 모두 신뢰점수 +2입니다.
- DECLINED 시 구매자 -5, NO_RESPONSE 시 구매자 -10입니다.

## 재경매

거래가 DECLINED 또는 NO_RESPONSE로 실패하면 기존 Auction은 ENDED 상태로 보존합니다.

판매자가 재경매를 선택하면 동일 Product에 새 Auction을 생성하고 `relistedFromAuctionId`로 이전 Auction을 참조합니다.
