# V2-A 검증

모든 검증은 `-B`로 실행하고 신규 결과 경로만 사용한다. 기존 `validation/audit/regression.py`는 원 audit 보고서를 쓰므로 이 작업에서 호출하지 않는다.

```powershell
.\.venv\Scripts\python.exe -B validation/v2_observe/test_observer.py
.\.venv\Scripts\python.exe -B validation/v2_observe/regression.py --out data/experiments/v2a-20261031/새회귀경로 --report validation/v2_observe/results/새회귀보고서.json --workers 2
.\.venv\Scripts\python.exe -B validation/v2_observe/benchmark.py --out validation/v2_observe/results/새성능보고서.json
```

## 무엇을 검증하는가

동일 World·시드·종료 정책에서 원 AuditMarket, V2-A OFF, ON을 비교한다. 부모의 **모든 인스턴스 속성**을 검사하며 World는 별도로 전후 해시를 확인한다. WTP cache의 키·값·삽입 순서, 지출·약정·선두·낙찰, bids/events/decisions의 순서·ID, watch/snipes/returns, cat_open, 미활동 거부 이벤트, 큐·seq·visit counter까지 포함한다.

검증 때만 keyrng.u/normal을 감싸 모든 호출·인자·반환값 순서의 SHA-256을 계산한다. normal 내부의 u도 그대로 포함하므로 두 count를 독립 난수 수처럼 더하지 않는다. heapq의 push/pop도 전체 원소와 순서로 해시한다. 관찰 엔진은 이 검증 wrapper나 monkey patch를 사용하지 않는다.

18개는 기존 A–F × seed1–3의 전체 World와 기본 hard-close 정책을 사용한다. 3개 모드의 11개 CSV가 같아야 하고, ON의 실제 저장 바이트가 `AUDIT_FIX_v1.json`의 동결 CSV 198개와도 일치해야 한다. 기존 구조 검사·활동 기간·입찰/예산 재현 validator를 재사용한다. 기존 데이터나 원 보고서는 쓰지 않는다.

작은 통제 실험은 M/T/N 손계산, 미래·마감·자기 자신 제외, soft extension 현재/예정 gap 분리, 실제 view만 A 반영, A 가격의 비자동 갱신, WTP 미평가 상태, 다른 입찰자 상회·정산의 Q snapshot, 비활동·동률·빈 표·덮어쓰기 방지와 6시나리오·변경 정책·soft close의 동등성을 확인한다. 전체 데이터에서는 T⊆M·창 단조성, N과 기존 실제 방문 로그, A와 view의 일대일 대응, Q 회계식, cache 값도 검사한다.

검증 범위는 해당 World·정책·fixture다. 모든 가능한 입력에 대한 수학적 증명이나 행태 가정의 실증 검증이라고 부르지 않는다.

## 성능

회귀의 instrumented 시간은 검증 hashing 비용을 포함하므로 실사용 속도로 제시하지 않는다. benchmark는 병렬 작업 종료 후 scenario_A seed1의 동일 World에서 audit/OFF/ON 순서를 회전해 각3회 측정한다. 초기화·시뮬레이션·메모리 trace 수집을 포함하고 World 생성·CSV 쓰기는 제외한다.

Python 메모리는 별도의 200명/60경매 fixture에서 tracemalloc으로 확인한다. 이는 전체 World의 peak RSS가 아니다. 실제 18개 결과의 진단 CSV 바이트 수는 회귀 보고서에 기록한다. 기존 검증을 통과한 뒤 관련 소스가 바뀌면 해당 검사도 다시 실행한다.
