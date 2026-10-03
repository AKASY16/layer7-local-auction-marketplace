# 지역 기반 중고거래 경매 플랫폼

TEAM LAYER7의 캡스톤 프로젝트입니다.

지역 기반 중고거래에 제한시간 경매를 결합한 웹 애플리케이션을 개발합니다. 판매자는 상품과 경매 조건을 설정하고, 구매자는 수동 입찰 또는 자동 입찰에 참여합니다. 경매 종료 후에는 낙찰자의 거래 의사 확인부터 거래 완료·포기·미응답까지의 상태를 관리합니다.

> TEAM LAYER7은 팀명이며 최종 서비스명은 아직 미정입니다.

## Team

| 이름 | 역할 | 담당 |
|---|---|---|
| 유선엽 | Backend Lead / 팀장 | 전체 일정·협업 관리, 백엔드 개발 및 구조 정리 |
| 장재혁 | Backend | Java/Spring 기반 백엔드 개발 |
| 박지우 | Frontend | React 기반 프론트엔드 개발 |

## Tech Stack

- Frontend: React, JavaScript, Styled Components, React Router
- Backend: Java 21, Spring Boot 3.5, Spring Data JPA, Spring Security + JWT
- Database: MySQL 8.4
- Realtime: WebSocket(STOMP)
- Auction consistency: Transaction / Lock
- Scheduler: 예약 시작, 경매 종료, 낙찰 응답 기한 처리
- File: Object Storage
- Deploy: Docker
- Development Assist: ChatGPT, Claude Code

## Core Flow

회원/지역 → 상품 등록 → 예약 또는 즉시 경매 → 수동/자동 입찰 → 경매 종료 → 낙찰 → 거래 응답 → 거래 진행 → 양측 완료 확인

## Documents

- [팀 역할 및 협업 규칙](docs/00-team-and-collaboration.md)
- [프로젝트 기획](docs/01-project-planning.md)
- [요구사항](docs/02-requirements.md)
- [경매 정책](docs/03-auction-policy.md)
- [회의 및 결정사항](docs/04-decisions.md)
- [API 명세](docs/05-api-spec.md)
- [Backend Domain](docs/backend/domain.md)
- [ERD / DB Schema](docs/backend/erd.md)
- [Auction / Trade 상태 모델](docs/backend/auction-state.md)
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
