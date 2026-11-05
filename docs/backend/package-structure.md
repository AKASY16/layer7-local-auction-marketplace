# Backend 패키지 구조

> 2026-10-29 적용 범위: 아래는 기존 패키지 구조입니다. P1 신규 기능(관심상품·앱 내부 알림·WebSocket·타임 경매)의 위치는 실제 구현 PR과 함께 반영합니다. [현재 요구사항](../02-requirements.md).

기능(도메인)별로 패키지를 나눕니다. "경매에 관한 코드는 `auction`에 다 있다"처럼, 어떤 코드를 찾을 때 도메인 이름만 알면 되게 하기 위함입니다.

```text
com.layer7.marketplace
├── global/         여러 도메인이 함께 쓰는 공통 코드 (config, error, scheduling, security, time, websocket)
├── auth/           회원가입·로그인·토큰 갱신·로그아웃, RefreshToken
├── user/           회원, 내 정보, 지역 변경, 회원탈퇴
├── region/         시·군·구 지역
├── product/        상품, 상품 이미지, 이미지 업로드, 관심상품
├── auction/        경매, 내용 추가, 경매 시작·종료 Scheduler
├── bid/            수동입찰, 자동입찰, 가격단위표
├── trade/          낙찰 후 거래, 거래 기한 Scheduler
├── trust/          신뢰점수 이력, 이용 정지
├── notification/   앱 내부 알림 저장·조회·읽음 (Web Push 구독·발송은 후순위)
├── idempotency/    HTTP 중복 요청 방지 (기능·테스트 후순위)
└── demo/           중간 발표 시연용 데이터 (demo 프로필 전용, docs/demo.md)
```

각 패키지에 무엇이 들어가는지는 패키지의 `package-info.java`에 적어 둡니다.

## 도메인 패키지 안의 구성

도메인마다 같은 모양으로 나눕니다. 필요한 것만 만들고, 빈 폴더를 미리 만들지 않습니다.

```text
auction/
├── controller/   HTTP 요청을 받아 service를 호출하고 DTO를 반환
├── service/      비즈니스 규칙과 트랜잭션
├── domain/       엔티티와 도메인 규칙 (예: Auction, AuctionStatus)
├── repository/   DB 조회·저장 (Spring Data JPA)
├── event/        도메인 이벤트와 커밋 후 처리 리스너 (예: AuctionPriceChangedEvent, AuctionEventBroadcaster)
├── scheduler/    @Scheduled 작업. service를 호출만 하고 규칙·트랜잭션은 service에 둔다 (예: AuctionCloseScheduler)
└── dto/          요청·응답 객체 (record)
```

## 지킬 것

- 다른 도메인의 기능이 필요하면 그 도메인의 service를 호출하고, 다른 도메인의 repository를 직접 쓰지 않습니다.
- 엔티티는 controller 밖으로 내보내지 않고 dto로 바꿔서 응답합니다.
- `global`에는 두 개 이상의 도메인이 쓰는 코드만 둡니다. 한 도메인만 쓰는 코드는 그 도메인 안에 둡니다.
- 도메인 사이에 서로가 서로를 부르는 순환이 생기면 구조를 다시 봅니다.
