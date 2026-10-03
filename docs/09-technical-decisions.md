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
- 실시간 전달: WebSocket(STOMP)
- Scheduler: 예약 시작 / 종료 / 응답 마감
- 이미지 저장: Object Storage
- 배포 단위: Docker
- 수동입찰 + 자동입찰
- 입찰 금액은 서비스 공통 가격구간별 `BidIncrementPolicy`의 유효 가격 격자를 사용
- 시작가, 수동입찰, AutoBid maxAmount 모두 같은 가격 격자를 공유
- AutoBid 사용자는 `maxAmount`만 설정하며 별도 incrementAmount를 두지 않음
- 자동입찰은 상시 실행 프로세스가 아니라 수동입찰/AutoBid 설정·변경 이벤트가 발생했을 때만 계산
- 동일 Auction의 입찰, AutoBid 설정 변경, 종료 Scheduler는 Auction row 기준으로 직렬화
- 경매 시간 판정은 Auction 락 획득 후 서버 `Clock` 기준으로 수행
- 입찰 가능 범위는 `startAt <= now < endAt`
- 애플리케이션 내부 시간 표현은 `Instant`/UTC 기준, 사용자 화면에서 지역시간으로 변환
- Scheduler 지연은 허용하되 정합성은 endAt 검증으로 보장
- 낙찰 응답기한은 실제 Scheduler 처리시각이 아닌 `endAt + 24h`로 계산
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
- Auction Lock 세부 전략
- AutoBid 경쟁 결과 계산 및 Bid 이력 압축 규칙
- Idempotency 적용 범위
