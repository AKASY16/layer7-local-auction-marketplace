# V2-A 관찰 전용 엔진 구현 결과

검증일: 2026-10-31. 로컬 브랜치: `codex/v2-a-observer-20261031`. 기준 부모: `audit-fix-v1`, Git 부모 커밋 `9796c6a`. **V2-B는 구현하지 않았다.** 추가 벌점·WTP 조정·구매자 선택 변경은 없다.

## 구현 결과

기존 AuditMarket를 상속한 `v2-a-observe-v1`을 추가했다. 부모의 이벤트 루프·큐·난수·WTP·입찰·예산·가격·proxy·재방문·스나이프·마감 규칙을 복사하거나 수정하지 않았다. 관찰 wrapper는 원 함수를 호출하고 별도 저장소에만 진단을 남긴다. 기존 CSV 11개와 별도로 진단 CSV 6개를 출력한다.

| 새 파일 | 역할·추가 이유 |
|---|---|
| [simulator.py](/experiments/auction-simulator/src/v2_observe/simulator.py) | 부모 함수 전후의 passive wrapper, observer ON/OFF |
| [metrics.py](/experiments/auction-simulator/src/v2_observe/metrics.py) | N과 M/T를 독립 측정; 현재/예정 종료·미등록/마감 제외 |
| [awareness.py](/experiments/auction-simulator/src/v2_observe/awareness.py) | 실제 view에서만 발견·조회 당시 정보를 갱신 |
| [observer.py](/experiments/auction-simulator/src/v2_observe/observer.py) | N/M/T/A/Q·기존 결정·기존 cache의 독립 기록 |
| [export.py](/experiments/auction-simulator/src/v2_observe/export.py) | audit CSV 보존, 진단 스키마·시간·잠재 정보 metadata |
| [__main__.py](/experiments/auction-simulator/src/v2_observe/__main__.py) | 기존 생성 경로를 바꾸지 않는 opt-in CLI |
| [검증 코드](/experiments/auction-simulator/validation/v2_observe/checks.py) | 전체 부모 상태·난수 호출·heap push/pop 순서의 독립 fingerprint |
| [단위 검사](/experiments/auction-simulator/validation/v2_observe/test_observer.py) | 18개 정확성·경계·동등성 테스트 |
| [회귀 검사](/experiments/auction-simulator/validation/v2_observe/regression.py) | 기존 18개 World·CSV의 3모드 전수 비교 |
| [성능 측정](/experiments/auction-simulator/validation/v2_observe/benchmark.py) | 검증 hashing을 제외한 시간·별도 Python 메모리 측정 |

`src/v2_observe/README.md`, `validation/v2_observe/README.md`, 패키지 식별용 `__init__.py`, 이 보고서·검증 JSON·manifest도 신규 추가했다. 기존 README·research 문서의 사용자 변경은 그대로 두었다.

## 기록의 의미

| 구분 | 기록 내용 | 행동에 전달하는가 |
|---|---|---|
| N | 기존 카테고리 마감 신호와 방문·열람 배수. 실제 방문 후보 수락과 판단 시점 측정 분리 | 원래 부모 값만 사용; 관찰 재계산은 전달하지 않음 |
| M | 현재 실제 열린 다른 경매의 기존 유사도 가중 공급량과 속성 일치 proxy 수 | 아니오 |
| T | 같은 M 안에서 1·3·6·12·24h 마감 근접. live/scheduled gap 별도 | 아니오 |
| A | 실제 view에서 얻은 당시 가격·마감·조회 순서·발견 이력 | 아니오 |
| Q | 초기·판단 전후·상회 전후·정산 전후의 spent/committed/leading/won | 아니오 |

WTP는 `wtp_log.get()`으로만 읽는다. 기존 엔진이 평가하지 않은 값은 missing으로 남긴다. 진단 때문에 `wtp()`를 먼저 호출하거나 cache key를 추가하지 않는다. `cached_quote_surplus_after_legacy`는 기존 평가 후 cache와 당시 최소가의 차이를 기록할 뿐, 예상 가격·선택 점수·새 가치가 아니다.

A는 전체 시장을 아는 집합이 아니다. 다른 상품의 가격·마감 연장은 실제 재조회 없이 갱신하지 않는다. 최종 A 표는 마지막 조회 이력이며 현재 열림·최신 가격의 보장이 아니다. Q의 초기화와 활동 종료 후 기존 proxy 정산은 관리 상태 기록이며 새 구매자 활동으로 보지 않는다.

등록 진단은 실제 LIST 처리 직후, 그 경매의 알림 전이다. 같은 시각에도 아직 처리되지 않은 LIST는 포함하지 않는다. M/T의 `start,end)` 진단 정의는 원 엔진의 마감 동률 처리를 바꾸지 않는다. `trace_id`는 관찰 기록 순서, `engine_log_length`는 기존 로그 위치이며 원 heap 번호와 구분한다.

## 행동 동등성·회귀 결과

**18개 단위 테스트 통과, 18/18 전체 회귀 통과, 동결된 audit CSV 198/198 바이트 일치.** 실제 view **735,965건**의 관찰 정확성 불변식도 검사했다.

각 World·시드·기본 종료 정책을 공유한 다음 세 실행을 비교했다.

1. 원 `audit-fix-v1`
2. V2-A observer OFF
3. V2-A observer ON

부모의 모든 인스턴스 속성을 비교했다. 별도 `observer` 저장소를 제외하고 bids/events/decisions의 전체 내용·순서·ID, WTP cache의 키·값·삽입 순서, 지출·약정·선두·낙찰, watch/snipes/returns, cat_open/cat_ends, 미활동 거부 이벤트, heap/seq/visit counter와 기타 부모 속성이 동일했다. World도 실행 전후 동일했다.

검증 때만 keyrng.u/normal의 전체 호출 인자·반환값·순서와 heap push/pop의 전체 원소·순서를 해시했다. 난수 및 큐 스트림도 세 모드가 동일했다. normal 내부 u도 기록하므로 함수 호출 수를 독립 난수 개수로 더하지 않는다. 이 검증 instrumentation은 실제 엔진에 포함되지 않는다.

CSV는 새 실행끼리의 비교에 그치지 않고 `AUDIT_FIX_v1.json`의 기존 198개 파일 해시와 실제 생성 바이트를 대조했다. 기존 구조·입찰 순서·가격·예산·활동 기간 validator도 18개 모두 통과했다. 새로운 metadata와 진단 CSV는 의도적으로 별도이며, 기존 11 CSV의 동등성을 주장한다.

정확성 테스트는 N=.4, M=1.1 등 손계산 가능한 fixture, T 부분집합·창 단조성, 자기 자신·미등록·마감·오른쪽 경계 제외, 현재/예정 마감의 soft extension, A와 실제 view의 일대일 대응, WTP 미평가 유지, 다른 입찰자 상회와 proxy 사후 정산의 Q, 빈 표 스키마·덮어쓰기 차단을 포함했다. 6개 축소 시나리오·변경 종료 정책·soft-close 동률에서도 난수·큐·전체 상태를 비교했다.

전체 18개는 기존 A–F × seed1–3의 **기본 hard-close 정책**이다. 모든 가능한 World·정책에 대한 수학적 증명으로 확대하지 않는다.

상세 결과: [회귀 JSON (미업로드), 성능 JSON (미업로드).

## 성능 영향

같은 A 시나리오 seed1 World(1,500명·500경매·30일)에서 모드 순서를 회전해 각 3회 측정했다. 기준 World 생성, CSV 쓰기, 검증 hashing은 제외하고 엔진 초기화·시뮬레이션·메모리 진단 수집을 포함했다. 회귀 worker는 종료했고 다른 시스템 부하는 통제하지 않았다.

| 모드 | 중앙값 |
|---|---:|
| 부모 audit | 2.969초 |
| observer OFF | 3.012초 |
| observer ON | 8.934초 |

ON은 OFF의 **2.97배**, OFF는 부모의 1.015배였다. 단일 World·로컬 컴퓨터의 소수 반복 측정이므로 작은 OFF 차이를 확정적 성능 저하로 일반화하지 않는다. 이 실행에서는 기존 입찰 6,633건·기존 이벤트 99,502건에 더해 실행 중 진단 428,573행을 기록했다. 최종 A 이력 표는 내보낼 때 별도 구성한다.

메모리는 별도의 **200명·60경매·10일** World에서 tracemalloc으로 엔진 이후 Python 할당만 측정했다. 부모 peak 2.27MiB, OFF 2.27MiB, ON **17.71MiB**였다. 원 World 생성 전의 메모리·OS RSS·전체 500경매의 peak가 아니다.

18개 진단 CSV의 합계는 **768,159,424바이트(732.6MiB)**다. 기존 11개 CSV의 새 회귀 복사본과 metadata는 이 크기에서 제외했다. 실제 경로는 `data/experiments/v2a-20261031/regression-1/`이다. 모든 trace를 메모리에 모으므로 큰 World에서는 메모리와 쓰기 비용이 커진다.

## 보존·미해결 사항

분석 시작 전 존재하던 **1,313개 파일의 변경·삭제는 0건**이다. baseline-v4 정의 33개·CSV198개, audit-fix 소스13개·CSV198개, 배치 자료77개가 모두 기존 manifest와 일치했다. 새 파일은 src/v2_observe, validation/v2_observe, data/experiments/v2a-20261031 아래에만 추가했다. Git metadata·venv·pycache는 파일 비교 범위에서 제외한다.

남은 한계는 다음과 같다.

- 진단값의 정확성과 행동 무영향을 검증했다. N·유사도·활동 곡선·포기 규칙의 실증 타당성을 새로 입증한 것은 아니다.
- 실제 SKU가 없는 합성 World의 category/subcategory/series/condition/rarity 속성 일치 수는 proxy다. 동일 상품이나 B-04의 영화 버전 집합으로 취급하지 않는다. 식별 속성이 없으면 unknown으로 남긴다.
- A는 실제 view 기록이며 구매자의 완전한 지식·기대 가격·희망 수량 모형이 아니다. 순위·선택·무료 가격 갱신을 추가하지 않았다.
- 관찰 비용은 0이 아니다. 스트리밍과 공급 집계 인덱스 최적화는 별도 과제로 남는다. 기록을 생략하거나 성능을 위해 행동을 변경하지 않았다.
- Q·WTP에는 잠재 진실이 들어 있다. 진단표를 그대로 추천 모델에 공급해서는 안 된다.
- V2-B 선택 정책, 새로운 벌점·WTP 조정·행동 계수, 보정 변경은 포함하지 않는다.

## 실행

```powershell
.\.venv\Scripts\python.exe -B src/v2_observe/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --out data/experiments/새경로/on
.\.venv\Scripts\python.exe -B src/v2_observe/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --no-observer --out data/experiments/새경로/off
```

존재하는 출력 경로와 baseline/audit 데이터 덮어쓰기는 거부한다. 재현 명령·범위는 [검증 안내](/experiments/auction-simulator/validation/v2_observe/README.md)에 있다.
