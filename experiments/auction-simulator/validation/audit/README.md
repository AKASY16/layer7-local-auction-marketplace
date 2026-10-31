# 독립 감사 실행 안내

최종 진단은 [REPORT.md](REPORT.md), 수정 전 진단은 [diagnosis_before_fixes.md](diagnosis_before_fixes.md), 발현 범위 보충은 [diagnosis_addendum.md](diagnosis_addendum.md)에 있다.

baseline-v4는 그대로 남아 있다. 기존 src/generate.py는 원본 엔진이다. 수정 엔진은 src/audit/ 아래에 있으며 명시적으로 실행해야 한다. 실측 보정값·대체성 규칙·활동 곡선·재입찰 가정은 바꾸지 않았다.

## 수정 엔진 실행

프로젝트 폴더의 PowerShell에서:

    .\.venv\Scripts\python.exe src/audit/__main__.py --scenario config/scenarios/scenario_B.yaml --seed 1101 --out data/experiments/new-audit-run

종료 시각 CSV는 원본과 같은 auction_id, scheduled_end_at(오프셋 포함 ISO)이며 --end-times로 지정한다. 모형 기간은 동결된 24–72시간을 유지한다. LAYER7 명세 전체인 1시간–7일을 검증한 생성기로 해석하지 않는다.

출력은 data/experiments 아래 **새 폴더**여야 한다. 기존 폴더와 data/synthetic을 덮어쓰는 요청은 거부한다. metadata에는 audit-fix-v1과 parent_baseline=baseline-v4가 기록된다.

## 검사

    .\.venv\Scripts\python.exe validation/audit/test_audit.py
    .\.venv\Scripts\python.exe validation/audit/controls.py --engine audit-fix-v1 --out validation/audit/new-controls.json
    .\.venv\Scripts\python.exe validation/audit/regression.py --out data/experiments/new-audit-regression --workers 4
    .\.venv\Scripts\python.exe validation/audit/validate_dataset.py --root data/experiments/new-audit-regression --out validation/audit/new-extended-check.json

전체 재현 검사는 원본 18개와 수정본 18개, 수정본 반복본을 새 폴더에 만든다. 원본 CSV와 바이트 비교하며 기존 가격·선두·예산 검사를 재사용한다. 활동 기간 정합성은 추가 검사다. 기존 validation/results.json과 baseline-v4는 갱신하지 않는다.

## 메커니즘 탐색

    .\.venv\Scripts\python.exe validation/audit/experiments.py --out data/experiments/new-audit-probes --workers 4

- 독립 세계 시드 1101–1112, B/C/D 원 규모.
- 21시 동시 마감과 저녁 분산의 차이를 두 엔진에서 비교한다. 기간/노출도 변하므로 일정 총효과다.
- B에서 같은 외생 세계를 유지한 평탄·12시간 피크 이동 곡선을 추가한다. 방문 후보 상한의 유효성을 검사한다.
- C에서 세계당 2회, 경매 10% 종료를 변경한다. seed/perturbation/auction_id를 보존한다.
- 시드별 차이의 평균·SD·SE·95% t 구간과 시드 bootstrap을 저장한다. 반복 경매 회귀는 seed cluster의 탐색 분석이다.
- 음의 충돌 계수나 특정 정책 승리를 통과 조건으로 삼지 않는다. 소수 세계와 모형 가정의 한계를 보고한다.

실행 당시 원시 요약은 data/experiments/audit-20261030/probes/*.csv, 수치 결과는 experiment_results.json이다. 서로 다른 실험을 실행할 때 원시 출력 폴더 이름을 구분한다. 감사 도구의 요약 JSON은 validation/audit 안의 최신 실행 결과로 갱신되므로, 기록을 보존하려면 기존 감사 브랜치 커밋/보고서와 함께 새 실행 결과를 별도 이름으로 보관한다.

## 버전과 근거

BASELINE_v4.json은 원본 33개 정의 파일과 198개 CSV의 해시다. AUDIT_FIX_v1.json은 부모 기준선과 추가 소스, 수정본 198개 CSV의 해시다. 원본을 새 기준선으로 덮어쓰지 않는다. 실데이터에서 얻은 입력 수치와 이를 한국 수집품의 행동·잠재 가치로 옮기는 가정은 구분한다. 특히 B2B 경매당 참여 탄력도를 방문·열람에 적용하는 연결은 ASSUMED다.

원래 validation/check_baseline.py는 원본 재생성용으로 계속 사용할 수 있다. 이 감사에서는 동일한 원본 생성/CSV 비교와 구조 검사 함수를 별도의 출력 경로에서 실행했고 기존 보고서는 덮어쓰지 않았다.
