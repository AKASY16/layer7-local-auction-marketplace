# 중간 발표 시연

> 이 문서는 기존 MVP의 실행 가능한 시연 절차입니다. 최종 P1 목표 흐름과 완료 기준은 [P1 통합 시연](p1/demo.md)에서 관리하며, 아직 구현되지 않은 새 시연과 구분합니다.

경매 생성 API와 입찰 화면이 아직 없어서, 경매는 시연용 데이터로 넣어 두고 입찰은 서버에 HTTP 요청을 보내 보여준다 (#53). 화면은 홈의 진행 중 경매 목록과 회원가입·로그인까지 시연하고, 앞으로 만들 화면은 발표 자료에 목업으로 소개한다.

## 띄우는 순서

개발용 DB(3307)는 건드리지 않고, 시연용 MySQL(3308)을 따로 띄운다. 시연용 MySQL은 데이터를 메모리에만 두므로 멈추면 사라진다.

```bash
# 1. 시연용 MySQL 실행 (빈 DB). --wait은 MySQL이 접속을 받을 수 있을 때까지 기다린다 (10~20초)
docker compose --profile demo up -d --wait demo-mysql

# 2. 백엔드를 demo 프로필로 실행 (AUCTION_JWT_SECRET 필요). 처음 시연 데이터를 만들 때 경매 id를 로그에 남긴다
cd backend
./gradlew bootRun --args='--spring.profiles.active=demo'

# 3. 새 터미널에서 저장소 루트 기준으로 프론트엔드 실행 (홈 경매 목록·회원가입·로그인 시연)
cd frontend
npm run dev
```

MySQL이 준비되기 전에 백엔드를 켜면 DB에 접속하지 못해 바로 종료되므로, 1번이 끝난 뒤에 2번을 실행한다.

IntelliJ에서는 AuctionApiApplication 실행 설정을 복사해 시연용 설정을 따로 만들고, 그 설정의 Environment variables에 `AUCTION_JWT_SECRET`과 함께 `SPRING_PROFILES_ACTIVE=demo`를 넣는다. 평소 쓰는 설정에 넣으면 개발할 때도 시연용 DB(3308)에 접속하려다 실패한다.

리허설과 발표 직전에는 시연용 MySQL을 다시 띄워서 시각을 그 시점에 맞춘다. 진행 중 경매는 서버를 켠 때부터 1일 뒤에 마감된다.

```bash
docker compose --profile demo stop demo-mysql
docker compose --profile demo up -d --wait demo-mysql
# 그다음 백엔드를 다시 켠다
```

demo 프로필은 비밀번호가 공개된 시연 계정을 만들므로 운영 배포에서는 켜지 않는다.

## 시연 데이터

계정 비밀번호는 모두 `layer7-demo`다 (시연용 DB에서만 쓰는 개발용 값).

| 이메일 | 닉네임 | 역할 |
|---|---|---|
| demo-seller@example.com | 김레이어 | 판매자 (모든 경매) |
| demo-bidder1@example.com | 익산사는개발자 | 입찰자 |
| demo-bidder2@example.com | 키보드좋아 | 입찰자 |
| demo-bidder3@example.com | 테크러버 | 입찰자 |

새 DB에서 켰을 때 경매 id (지역은 모두 익산시):

| id | 상품 | 상태 | 현재가 / 선두 |
|---|---|---|---|
| 1 | 몬스타기어 닌자87 기계식 키보드 | 진행 중 | 85,000원 / 테크러버 |
| 2 | 드롱기 아이코나 커피머신 | 진행 중 | 42,000원 / 익산사는개발자 |
| 3 | 시디즈 T50 사무용 의자 | 진행 중 | 120,000원 / 키보드좋아 |
| 4 | 아이패드 프로 키보드 케이스 | 마감 (1시간 전) | 60,000원 / 입찰 없음 |
| 5 | 로지텍 MX Master 3S 마우스 | 시작 전 (1일 뒤 시작) | 50,000원 / 입찰 없음 |

## 입찰 시연

IntelliJ에서 `backend/http/demo.http`를 열고 위에서부터 순서대로 실행한다.

1. 입찰자 2명과 판매자 로그인 (토큰은 자동으로 저장된다)
2. 키보드에 86,000원 입찰 → `201`
3. 다른 입찰자가 같은 금액 → `409 BID_AMOUNT_TOO_LOW`
4. 판매자가 본인 경매에 입찰 → `403 SELF_BID_FORBIDDEN`
5. 마감된 경매에 입찰 → `409 AUCTION_ENDED`
6. 시작 전 경매에 입찰 → `409 AUCTION_NOT_OPEN`

홈 화면(로그인하지 않아도 됨)에는 진행 중 경매 1~3번만 나온다. 2번을 실행한 뒤 홈을 새로 고침하면 키보드 현재가가 86,000원으로 바뀐다.

2~6번의 입찰 결과(성공·오류 코드)는 `DemoDataInitializerTest`가 같은 순서로 확인하므로, 시연 데이터나 입찰 규칙이 바뀌어 순서가 깨지면 테스트가 실패한다. 오류 코드마다 HTTP 상태(403·409)가 명세 표와 같은지는 `ErrorCodeSpecTest`가, 실제 HTTP 응답 형식은 `BidApiTest`가 확인한다.
