# 팀 역할 및 협업 규칙

## 팀 구성

| 이름 | 역할 | 현재 계획 |
|---|---|---|
| 유선엽 | Backend Lead / 팀장 | 전체 일정·협업 관리, 백엔드 개발 및 구조 정리 |
| 장재혁 | Backend | Java를 학습하며 백엔드 개발 참여 |
| 박지우 | Frontend | React를 학습하며 프론트엔드 개발 참여 |

## 협업 방향

- Frontend와 Backend를 분리해 병렬 개발하고 API 명세를 연동 기준으로 사용합니다.
- 기능별 Branch와 Pull Request를 사용해 변경사항을 검토한 뒤 통합합니다.
- 회원·상품 → 경매 → 입찰 → 낙찰 → 거래 진행 순으로 핵심 거래 흐름을 우선 구현합니다.
- 경매 정책, API 변경, 공통 기능은 팀 단위로 합의합니다.
- AI가 생성하거나 수정한 코드는 담당 개발자가 직접 검토한 뒤 반영합니다.

## 기술 스택

- Frontend: React · JavaScript · Styled Components · React Router
- Backend: Java 21 · Spring Boot 3.5 · Spring Data JPA · Spring Security + JWT
- Database: MySQL 8.4
- Auction: WebSocket(STOMP) · Transaction/Lock · Scheduler
- File / Deploy: Object Storage · Docker
- AI: Multimodal AI API 검토
- 개발 보조 도구: ChatGPT · Claude Code
