# Infra / Deployment

## 현재 방향
- Docker
- MySQL 8.4
- Object Storage
- Frontend / Backend 분리 배포 검토
- Frontend와 API는 같은 사이트(등록 도메인)에 배포. Refresh Token 쿠키가 `SameSite=Strict`라 다른 사이트에서는 전송되지 않음 (예: `app.<도메인>` / `api.<도메인>`)
- HTTPS 필수 (Refresh Token 쿠키 `Secure`)

## 추후 결정
- Backend 실제 배포 환경
- Frontend 실제 배포 환경
- 운영 Database 방식
- Object Storage 제공자
- CI/CD 범위
- 도메인 / HTTPS
