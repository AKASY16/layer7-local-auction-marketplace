# 지역 기반 중고거래 경매 플랫폼

TEAM LAYER7의 캡스톤 프로젝트입니다.

지역 기반 중고거래에 제한시간 경매를 결합한 웹 애플리케이션을 개발합니다. 판매자는 상품과 경매 조건을 설정하고, 구매자는 수동 입찰 또는 자동 입찰에 참여합니다. 경매 종료 후에는 낙찰자의 거래 의사 확인부터 거래 완료·포기·미응답까지의 상태를 관리합니다.

> TEAM LAYER7은 팀명이며 최종 서비스명은 아직 미정입니다.

## Backend Technical Focus

단순 CRUD 기능 수보다 **실시간 경매에서 발생하는 경쟁 상태와 데이터 정합성 문제**를 핵심 기술 주제로 다룹니다.

- 동시에 여러 입찰이 들어올 때 현재가·최고입찰자·Bid 이력의 정합성
- 수동입찰과 여러 AutoBid의 경쟁
- 경매 종료 시각과 마지막 입찰의 race condition
- 중복 요청 / Scheduler 중복 실행에 대한 멱등성
- Transaction commit 이후 WebSocket / Web Push 전달
- Testcontainers + MySQL 기반 동시성 통합테스트
- 부하 테스트 및 운영 지표를 통한 병목 분석

기술 복잡도를 불필요하게 높이지 않고, 실제 문제와 측정 근거가 있을 때 MSA/Kafka/Redis 등의 도입을 검토합니다.

## Team

| 이름 | 역할 | 담당 |
|---|---|---|
| 유선엽 | Backend Lead / 팀장 | 전체 일정·협업 관리, 백엔드 개발 및 구조 정리 |
| 장재혁 | Backend | Java/Spring 기반 백엔드 개발 |
| 박지우 | Frontend | React 기반 프론트엔드 개발 |

## Tech Stack

- Frontend: React 19, Vite, JavaScript, Styled Components, React Router
- Backend: Java 25, Spring Boot 4.1, Spring Data JPA, Spring Security + JWT, Flyway
- Database: MySQL 8.4
- Realtime: WebSocket(STOMP)
- Auction consistency: Transaction / Lock
- Scheduler: 예약 시작, 경매 종료, 낙찰 응답·거래 기한 처리
- File: Object Storage
- Deploy: Docker
- Development Assist: ChatGPT, Claude Code

## Core Flow

회원/지역 → 상품 등록 → 예약 또는 즉시 경매 → 수동/자동 입찰 → 경매 종료 → 낙찰 → 거래 응답 → 거래 진행 → 양측 완료 확인

## Project Structure

```text
backend/             Spring Boot API (Gradle, Java 25, 패키지 com.layer7.marketplace)
  src/main/resources/db/migration/   Flyway 마이그레이션
frontend/            React 웹 클라이언트 (Vite)
docs/                기획·정책·API 명세·설계 문서
infra/               로컬 인프라 설정 (SeaweedFS S3 계정)
docker-compose.yml   로컬 개발용 MySQL 8.4, 이미지 저장소(SeaweedFS)
.github/             CI, PR/Issue 템플릿
```

## Local Development

필요한 도구: JDK 25, Node.js 24, Docker

```bash
# 1. 로컬 MySQL(호스트 포트 3307)과 이미지 저장소(8333) 실행
docker compose up -d

# 2. 백엔드 실행 (http://localhost:8080, 시작 시 Flyway가 스키마 생성)
cd backend
./gradlew bootRun

# 3. 프론트엔드 실행 (http://localhost:5173, /api와 /ws는 백엔드로 프록시)
cd frontend
npm install
npm run dev
```

백엔드는 기본으로 `127.0.0.1:3307`의 `auction` / `auction` 계정에 접속합니다. 다른 값을 쓰려면 환경 변수 `AUCTION_DB_USERNAME`, `AUCTION_DB_PASSWORD`를 지정하세요. `DB_PASSWORD` 같은 흔한 이름은 다른 프로젝트용 환경 변수와 겹칠 수 있어 쓰지 않습니다.

이미지 저장소는 S3 API를 그대로 제공하는 SeaweedFS입니다. 운영에서 S3 호환 저장소로 바꿀 때 접속 주소와 키만 바꾸면 됩니다.

| 항목 | 로컬 값 |
|---|---|
| S3 endpoint | `http://localhost:8333` (path-style) |
| 버킷 | `product-images` (`docker compose up` 때 자동 생성) |
| Access Key / Secret Key | `local` / `localsecret` (로컬 전용) |
| 이미지 공개 URL | `http://localhost:8333/product-images/{objectKey}` |

업로드는 서명된 URL로만 가능하고, 읽기는 누구나 가능합니다.

백엔드 테스트는 Testcontainers로 MySQL 8.4를 띄우므로 Docker가 실행 중이어야 합니다.

```bash
cd backend
./gradlew test
```

## Documents

- [팀 역할 및 협업 규칙](docs/00-team-and-collaboration.md)
- [프로젝트 기획](docs/01-project-planning.md)
- [요구사항](docs/02-requirements.md)
- [경매 정책](docs/03-auction-policy.md)
- [회의 및 결정사항](docs/04-decisions.md)
- [API 명세](docs/05-api-spec.md)
- [Backend Domain](docs/backend/domain.md)
- [Backend 패키지 구조](docs/backend/package-structure.md)
- [ERD / DB Schema](docs/backend/erd.md)
- [Flyway V1 Schema](backend/src/main/resources/db/migration/V1__init_schema.sql)
- [Auction / Trade 상태 모델](docs/backend/auction-state.md)
- [경매 동시성 테스트 계획](docs/backend/concurrency-testing.md)
- [락 순서와 트랜잭션 규칙](docs/backend/locking.md)
- [Scheduler](docs/backend/scheduler.md)
- [Frontend](docs/07-frontend.md)
- [Infra / Deployment](docs/08-infra.md)
- [기술 의사결정](docs/09-technical-decisions.md)
- [AI 기능 검토](docs/ai-features.md)
- [현재 작업 목록](docs/task-board.md)

## Development Policy

- Frontend / Backend를 분리해 병렬 개발합니다.
- API 명세를 연동 계약으로 사용합니다.
- 기능별 Branch + Pull Request 방식으로 작업합니다.
- AI가 생성하거나 수정한 코드는 담당 개발자가 검토한 뒤 반영합니다.
- 개발 기준 원본은 GitHub 문서와 Issue/PR로 관리합니다.
