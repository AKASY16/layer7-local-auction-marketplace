# 이미지 업로드·상품 등록 확인 (#63)

## 실행과 종료

1. Docker Desktop을 열고 왼쪽 **Containers**에서 프로젝트의 MySQL·storage를 시작한다. **Start** 버튼으로 시작하고 **Stop** 버튼으로 종료한다. 저장소 포트는 8333, MySQL 포트는 3307이다. storage-init는 버킷 생성 뒤 종료되는 일회성 컨테이너다.
2. IntelliJ에서 Gradle 새로고침을 눌러 S3 SDK 의존성을 받는다. Project SDK와 Gradle JVM은 JDK 25를 사용한다.
3. 기존 서버 실행 설정에 `AUCTION_JWT_SECRET`을 지정하고 `AuctionApiApplication`의 실행 버튼을 누른다. 시연 판매자 계정을 쓰려면 기존 demo 프로필 실행 설정을 선택한다. 종료는 Stop 버튼을 누른다.
4. `backend/http/product-images.http`를 연다. 로그인 이메일·비밀번호를 본인 계정으로 바꾸고 각 요청 왼쪽의 실행 버튼을 위에서부터 누른다. demo 프로필이면 기본 시연 판매자 값을 그대로 쓸 수 있다.
5. URL 발급 → 샘플 PNG PUT → 상품 등록 → 상품 공개 조회 순서로 실행한다. 응답에서 받은 URL과 key는 HTTP Client가 다음 요청에 자동으로 전달한다. 재등록 시에는 URL 발급부터 다시 실행한다. key는 한 번만 등록할 수 있다.

### 기존 build 폴더의 삭제 권한 오류가 나는 경우

현재 Windows 작업 폴더에서 기존 `backend/build`의 하위 폴더를 삭제할 수 없는 오류가 확인됐다. 이 경우 IntelliJ 상단 실행 설정에서 **Backend - build (local output)**를 선택하고 실행 버튼을 누른다. 전체 테스트와 빌드 산출물은 시스템 임시 폴더의 프로젝트별 디렉터리에 생성되며, 기존 폴더의 권한을 바꾸지 않는다.

서버는 **Backend - run (local output)**으로 시작하고 Stop으로 종료한다. **Run → Edit Configurations**에서 이 설정의 **Environment variables**에 기존 `AUCTION_JWT_SECRET`을 넣는다. demo 프로필을 사용할 때는 `SPRING_PROFILES_ACTIVE=demo`도 넣는다. Gradle JVM은 JDK 25여야 한다.

실행 설정이 보이지 않으면 IntelliJ에서 저장소 최상위 폴더를 프로젝트로 연다. 두 설정은 저장소의 `.run` 폴더에 포함돼 있다. 결과는 파일 탐색기 주소 표시줄에 `%TEMP%`를 입력한 뒤 `layer7-auction-build-`로 시작하는 프로젝트 폴더에서 확인한다. 테스트 보고서는 `reports/tests/test/index.html`, JAR는 `libs` 안에 있다. CI에서는 기본 `build` 경로를 그대로 사용한다.

IntelliJ HTTP Client를 사용할 수 없는 경우 Postman에서 같은 파일의 메서드·주소·본문을 사용한다. PUT의 Body는 **binary**로 PNG를 선택하고, 발급 응답의 Content-Type 헤더와 uploadUrl을 그대로 사용한다. 상품 등록에는 파일 본문 대신 objectKey를 넣는다.

## 저장소 설정

기본값은 로컬 SeaweedFS 설정이다. 실행 설정의 **Environment variables**에서 필요할 때 바꾼다.

| 환경 변수 | 기본값 | 용도 |
|---|---|---|
| AUCTION_STORAGE_ENDPOINT | http://localhost:8333 | 서버 HEAD와 클라이언트 PUT이 모두 접근할 수 있는 S3 API 주소 |
| AUCTION_STORAGE_REGION | us-east-1 | 서명 지역 |
| AUCTION_STORAGE_BUCKET | product-images | 버킷 이름 |
| AUCTION_STORAGE_ACCESS_KEY | local | 로컬용 접근 키 |
| AUCTION_STORAGE_SECRET_KEY | localsecret | 로컬용 비밀 키 |
| AUCTION_STORAGE_PUBLIC_URL | http://localhost:8333/product-images | 이미지 공개 URL 접두사(버킷 경로 포함) |

운영 환경에서는 운영 저장소의 주소·키·버킷으로 교체한다. 실제 비밀 키는 Git에 기록하지 않는다. 개발 화면을 다른 기기에서 접속한다면 localhost 대신 그 기기에서도 접근할 수 있는 주소가 필요하다.

## 검증

IntelliJ **Gradle → Tasks → verification → test**로 전체 테스트를, **build → build**로 전체 빌드를 실행한다. Docker Desktop 엔진만 실행되어 있으면 Testcontainers가 격리된 MySQL 8.4와 SeaweedFS 4.48을 자동 생성·종료한다. 개발 DB나 이미지 객체는 테스트에서 사용하지 않는다.

- `ProductImageUploadApiTest`: URL 발급·개수·형식·크기 경계·Content-Type 서명과 실제 저장소의 변조 거절.
- `ProductApiTest`: 실제 PUT·등록·공개 조회·지역 스냅숏·목록 썸네일, 타인/만료/미업로드/크기/형식/중복 key 거절과 동시 등록.

## 리뷰 분리

이슈에서 요청한 두 PR 범위는 다음과 같다. 1차 PR #96은 main에 병합됐다. 2차 변경은 그 이후의 최신 main을 기준으로 반영한다.

1. 업로드 URL 발급: S3 SDK·설정, ImageUpload 엔티티/저장소, 업로드 DTO·서비스·컨트롤러, SeaweedFS 테스트 설정, ProductImageUploadApiTest.
2. 상품 등록·조회: ProductImage 엔티티/저장소, 상품 DTO·서비스·컨트롤러, 공개 조회 보안 설정, 경매 목록 썸네일, ProductApiTest, 사용 예제·문서.

2차 PR 본문에는 `Closes #63`을 지정한다. 팀장 리뷰 승인과 CI 통과 후 main에 병합되면 이슈 #63이 종료된다.
