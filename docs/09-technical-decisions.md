# 기술 의사결정

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
- Product 1:N Auction
- Bid / AutoBid 분리
- Auction / Trade 분리
- User.trustScore + TrustHistory
- Notification + PushSubscription
- 시·군·구 지역 단위
- 예약경매
- 양측 거래 완료 확인
- 재경매는 새 Auction + relistedFromAuctionId

## 미결
- 최종 서비스명
- 실제 배포 환경
- Object Storage 제공자
- 대표 AI 기능 2~3개
- 추가 차별 기능
- 구체 Lock 전략
- JPA 연관관계 방향
