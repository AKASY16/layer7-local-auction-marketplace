# Backend Domain

> 2026-10-29 적용 범위: 아래 전체 도메인 목록은 기존 설계를 포함합니다. 현재 JPA 엔티티는 User·Region·Product·Auction·Bid이며 P1 새 도메인·관계는 #61·#62에서 확정합니다. AutoBid·Trade·Trust·알림 등은 후순위입니다. [현재 요구사항](../02-requirements.md).

## Core Domain
- User
- RefreshToken
- Region
- Product
- ProductImage
- ProductAppend
- Auction
- Bid
- AutoBid
- Trade
- TrustHistory
- UserRestriction
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

User ──< RefreshToken
User ──< TrustHistory
User ──< UserRestriction
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
- 신뢰점수는 표시용이며 제재는 UserRestriction(기간제 거래 참여 정지)으로 분리
- Notification과 PushSubscription 분리
- ProductAppend는 특정 Auction 중 추가 고지 전용이며 Product는 Auction을 통해 파생. 경매 상세는 같은 Product의 모든 Auction 고지를 함께 보여줌
- HTTP 요청 멱등 기능과 IdempotencyRequest 연동은 후순위. P1 분석 이벤트(#66)와 종료(#47)의 중복 실행 방지는 유지
