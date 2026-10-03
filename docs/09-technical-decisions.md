# 기술 의사결정

## 프로젝트 기술 목표
이 프로젝트는 캡스톤 결과물로서 실제 서비스 수준의 백엔드 안정성과 설계 근거를 확보하는 것을 목표로 합니다.

따라서 기능 수를 무리하게 늘리기보다 **실시간 경매 도메인에서 발생하는 경쟁 상태와 데이터 정합성 문제를 설계·구현·검증하는 것**을 기술 중심축으로 둡니다.

핵심 설명 문장:

> 실시간 경매라는 경쟁 상태가 발생하는 도메인에서 Transaction, Lock, 자동입찰, 상태 전이, Scheduler를 이용해 데이터 정합성을 설계하고 테스트한다.

## 확정
- 서비스 형태: 웹 애플리케이션
- Frontend: React / JavaScript / Styled Components / React Router
- Backend: Java 21 / Spring Boot 3.5 / Spring Data JPA / Spring Security + JWT
- Database: MySQL 8.4
- 입찰 처리: REST + Transaction/Lock
- 실시간 전달: WebSocket(STOMP). 경매 이벤트에 `version`을 넣어 순서를 판단하고, 발송은 AFTER_COMMIT 이후 별도 executor에서 수행
- Scheduler: 예약 시작 / 종료 / 응답 마감
- 이미지 저장: Object Storage
- 배포 단위: Docker
- 수동입찰 + 자동입찰
- 입찰 금액은 서비스 공통 가격구간별 `BidIncrementPolicy`의 유효 가격 격자를 사용
- 시작가, 수동입찰, AutoBid maxAmount 모두 같은 가격 격자를 공유
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
- 부작용이 있는 HTTP 명령은 `Idempotency-Key + requestHash + DB UNIQUE`로 중복 실행 방지
- 동일 key 재전송은 기존 결과를 재사용하고, 같은 key에 다른 요청 내용은 409 Conflict
- 멱등 기록은 비즈니스 트랜잭션의 첫 쓰기로 INSERT하고 성공한 결과만 24시간 보관
- Scheduler/내부 이벤트는 상태 조건, row lock, 도메인 UNIQUE 제약으로 멱등성 보장
- Trade는 `UNIQUE(auctionId)`, TrustHistory는 `UNIQUE(tradeId,userId,reason)`, Notification은 `dedupeKey UNIQUE` 활용
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
- 동시입찰 정합성
- 자동입찰 경합
- 경매 종료와 입찰의 race condition
- 중복 요청 / 멱등성
- Scheduler 중복 실행 방지
- WebSocket / Push의 AFTER_COMMIT 처리
- Testcontainers 기반 실제 MySQL 동시성 테스트
- 부하 테스트 및 병목 수치 기록

### 일반 서비스 기능
- 회원 / 상품 / 지역
- Trade 상태 관리
- 신뢰점수
- 관심상품 / 알림

### 후순위
- 자체 채팅
- 안심결제 / 에스크로
- 복잡한 관리자 기능
- 불필요한 소셜 기능

### 지양
Kafka, Kubernetes, MSA, Redis 등을 근거 없이 추가하지 않습니다. 실제 병목이나 요구가 확인될 때 도입 여부를 검토합니다.

## 미결
- 최종 서비스명
- 실제 배포 환경
- Object Storage 제공자
- 대표 AI 기능 2~3개
- 추가 차별 기능

