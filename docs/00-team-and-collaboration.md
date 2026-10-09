# 팀 역할 및 협업 규칙

## 팀 구성

| 이름 | 역할 | 현재 계획 |
|---|---|---|
| 유선엽 | Backend / 팀장 | 전체 일정·협업 관리, 백엔드 개발 및 구조 정리 |
| 장재혁 | Backend | Java를 학습하며 백엔드 개발 참여 |
| 박지우 | Frontend | React를 학습하며 프론트엔드 개발 참여 |

## 협업 방향

- Frontend와 Backend를 분리해 병렬 개발하고 API 명세를 연동 기준으로 사용합니다.
- 기능별 Branch와 Pull Request를 사용해 변경사항을 검토한 뒤 통합합니다.
- 회원·상품 → 경매 → 입찰 → 낙찰 → 거래 진행 순으로 핵심 거래 흐름을 우선 구현합니다.
- 경매 정책, API 변경, 공통 기능은 팀 단위로 합의합니다.
- AI가 생성하거나 수정한 코드는 담당 개발자가 직접 검토한 뒤 반영합니다.

## 작업 흐름

```text
Issue 고르기 → 보드에서 In Progress로 이동 → 브랜치 만들기 → 커밋
→ PR 올리기 (본문에 Closes #이슈번호) → 보드에서 In Review로 이동
→ 리뷰 · 승인 1개 + CI 통과 → Squash and merge → 브랜치 삭제 → 이슈 자동 종료(Done)
```

- 작업은 모두 GitHub Issue에서 시작합니다. 이슈가 없는 작업이면 먼저 이슈를 만듭니다.
- 진행 상황은 [개발 보드](https://github.com/users/AKASY16/projects/1)에서 카드를 옮겨 공유합니다.
- 막히면 혼자 오래 붙잡지 않고 이슈 댓글이나 디스코드에 바로 남깁니다.

## 브랜치

- `main`은 보호되어 있어 직접 push할 수 없습니다. PR, 승인 1개, CI(backend, frontend) 통과가 있어야 병합됩니다.
- 브랜치 이름은 `종류/이슈번호-요약`입니다. 요약은 영어 소문자와 하이픈으로 씁니다.
  - 예: `feat/21-bid-increment-policy`, `fix/40-login-error-message`, `docs/18-dev-rules`
- 종류

| 종류 | 쓰는 경우 |
|---|---|
| `feat` | 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 동작을 바꾸지 않는 코드 정리 |
| `test` | 테스트만 추가·수정 |
| `docs` | 문서 |
| `chore` | 설정, 빌드, 의존성 |
| `ci` | GitHub Actions 등 CI |

- 브랜치 하나에는 이슈 하나만 담습니다.
- 항상 최신 `main`에서 시작합니다.

```bash
git switch main
git pull
git switch -c feat/21-bid-increment-policy
```

- 작업이 길어지면 중간에 `main`의 변경을 받아옵니다: `git fetch origin` 후 `git merge origin/main`. 충돌이 나면 혼자 해결하려 하지 말고 공유합니다.

## 커밋

- 형식은 `종류: 요약`이고, 종류는 브랜치와 같은 목록을 씁니다. 요약은 한국어로 써도 됩니다.
  - 예: `feat: 가격단위표 다음 유효 금액 계산 추가`
- 커밋 하나에는 한 가지 의도만 담습니다. 기능 추가와 관련 없는 포맷 정리를 섞지 않습니다.
- 빌드가 깨진 상태로 push하지 않습니다.
- AI 도구가 만든 코드도 본인이 이해한 뒤 커밋합니다. 리뷰에서 설명할 수 없는 코드는 올리지 않습니다.

## Pull Request

- 제목은 커밋과 같은 형식입니다. Squash 병합을 하면 PR 제목이 `main`의 커밋 메시지가 됩니다.
- 본문은 PR 템플릿을 채우고, `Closes #이슈번호`를 꼭 씁니다. 병합되면 이슈가 자동으로 닫힙니다.
- 크기는 변경 400줄 안팎을 목표로 하고, 넘으면 나눕니다. 자동 생성 파일과 `package-lock.json`은 줄 수에서 뺍니다.
- 올리기 전에 로컬에서 빌드와 테스트를 통과시킵니다.
- 방향이 맞는지 일찍 확인받고 싶으면 Draft PR로 먼저 올립니다.
- 병합은 Squash and merge로 하고, 병합 후 브랜치를 삭제합니다.
- 앞 PR이 병합되기 전에 그 위에 다음 PR을 쌓지 않습니다. 의존하는 작업은 앞 PR이 병합된 뒤 최신 `main`에서 시작합니다.

## 코드 리뷰

- 리뷰 요청을 받으면 24시간 안에 1차 리뷰를 합니다.
- 승인 기준은 세 가지입니다: 의도대로 동작한다, 명세와 [코드 컨벤션](backend/conventions.md)에 맞는다, 읽고 이해할 수 있다.
- 질문도 리뷰입니다. 이해되지 않는 부분은 그대로 물어봅니다.
- 댓글 앞에 성격을 붙입니다.

| 접두사 | 의미 | 승인 여부 |
|---|---|---|
| (없음) | 고쳐야 하는 것 | 고친 뒤 승인 |
| `question:` | 궁금한 것 | 답을 듣고 판단 |
| `nit:` | 사소한 제안 (이름, 줄바꿈 등) | 안 고쳐도 승인 가능 |

- 사람이 아니라 코드에 대해 말합니다. 예: "왜 이렇게 했어요?" 대신 "이 부분은 동시에 요청이 오면 어떻게 되나요?"
- 작성자는 모든 댓글에 답하고, 해결된 대화는 Resolve합니다.
- 의견이 갈리면 디스코드에서 짧게 이야기하고, 결론을 PR 댓글로 남깁니다.

## 기술 스택

- Frontend: React 19 · Vite · JavaScript · Styled Components · React Router
- Backend: Java 25 · Spring Boot 4.1 · Spring Data JPA · Spring Security + JWT · Flyway
- Database: MySQL 8.4
- Auction: WebSocket(STOMP) · Transaction/Lock · Scheduler
- File / Deploy: Object Storage · Docker
- AI: Multimodal AI API 검토
- 개발 보조 도구: ChatGPT · Claude Code
