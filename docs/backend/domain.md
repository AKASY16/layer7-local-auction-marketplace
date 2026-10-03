# Backend Domain

## Core Domain

- `User`
- `Region`
- `Product`
- `ProductImage`
- `ProductAppend`
- `Auction`
- `Bid`
- `AutoBid`
- `Trade`
- `TrustHistory`
- `Notification`
- `PushSubscription`
- `Favorite`

## 관계

```text
Region
  ↑
  ├── User
  └── Product

User ──< Product
           │
           ├──< ProductImage
           ├──< ProductAppend
           └──< Auction
                  │
                  ├──< Bid
                  ├──< AutoBid
                  └── 0..1 Trade

User ──< TrustHistory
User ──< Notification
User ──< PushSubscription

User >──< Product
     Favorite
```

## 핵심 설계 원칙

- Product와 Auction 분리
- 재경매는 새 Auction
- Bid와 AutoBid 분리
- Auction과 Trade 분리
- User의 현재 `trustScore` + `TrustHistory`
- Notification과 PushSubscription 분리
- ProductAppend는 경매 중 추가 고지 전용
