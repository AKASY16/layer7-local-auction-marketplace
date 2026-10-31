# LAYER7 — 전국 수집품 경매 플랫폼

TEAM LAYER7의 3인 캡스톤 프로젝트입니다. 전국의 수집품을 대상으로 경매 플랫폼을 개발합니다. 현재 서비스 작업명은 Layer7이며 최종 명칭은 별도 결정합니다.

## 현재 개발 목표 — P1 최종 시연

2026-10-29 기준 최종 시연까지 3~4주 동안 다음 두 기술의 구현·비교 실험에 집중합니다.

- **이상입찰 탐지:** 논문을 근거로 입찰 행동을 분석하고 위험 점수·판단 근거·오탐 감소 결과를 제공합니다. 원문 지표·수식은 아직 미확인 상태이며 구현 완료를 뜻하지 않습니다.
- **수요 기반 매칭·마감 편성:** 구매 희망과 상품 동일성을 매칭하고, 참여 가능 시간·대체 상품 경매·판매자 제약을 고려해 마감 시간을 추천합니다.

경매는 두 기술을 연결할 최소 MVP로 개발합니다. 기존 입찰 엔진의 비관적 락, 락 이후 서버 시각 판정, 판정 시각 기록과 MySQL 동시성 검증을 유지합니다. 최소 상품 이미지 업로드·등록·표시는 MVP에 포함합니다. HTTP 요청 멱등 기능·Trade·자동입찰·신뢰점수 변경·범용 Push·배송·결제·채팅은 후순위이고 WebSocket·실시간 ML 추론은 선택 범위입니다.

| 현재 구현 | 추가로 필요한 것 |
|---|---|
| 가입·로그인·내 정보·지역·공개 경매 목록·수동입찰 API | 이미지 업로드·상품 등록/이미지 표시·경매 생성/상세·입찰 이력·종료/낙찰 확정 |
| 홈 목록·가입/로그인 화면·공통 디자인·분리된 demo DB | 두 기술의 모듈·관리자 권한·화면·비교 실험·통합 시연 |

[현재 요구사항](docs/02-requirements.md) · [P1 범위와 선행 작업](docs/p1/README.md) · [최종 시연 마일스톤](https://github.com/AKASY16/layer7-local-auction-marketplace/milestone/2)

## Team

| 이름 | GitHub | 역할 | 담당 |
|---|---|---|---|
| 유선엽 | [AKASY16](https://github.com/AKASY16) | Backend / 팀장 | 전체 일정·협업 관리, 핵심 연구·알고리즘·동시성·설계 |
| 장재혁 | [redrum2555](https://github.com/redrum2555) | Backend | 상품·경매·수요 등록·관리자 조회 등 백엔드 API |
| 박지우 | [woo081](https://github.com/woo081) | Frontend | 사용자·관리자 화면과 API 연동 |

개별 작업의 책임자는 각 이슈의 Assignees를 기준으로 관리합니다. 새 이슈는 담당자를 지정해 생성하고, 공동 작업은 본문에 주관자와 각자 책임을 기록합니다. [협업 규칙](docs/00-team-and-collaboration.md).

## Tech Stack

- Frontend: React 19, Vite, JavaScript, Styled Components, React Router
- Backend: Java 25, Spring Boot 4.1, Spring Data JPA, Spring Security + JWT, Flyway
- Database: MySQL 8.4
- Realtime: WebSocket(STOMP) 설계는 보존하며 P1 화면 갱신 수단은 별도 선택
- Auction consistency: Transaction / Lock
- Scheduler: 경매 종료·낙찰 확정 구현 예정 (#47), 거래 기한 처리는 후순위
- File: Object Storage
- Local Infrastructure: Docker Compose (MySQL·S3 호환 저장소). 운영 배포 환경은 미정
- Experiments: Python 3.12 (pandas·NumPy·SciPy·statsmodels), 합성 경매 시뮬레이터는 `experiments/auction-simulator/`
- Development Assist: ChatGPT, Claude Code, Codex

## Core Flow

개발 목표: 구매 희망 등록 → 상품 매칭·수요 집계 → 마감 추천 → 경매 생성 → 정상/의심 입찰 → 위험 분석 → 종료·낙찰 확정 → 비교 실험 확인

## Project Structure

```text
backend/             Spring Boot API (Gradle, Java 25, 패키지 com.layer7.marketplace)
  src/main/resources/db/migration/   Flyway 마이그레이션
frontend/            React 웹 클라이언트 (Vite)
docs/                기획·정책·API 명세·설계 문서
infra/               로컬 인프라 설정 (SeaweedFS S3 계정)
docker-compose.yml   로컬 개발용 MySQL 8.4, 이미지 저장소(SeaweedFS)
experiments/         실험 코드와 기록 (auction-simulator: 경매 종료 시각 합성 시뮬레이터, 원시·합성 데이터는 미업로드)
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

중간 발표 시연용 데이터로 띄우는 방법은 [docs/demo.md](docs/demo.md)에 있습니다. 개발용 DB와 따로 시연용 MySQL을 씁니다.

이미지 저장소는 S3 API를 그대로 제공하는 SeaweedFS입니다. 운영에서 S3 호환 저장소로 바꿀 때 접속 주소와 키만 바꾸면 됩니다.

| 항목 | 로컬 값 |
|---|---|
| S3 endpoint | `http://localhost:8333` (path-style) |
| 버킷 | `product-images` (`docker compose up` 때 자동 생성) |
| Access Key / Secret Key | `local` / `localsecret` (로컬 전용) |
| 이미지 공개 URL | `http://localhost:8333/product-images/{objectKey}` |

저장소 접근 정책은 서명된 URL 업로드·공개 읽기를 전제로 합니다. 상품 이미지 업로드 API는 아직 구현되지 않았습니다.

백엔드 테스트는 Testcontainers로 MySQL 8.4를 띄우므로 Docker가 실행 중이어야 합니다.

```bash
cd backend
./gradlew test
```

### JWT 설정

- 서버 실행에는 환경 변수 AUCTION_JWT_SECRET이 필요하다.
- 키는 UTF-8 기준 최소 32바이트이며, 충분히 무작위인 값을 사용한다.
- 실제 키는 소스 코드나 Git에 저장하지 않는다.
- 테스트는 src/test/resources/application.properties의 테스트 전용 키를 사용한다.
- 테스트 전용 키는 실제 서비스에 사용하지 않는다.

### IntelliJ에서 실행·검증

- Project SDK와 Gradle JVM을 JDK 25로 설정한다.
- 서버 실행 설정의 Environment variables에 AUCTION_JWT_SECRET을 지정한다.
- 개발용 MySQL이 실행된 상태에서 AuctionApiApplication의 실행 버튼으로 서버를 시작한다.
- 서버 종료는 IntelliJ의 Stop 버튼을 사용한다.
- 통합 테스트는 Docker Desktop 엔진이 실행 중이어야 한다.
- 테스트용 MySQL은 Testcontainers가 자동으로 실행한다.
- 전체 테스트: Gradle 창 → Tasks → verification → test.
- 전체 빌드: Gradle 창 → Tasks → build → build.

## Documents

- [팀 역할 및 협업 규칙](docs/00-team-and-collaboration.md)
- [프로젝트 기획](docs/01-project-planning.md)
- [요구사항](docs/02-requirements.md)
- [경매 정책](docs/03-auction-policy.md)
- [회의 및 결정사항](docs/04-decisions.md)
- [API 명세](docs/05-api-spec.md)
- [Backend Domain](docs/backend/domain.md)
- [Backend 패키지 구조](docs/backend/package-structure.md)
- [Backend 코드 컨벤션](docs/backend/conventions.md)
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
- [경매 종료 시각 합성 시뮬레이터](experiments/auction-simulator/README.md)

## Development Policy

- Frontend / Backend를 분리해 병렬 개발합니다.
- API 명세를 연동 계약으로 사용합니다.
- 기능별 Branch + Pull Request 방식으로 작업합니다.
- AI가 생성하거나 수정한 코드는 담당 개발자가 검토한 뒤 반영합니다.
- 개발 기준 원본은 GitHub 문서와 Issue/PR로 관리합니다.
