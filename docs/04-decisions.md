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

- ~~자동입찰: maxAmount + incrementAmount~~ → 이후 서비스 공통 가격단위표를 채택하면서 incrementAmount 폐기. AutoBid는 maxAmount만 설정
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

> 이후 설계 리뷰에서 priorityAt을 제거하고 현재 선두 우선 규칙으로 대체했습니다. 아래 "설계 리뷰 반영 — 입찰 경쟁" 참고.

- 같은 maxAmount면 현재 maxAmount를 먼저 설정한 사용자가 우선
- maxAmount 변경 시 priorityAt 갱신
- ~~incrementAmount만 변경하면 priorityAt 유지~~ → incrementAmount 폐기로 해당 없음

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

## 2026-10-03 — 설계 리뷰 반영 — 입찰 경쟁

- 경쟁 계산은 도전자 1명 대 현재 선두 1명 비교로 단순화
- 커밋 시점마다 ACTIVE AutoBid는 최대 1개이며 현재 선두의 것
- 동액이면 현재 선두 우선. "먼저 확정한 쪽 우선" 원칙은 유지하되 구현은 선두 우선 규칙으로 대체
- AutoBid.priorityAt 제거
- 저장 Bid는 패자가 버틴 금액 + 승자 최종가, 이벤트당 최대 2건
- 현재 선두는 수동입찰 불가
- READY 중 AutoBid 사전 등록 미지원

## 2026-10-03 — 설계 리뷰 반영 — 거래 기한과 이용 정지

- 거래 기한 tradeDeadline = endAt + 7일
- 완료 요청을 받은 상대방은 요청 시점부터 최소 24시간 응답 시간 보장, 가장 긴 거래 기간은 endAt + 8일
- 응답 없는 완료 요청은 자동 완료, 완료 요청 없이 기한이 지나면 EXPIRED(페널티 없음)
- 판매자·구매자 일방 취소 허용, 취소한 쪽 -5
- 재경매 허용 조건에 CANCELED / EXPIRED 추가
- 신뢰점수는 표시용. 점수 기준 입찰 금지는 두지 않음
- 본인 책임 실패(포기·미응답·본인 취소) 3회 연속 시 7일 거래 참여 정지
- MVP 수동 정지는 관리자 API 없이 DB 기록으로 처리

## 2026-10-03 — 설계 리뷰 반영 — 락과 트랜잭션

- 트랜잭션 격리 수준 READ COMMITTED
- 전역 락 순서 Product → Auction → Trade → User(id 오름차순)
- 락 전 조회는 ID 탐색용(ID 프로젝션), 판단은 락 후 재검증
- 상품 수정은 경매가 논리적으로 시작되기 전이고 과거 Bid가 0건일 때만. OPEN 경매는 취소 후 수정
- 상품 삭제는 ACTIVE 상품이면서 진행 중 경매·거래가 없을 때만
- 신뢰점수는 원자 UPDATE로 갱신

## 2026-10-03 — 설계 리뷰 반영 — 논리 상태

- 저장 status는 Scheduler가 뒤따라 맞추는 값, 시간 경계의 기준은 startAt/endAt과 각 기한
- API의 Auction/Trade status는 서버시간 기준 논리 상태로 반환
- 후처리 완료 여부는 `finalized` 필드로 제공, `biddingOpen` 필드는 제거
- READY → OPEN은 쓰기 경로에서 즉시 전이, 종료·거래 기한 전이는 Scheduler만
- 의무 검사와 재경매 조건은 저장 상태(finalized) 기준

## 2026-10-03 — 설계 리뷰 반영 — 명세 보강

- Idempotency: 기록은 비즈니스 트랜잭션의 첫 쓰기로 INSERT, 성공 결과만 24시간 보관, requestHash에 경로 포함, 상품 등록에도 적용, 상태 컬럼 제거
- 실시간: 경매 이벤트에 version 추가(오래된 이벤트 무시), 발송은 별도 executor, Web Push 404/410 구독 삭제, 단일 서버 Simple Broker 전제
- 락 대기 3초 후 503 RESOURCE_BUSY, Scheduler 주기·배치 크기·기한 임박 알림 시점을 scheduler.md로 정리
- 금액 상한 10,000,000원, 경매 기간 1시간~7일, 예약 시작 7일 이내
- 내용 추가: READY/OPEN 경매에 입찰 여부 무관 등록, 경매당 10건, 상세에 이전 경매 고지 포함, 알림 대상 정의
- 가격단위표 전체를 GET /bid-increment-policy로 제공, bid-policy의 currentUnit을 minimumBidUnit으로 변경
- 인증: Access Token 30분 + Refresh Token 14일(HttpOnly 쿠키, 해시 저장, rotation, 재사용 시 family 폐기, 10초 동시 갱신 유예), 쓰기 API는 요청마다 사용자 상태 확인
- 이미지: Presigned URL 직접 업로드, image_uploads로 발급·연결·정리 상태 관리, 상품 등록은 JSON + imageKeys
- 탐색: auctions에 regionId/category 복사와 탐색 인덱스 추가, keyword LIKE는 측정 후 개선 대상으로 명시
