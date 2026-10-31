# V2-B.1: 기존 조회 슬롯을 이용한 대안 재확인 실험

기본값은 `legacy`. `known-surplus-v1`도 원래 클래스 그대로 반환한다.
`known-surplus-followup-v1`만 직전 대안 보류 의향을 저장하고 다음에 허용된
일반 방문의 첫 슬롯을 표적 재조회에 사용한다. 부모 `visit/run/place_bid/close`는
상속한다. 기존 알림·재방문·가용성·WTP·가격 비교·예산·정산 공식은 유지한다.

신규 수치 파라미터 0. 가장 최근 의향 하나, 첫 슬롯 우선, 방문당 한 재확인과
중복 조회 방지는 **ASSUMED**. 실측 행동 법칙이나 채택된 기본 모델로 취급하지
않는다. 선택은 기지 quote와 자기 상태만 사용하며, 현재 가격은 실제 조회 뒤에
갱신한다. 조회 요청의 서버 가용성 검사에서만 실제 start/end/closed를 사용한다.

프로젝트 루트의 PowerShell:

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.\.venv\Scripts\python.exe -B -X utf8 -m v2_followup.run --scenario config/scenarios/scenario_A.yaml --seed 1 --model known-surplus-followup-v1 --out data/experiments/v2b1-20261031/manual-example-1
```

출력은 새 경로만 허용한다. 과거 baseline/실험 경로로 저장할 수 없다. 함수 API는
`v2_followup.simulator.make_market(..., model=...)`. 3모드 전환 가능. 이 CLI는
seller_default hard-close만 제공하며 종료 정책 탐색/최적화를 수행하지 않는다.

근거·검증·판정: `validation/v2_followup/PRE_IMPLEMENTATION.md`, `REPORT.md`.
원인 감사의 전지적 가격 대조 코드는 validation 전용으로 런타임에서 import하지 않는다.
