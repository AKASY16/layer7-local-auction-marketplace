# Backend Domain

## Core Domain
- User
- Region
- Product
- ProductImage
- ProductAppend
- Auction
- Bid
- AutoBid
- Trade
- TrustHistory
- Notification
- PushSubscription
- Favorite
- IdempotencyRequest

## 관계

```text
Region
  ↑
  ├── User
  └── Product

User ──< Product
           │
           ├──< ProductImage
           └──< Auction
                  │
                  ├──< ProductAppend
                  ├──< Bid
                  ├──< AutoBid
                  └── 0..1 Trade

Auction ──> leadingBid  (nullable)
Auction ──> winningBid  (nullable)
Auction ──> relistedFromAuction (nullable)

User ──< TrustHistory
User ──< Notification
User ──< PushSubscription
User ──< IdempotencyRequest

User >──< Product
     Favorite
```

## 핵심 설계 원칙
- Product와 Auction 분리
- 재경매는 기존 Auction 재사용이 아니라 새 Auction 생성
- Bid와 AutoBid 분리
- Auction과 Trade 분리
- Auction은 currentPrice와 leadingBid를 현재 상태 snapshot으로 유지
- 종료 시 winningBid로 실제 낙찰 근거 보존
- User의 현재 trustScore + TrustHistory 이력
- Notification과 PushSubscription 분리
- ProductAppend는 특정 Auction 중 추가 고지 전용이며 Product는 Auction을 통해 파생
- 명령형 HTTP 중복실행은 IdempotencyRequest로 제어
