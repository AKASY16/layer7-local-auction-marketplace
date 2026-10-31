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

## 2026-10-06 — 프로젝트 기반

- 저장소를 backend / frontend / docs로 나눈 단일 저장소로 운영
- Spring Boot 3.5 → 4.1: 3.5의 오픈소스 지원이 2026-06-30에 종료되어, 2027-07까지 지원되는 4.1로 변경
- Java 21 → 25: 최신 LTS로 변경
- Frontend는 Vite + React 19, 린터는 oxlint, 포맷은 Prettier
- 로컬 MySQL은 docker-compose(호스트 포트 3307), 테스트는 Testcontainers MySQL 8.4
- PR마다 GitHub Actions로 백엔드 빌드·테스트와 프론트 lint·format·build 실행
- Backend 기본 패키지는 com.layer7.marketplace, 그 아래를 도메인별 패키지로 나눔 (docs/backend/package-structure.md)
- 로컬 이미지 저장소는 SeaweedFS(S3 호환). MinIO는 Docker Hub 공식 이미지 제공이 중단되어 제외. 업로드는 Presigned URL로만, 읽기는 공개
- 지역 단위는 시·군·구(자치구). 일반구는 상위 시로 통합 (예: 수원시)

## 2026-10-07 — 개발 규칙

- 코드 컨벤션을 docs/backend/conventions.md로 정리 (DTO는 record, 엔티티에 @Setter·@Data·@Builder 금지, 오류는 BusinessException 하나, 시간은 Instant + Clock, 테스트 이름은 한글 @DisplayName)
- 브랜치·커밋·PR·리뷰 규칙을 docs/00-team-and-collaboration.md에 정리 (브랜치 종류/이슈번호-요약, 커밋 종류: 요약, PR 400줄 안팎, 리뷰 24시간 안, Squash 병합)
- API 문서는 혼합 방식: 정책·흐름은 마크다운, 엔드포인트별 필드는 springdoc-openapi로 코드에서 생성. 구현 전에는 마크다운이 기준이고, springdoc은 첫 API PR에서 추가

## 2026-10-29 — 전국 수집품 경매와 P1 최종 시연

- 서비스 방향을 전국 수집품 대상 경매로 전환한다. 현재 작업명은 Layer7이다.
- 3~4주 후 최종 시연은 논문 기반 이상입찰 탐지와 수요 기반 상품 매칭·마감 편성의 구현·비교 실험에 집중한다. 정확한 발표일은 미정이다.
- 경매는 두 기술을 연결할 최소 MVP만 개발한다. 기존 입찰 락 순서·락 후 서버 시각 판정·Bid 판정 시각 기록을 유지한다.
- 이번 종료 처리(#47)는 낙찰 확정까지다. 자동입찰·Trade·신뢰점수 변경·범용 Push·배송·결제·채팅·Refresh 등은 후순위다. WebSocket·실시간 ML 추론은 선택이다.
- 위험 점수는 확률이 아니며 자동 차단하지 않는다. 오탐 감소·데이터 부족·버전·근거를 포함하고 분석은 입찰 커밋 후 수행한다.
- 수요 매칭은 정확/조건부/유사를 구분한다. 관심 수요를 실제 입찰 참여로 단정하지 않고 개별 희망 가격 상한을 공개하지 않는다.
- 논문 원문·지표·가중치·수식, 상품군·카탈로그·새 개인별 분업·상세 API/ERD는 확인 후 확정한다. 편성 알고리즘은 자체 설계와 논문 근거를 구분한다.
- #7·#31의 이전 계획은 새 P1 작업으로 이관하고, Sprint 1의 기한·완료 이력은 보존한다. 기존 설계와 스키마를 소급 삭제하지 않는다.
- 현재 범위는 [요구사항](02-requirements.md), 선행 작업은 [P1 개요](p1/README.md), 전환 정리는 #60을 참조한다.

### 2026-10-29 추가 확인 — 이미지와 HTTP 요청 멱등성

- 최소 상품 등록에 이미지 업로드·연결·표시를 포함한다. 기존 이미지 1~10장·형식·크기·본인 업로드 검증 정책을 유지하며 등록 후 이미지 편집·정리 배치는 후순위로 둔다.
- HTTP 요청 멱등성은 테스트뿐 아니라 기능 전체를 후순위로 둔다. P1은 Idempotency-Key 필수/형식 검증·요청 선점·해시/응답 저장·재사용 응답을 제공하지 않는다. 전달된 키도 멱등 처리에 사용하지 않는다.
- 분석 이벤트의 입찰 식별자 기반 중복 처리 방지·재처리(#66)와 종료 Scheduler 중복 실행 방지(#47)는 필수로 유지한다.

### 2026-10-29 추가 확인 — 이슈 책임 배정

- `AKASY16`은 유선엽(Backend·팀장), `redrum2555`는 장재혁(Backend), `woo081`은 박지우(Frontend)다.
- 열린 이슈에 책임자를 배정했다. 핵심 연구·알고리즘·동시성·설계는 유선엽, 일반 백엔드 API는 장재혁, 화면·API 연동은 박지우가 담당한다. 구체적인 배정은 각 이슈의 Assignees를 기준으로 관리한다.
- 공동 작업은 이슈 본문에 주관자와 각자 책임을 구분한다. 새 이슈는 담당자를 지정해 생성하고 담당 변경 시 본문도 함께 수정한다.
- 앞선 전환 시점의 개인별 분업 미정 상태를 이 배정으로 갱신한다. 정확한 발표일과 미확인 논문·상품군·API 계약은 별도로 확정한다.

## 2026-10-31 — 경매 종료 시각 합성 시뮬레이터 기록

- 종료 시각 정책 검증용 합성 경매 시뮬레이터와 실험 기록을 `experiments/auction-simulator/`에 둔다. 기본 엔진은 audit-fix-v1, 시연 시각화는 V2-A 관찰 모드를 쓴다.
- 시뮬레이션에서 추천 효과가 가정한 구매자 활동 시간에 따라 뒤집혔다(활동량 TOP3: 저녁 피크 +5.5%, 낮 피크 −11.0%). 이 결과를 마감 추천의 성과 근거로 쓰지 않는다. 마감 추천(#72)은 후보와 근거를 보여 주고 판매자가 확정한다.
- 원시·합성 데이터셋은 개인정보 보호 문제로 저장소에 올리지 않는다. 실험 결과 CSV·JSON과 로그도 올리지 않고 담당자 로컬에 보관한다.
- Retailrocket 쇼핑 활동 곡선은 수집 국가·시간대 미상, 2015년 자료, 비상업 라이선스 때문에 기각한다.
- 이 이관은 이미 만든 실험 기록을 한 번에 옮기는 작업이라 PR 크기 기준(400줄 안팎)의 예외로 하나의 PR로 올린다.
