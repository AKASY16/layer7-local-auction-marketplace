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
- Auction별 Timer/Thread를 유지하지 않고 `status + startAt/endAt` 조건으로 전이 대상을 조회합니다.
- 입찰 처리와 종료 Scheduler는 동일 Auction row에 대해 쓰기 락 규칙을 공유해 경계시각 경쟁 상태를 직렬화합니다.
- 서버가 Auction 쓰기 락을 획득한 뒤의 현재시각을 기준으로 판정하며, 시간은 주입된 `Clock`과 `Instant` 기준입니다.

### 저장 상태와 논리 상태

저장된 status는 Scheduler가 뒤따라 맞추는 값이고, 시간 경계의 기준은 startAt/endAt입니다. 입찰 판정과 API 응답은 항상 서버시간 기준 논리 상태를 사용합니다.

```text
CANCELED  저장 status가 CANCELED
ENDED     저장 status가 ENDED, 또는 READY/OPEN이면서 now >= endAt
OPEN      저장 status가 READY/OPEN이면서 startAt <= now < endAt
READY     저장 status가 READY이면서 now < startAt
```

- READY → OPEN은 따라붙는 부작용이 없으므로, 쓰기 경로가 Auction 락을 잡은 뒤 논리 상태는 OPEN인데 저장값이 READY면 그 자리에서 OPEN으로 바꾸고 진행합니다. 시작 Scheduler는 놓친 전이를 뒤늦게 맞추는 용도입니다.
- OPEN → ENDED는 winningBid 확정·Trade 생성·알림이 따라붙으므로 종료 Scheduler만 수행합니다. 그 전까지는 논리 상태가 ENDED라서 입찰을 거절합니다.
- 종료 Scheduler 대상은 `status IN (READY, OPEN) AND endAt <= now`입니다. 시작 전이조차 못 한 채 끝난 경매도 정리됩니다.
- 저장 상태를 바꾼 쪽이 AFTER_COMMIT으로 상태 이벤트를 발행합니다.
- `finalized`는 저장 status가 ENDED 또는 CANCELED인지 여부입니다. 논리 상태가 ENDED여도 finalized가 false면 낙찰 확정 전입니다.
- 회원탈퇴·상품 삭제의 의무 검사와 재경매 조건은 저장 상태(finalized) 기준으로 판단합니다. 정산 전 경매에는 아직 Trade가 없으므로 논리 상태만 보고 유찰로 판단하면 안 됩니다.
- ENDED + finalized + winningBidId == null 이면 유찰, winningBidId != null 이면 낙찰입니다.
- 낙찰 시에만 Trade를 생성하며, responseDeadline은 `Auction.endAt + 24시간`으로 계산합니다.

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

### 저장 상태와 논리 상태

Trade도 Auction과 같은 원칙을 따릅니다. 기한 전이에는 신뢰점수·정지·알림·상품 상태가 따라붙으므로 Scheduler만 저장 상태를 바꾸고, 그 전까지 API는 논리 상태를 반환하며 기한이 지난 명령은 거절합니다.

```text
NO_RESPONSE  저장 AWAITING_RESPONSE이면서 now >= responseDeadline
EXPIRED      저장 IN_PROGRESS이면서 now >= tradeDeadline
COMPLETED    저장 COMPLETION_REQUESTED이면서 now >= completionDeadline
그 외        저장 status 그대로
```

- `finalized`는 저장 status가 COMPLETED / DECLINED / NO_RESPONSE / CANCELED / EXPIRED인지 여부입니다. 논리 상태가 바뀌었어도 finalized가 false면 신뢰점수·정지·상품 상태가 아직 반영되지 않은 상태입니다.
- 재경매 허용 여부는 finalized Trade의 상태로 판단합니다.

## 재경매

거래가 DECLINED / NO_RESPONSE / CANCELED / EXPIRED로 실패하면 기존 Auction은 ENDED 상태로 보존합니다.

판매자가 재경매를 선택하면 동일 Product에 새 Auction을 생성하고 `relistedFromAuctionId`로 이전 Auction을 참조합니다.
