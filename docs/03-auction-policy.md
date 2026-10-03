# 경매 정책 및 비즈니스 규칙

## 입찰

- 수동 입찰과 자동 입찰 모두 지원
- 성립한 Bid는 수정·삭제·철회하지 않음
- 입찰 전 최종 금액과 철회 불가 정책을 명확하게 표시
- 판매자는 본인 경매에 입찰할 수 없음

## 자동입찰

자동입찰 설정값:
- `maxAmount`: 최대 입찰 가격
- `incrementAmount`: 1회 가격 상승분

규칙:
- 최대가격을 초과하지 않는 범위에서 자동입찰
- `incrementAmount`는 해당 경매의 최소 입찰 단위 이상
- 같은 최대금액이면 `priorityAt`이 빠른 사용자가 우선
- 최초 등록 시 `priorityAt = now`
- `maxAmount` 변경 시 `priorityAt` 갱신
- `incrementAmount`만 변경하면 `priorityAt` 유지
- 최대금액 상향 가능
- 하향은 현재 성립 가격 미만으로 불가
- 자동입찰 중지 가능
- 이미 성립한 Bid는 설정 변경/중지 후에도 유지
- `currentPrice + incrementAmount`가 `maxAmount`를 초과하는 경우, `maxAmount`가 최소 유효 입찰가 이상이면 **maxAmount를 마지막 자동입찰 금액으로 사용**
- 단, `maxAmount < currentPrice + minBidIncrement`이면 유효한 다음 입찰이 불가능하므로 AutoBid를 `EXHAUSTED` 처리
- 자동입찰 설정/변경 전에는 **마지막 입찰이 설정한 incrementAmount보다 작아질 수 있음**을 사용자에게 명확히 안내하고 확인을 받음
- 현재 가격 기준으로 바로 상한 보정이 예상되는 경우, 예: 현재가 94,000원 / 상승분 10,000원 / 최대 100,000원 → 다음 자동입찰은 104,000원이 아니라 100,000원이라는 구체적 예시를 표시

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

## 상품 내용

- 입찰 1건 이상이면 기존 핵심 상품정보 수정/삭제 불가
- 판매자는 기존 내용을 덮어쓰지 않고 `ProductAppend` 등록
- 1회 최대 200자

## 낙찰

- 차순위 승계 없음
- 입찰자가 없으면 유찰, Trade 생성 안 함
- 낙찰자가 있으면 Trade 생성
- 낙찰자 응답 기한 24시간

## 재경매

- 기존 Auction을 다시 OPEN으로 되돌리지 않음
- 판매자가 새 Auction 생성
- `relistedFromAuctionId`로 이전 경매 참조
- 기존 Bid / AutoBid / Trade 이력은 변경하지 않음

## 즉시구매

MVP 제외.
