# 기술 의사결정

## 현재 기술 목표 — P1

전국 수집품 경매에서 **이상입찰 탐지와 수요 기반 매칭·마감 편성을 구현·비교·검증**합니다. 기존 입찰 정합성은 두 기술의 기반으로 유지합니다. 적용 범위의 원본은 [요구사항](02-requirements.md)이며 평가 기준은 [실험 계획](p1/experiments.md)입니다.

## 기존 기술·정책 결정

아래에는 현재 구현과 후순위 설계가 함께 있습니다. Refresh·Swagger·WebSocket·AutoBid·Trade 등이 구현 완료라는 뜻은 아닙니다. 실제 구현 상태와 이번 적용 범위는 요구사항을 따릅니다.

- 서비스 형태: 웹 애플리케이션
- Frontend: React 19 / Vite / JavaScript / Styled Components / React Router / oxlint / Prettier
- Backend: Java 25 / Spring Boot 4.1 / Spring Data JPA / Spring Security + JWT / Flyway / Gradle
- 인증: Access Token(JWT, 30분) + Refresh Token(14일, HttpOnly 쿠키, 해시 저장, rotation과 재사용 감지)
- Database: MySQL 8.4
- 입찰 처리: REST + Transaction/Lock
- API 문서: 정책·흐름은 마크다운, 엔드포인트별 필드는 코드에서 생성하는 Swagger(springdoc-openapi). 구현 전에는 마크다운이 기준
- 실시간 전달: WebSocket(STOMP). 경매 이벤트에 `version`을 넣어 순서를 판단하고, 발송은 AFTER_COMMIT 이후 별도 executor에서 수행
- Scheduler: 예약 시작 / 종료 / 응답 마감
- 이미지 저장: Object Storage. Presigned URL 발급·직접 업로드·최초 등록·표시는 P1 필수, 등록 후 이미지 편집·정리 배치는 후순위
- 배포 단위: Docker
- 수동입찰 + 자동입찰
- 입찰 금액은 서비스 공통 가격구간별 `BidIncrementPolicy`의 유효 가격 격자를 사용
- 시작가, 수동입찰, AutoBid maxAmount 모두 같은 가격 격자를 공유
- 금액 상한 10,000,000원, 경매 기간 1시간~7일, 예약 시작 7일 이내 (도메인 검증)
- AutoBid 사용자는 `maxAmount`만 설정하며 별도 incrementAmount를 두지 않음
- 자동입찰은 상시 실행 프로세스가 아니라 수동입찰/AutoBid 설정·변경 이벤트가 발생했을 때만 계산
- AutoBid 경쟁은 도전자 1명 대 현재 선두 1명 비교. 동액이면 현재 선두 우선이며 priorityAt은 두지 않음
- Bid는 패자가 버틴 금액과 승자 최종가만 저장 (이벤트당 최대 2건)
- 동일 Auction의 입찰, AutoBid 설정 변경, 종료 Scheduler는 Auction row 기준으로 직렬화
- 트랜잭션 격리 수준은 READ COMMITTED, 직렬화는 비관적 락으로 보장
- 락 대기 시간은 3초(`innodb_lock_wait_timeout`), 초과 시 503 RESOURCE_BUSY로 빠르게 실패
- Scheduler는 대상 하나당 하나의 트랜잭션, 경매 시작·종료 1초 / 거래 기한 1분 주기
- 전역 락 순서는 Product → Auction → Trade → User(id 오름차순). 락 전 조회는 ID 탐색용이며 판단은 락 후 재검증한 값으로 함
- 상품 핵심정보는 경매가 논리적으로 시작되기 전이고 과거 Bid가 0건일 때만 수정
- 내용 추가(ProductAppend)는 READY/OPEN 경매에 입찰 여부와 관계없이 등록(경매당 10건), 상세에는 같은 Product의 이전 경매 고지까지 표시
- 경매 시간 판정은 Auction 락 획득 후 서버 `Clock` 기준으로 수행
- 입찰 가능 범위는 `startAt <= now < endAt`
- 애플리케이션 내부 시간 표현은 `Instant`/UTC 기준, 사용자 화면에서 지역시간으로 변환
- Scheduler 지연은 허용하되 정합성은 startAt/endAt과 각 기한의 논리 시간 판정으로 보장
- API의 Auction/Trade status는 서버시간 기준 논리 상태, 후처리 완료 여부는 `finalized`로 제공
- READY → OPEN은 쓰기 경로에서 즉시 전이, 종료·거래 기한 전이는 Scheduler만 수행
- 낙찰 응답기한은 실제 Scheduler 처리시각이 아닌 `endAt + 24h`로 계산
- 거래 기한은 `endAt + 7d`, 완료 요청을 받은 상대방에게는 요청 시점부터 최소 24시간 보장
- 거래 일방 취소는 취소한 쪽 -5, 기한 만료(EXPIRED)는 페널티 없음
- 신뢰점수는 표시용이며 제재는 본인 책임 실패 3회 연속 시 7일 거래 참여 정지(UserRestriction)
- 아래 HTTP 요청 멱등 설계는 기능·테스트 모두 후순위. P1은 키를 요구/검증하지 않고 전달되어도 무시함. 도입 후 `Idempotency-Key + requestHash + DB UNIQUE`로 중복 실행 방지
- 동일 key 재전송은 기존 결과를 재사용하고, 같은 key에 다른 요청 내용은 409 Conflict
- 후순위 HTTP 멱등 기능 도입 시에만 해당 기록을 비즈니스 트랜잭션의 첫 쓰기로 INSERT하고 성공한 결과를 24시간 보관
- Scheduler/내부 이벤트는 상태 조건, row lock, 도메인 UNIQUE 제약으로 멱등성 보장
- Trade는 `UNIQUE(auctionId)`, TrustHistory는 `UNIQUE(tradeId,userId,reason)`, Notification은 `dedupeKey UNIQUE` 활용
- 경매 탐색용으로 auctions에 regionId/category를 복사해 조인 없이 필터링. keyword LIKE 검색은 부하 테스트로 측정한 뒤 개선
- Product 1:N Auction
- Bid / AutoBid 분리
- Auction / Trade 분리
- User.trustScore + TrustHistory
- Notification + PushSubscription
- 시·군·구 지역 단위
- 예약경매
- 양측 거래 완료 확인
- 재경매는 새 Auction + relistedFromAuctionId
- Auction에 winningBidId를 두어 최종 낙찰의 실제 Bid를 추적
- JPA는 대부분 ManyToOne LAZY 단방향
- Product ↔ ProductImage만 생명주기 결합을 이유로 양방향 + cascade/orphanRemoval 허용
- Favorite는 별도 Entity, @ManyToMany 미사용

## 기술 우선순위

### 최우선
- LSS 원문·온라인 적용 가능 특성 확인, 위험 점수·오탐 감소·데이터 부족·근거 제공
- 상품 동일성·구매 희망·시간대 매칭과 마감 추천·설명
- 공개/합성/실사용 데이터 구분, 기준 방식과 재현 가능한 비교 실험
- 입찰 커밋 후 분석과 실패·중복 처리, 관리자 권한
- 최초 이미지 업로드·상품 등록/표시·경매·입찰 이력·종료/낙찰 흐름과 두 기술의 통합 시연
- 기존 비관적 락·Clock·MySQL 동시성 회귀 검증, 입찰 응답 성능과 분석 지연 분리 측정

### 후순위와 선택
- 자동입찰·Trade·신뢰점수 변경·범용 Push·재경매·Refresh·등록 후 이미지 편집/정리 배치·HTTP 요청 멱등 기능은 후순위
- WebSocket·실시간 ML 추론·MRF/LOF·임베딩은 선택
- 관리자 분석 조회 권한은 P1 필수이며 일반적인 관리자 기능 전체를 개발하지 않음

### 지양
Kafka, Kubernetes, MSA, Redis 등을 근거 없이 추가하지 않습니다. 실제 병목이나 요구가 확인될 때 도입 여부를 검토합니다.

## 미결
- 최종 서비스명
- 실제 배포 환경
- Object Storage 제공자
- LSS 원문과 적용 특성·수식, 상품군·카탈로그 출처
- 정확한 발표일·P1 세부 API/ERD

개인별 담당은 각 이슈의 Assignees와 담당·책임 본문을 따릅니다. [협업 규칙](00-team-and-collaboration.md).
