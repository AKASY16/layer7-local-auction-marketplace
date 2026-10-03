# 회의 및 결정사항

## 2026-10-03 — 개발 착수 기준

- TEAM LAYER7은 팀명, 서비스명은 별도 결정
- 웹 애플리케이션
- 수동 + 자동입찰 지원
- Frontend / Backend 분리 개발
- API 명세 기준 연동
- 기능별 Branch + Pull Request
- ChatGPT / Claude Code 활용, 생성 코드 담당자 검토

## 2026-10-03 — 경매 세부 정책

- 자동입찰: maxAmount + incrementAmount
- Bid 철회 없음
- 상품 핵심정보 입찰 후 잠금
- ProductAppend 1회 200자
- 차순위 승계 없음
- 판매자 선택 시 재경매
- 신뢰점수 MVP 포함
- 판매자 취소는 입찰 0건일 때만
- 마감 연장 없음
- 낙찰 응답 24시간
- 즉시구매 MVP 제외

## 2026-10-03 — 자동입찰 우선순위

- 같은 maxAmount면 현재 maxAmount를 먼저 설정한 사용자가 우선
- maxAmount 변경 시 priorityAt 갱신
- incrementAmount만 변경하면 priorityAt 유지

## 2026-10-03 — Auction / Trade 상태 모델

- 예약경매 포함
- Auction: READY / OPEN / ENDED / CANCELED
- Trade: AWAITING_RESPONSE / IN_PROGRESS / COMPLETION_REQUESTED / COMPLETED / DECLINED / NO_RESPONSE
- 거래 완료는 한쪽 요청 + 상대방 확인
- 상대방 미완료 판단 시 IN_PROGRESS 복귀
- COMPLETED 시 판매자·구매자 모두 +2
- 재경매는 새 Auction + relistedFromAuctionId
- 자체 채팅 / 안심결제는 추후 확장

## 2026-10-03 — User / Product 세부 모델

- User.nickname UNIQUE
- 회원탈퇴는 WITHDRAWN 상태 처리
- Product 상태 등급 6단계
- conditionDescription 필수
