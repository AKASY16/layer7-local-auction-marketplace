"""Render the final audit from saved measurements; never edits baseline inputs."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'validation/audit'
B = chr(96)


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def mean(records, section, metric):
    return float(np.mean([r[section][metric] for r in records]))


def ci_text(value, factor=1.):
    lo, hi = value['ci95_t']
    return f"{factor*value['mean']:+.3f} [{factor*lo:+.3f}, {factor*hi:+.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outputs', type=Path)
    args = ap.parse_args()
    regression = read('regression_results.json')
    experiments = read('experiment_results.json')
    initial = read('baseline_data_audit.json')
    extended = read('extended_structure_results.json')
    records = list(regression['datasets'].values())
    assert regression['all_pass'] and extended['all_pass']
    n_bids = sum(r['baseline_bid_count'] for r in records)
    fixed_bids = sum(r['corrected_bid_count'] for r in records)
    bad_bids = sum(r['baseline_activity_bad_bids_exact'] for r in records)
    table = []
    for scenario in 'ABCDEF':
        rs = [r for key, r in regression['datasets'].items() if key.startswith(f'scenario_{scenario}/')]
        table.append(f"| {scenario} | {np.mean([r['baseline_bid_count'] for r in rs]):.1f} → {np.mean([r['corrected_bid_count'] for r in rs]):.1f} | "
                     f"{mean(rs, 'baseline_moments', 'bids_per_bidder_in_auction_mean'):.3f} → {mean(rs, 'corrected_moments', 'bids_per_bidder_in_auction_mean'):.3f} | "
                     f"{mean(rs, 'baseline_moments', 'slope_log_price_log_bids_sold'):.3f} → {mean(rs, 'corrected_moments', 'slope_log_price_log_bids_sold'):.3f} | "
                     f"{sum(r['baseline_activity_bad_bids_exact'] for r in rs)} → 0 |")
    contrasts = []
    for scenario, variant in [('B', 'original'), ('C', 'original'), ('D', 'original'), ('B', 'flat'), ('B', 'shift12h')]:
        key = f'{scenario}/{variant}'
        a = experiments['policy_contrasts'][key+'/baseline-v4']['mean_revenue_value_ratio']
        b = experiments['policy_contrasts'][key+'/audit-fix-v1']['mean_revenue_value_ratio']
        contrasts.append(f'| {key} | {ci_text(a, 100)} | {ci_text(b, 100)} |')
    cluster = experiments['exploratory_repeated_shift_ols']['audit-fix-v1']['delta_revenue_value_ratio']
    c_beta = cluster['beta'][2]
    c_se = cluster['seed_cluster_se'][2]
    c_ci = cluster['ci95_seed_cluster_t'][2]
    spill = experiments['spillover']['audit-fix-v1']['share_unmoved_changed_outcomes']
    oldspill = experiments['spillover']['baseline-v4']['share_unmoved_changed_outcomes']
    text = f'''# LAYER7 경매 시뮬레이터 독립 감사·개선 보고서

2026-10-30 · 대상: /experiments/auction-simulator

**확인된 구현 오류를 별도 엔진 audit-fix-v1에서 수정했고, baseline-v4의 코드·설정 33개와 데이터 CSV 198개는 보존했다. 원본과 수정본 모두 18개 재현·구조 검증을 통과했다. 그러나 이 결과로 실제 LAYER7 추천 알고리즘의 성과를 입증할 수는 없다.** 수정 이후에도 종료 시각 충돌의 독립 효과는 불확실하고 활동 곡선·대체성·참여 모형의 경험적 근거가 부족하다.

## 1. 작업과 보존 방식

- 전달받은 폴더는 Git 저장소가 아니었다. 로컬 baseline-v4 브랜치/커밋 cc32802를 만든 뒤 audit/2026-10-30에서 작업했다. 기준선 커밋의 작성자는 Codex Audit이다.
- 수정 전 최소 통제 실험과 진단을 먼저 저장하고 커밋 026df6d로 보존한 뒤 수정했다. 기록은 diagnosis_before_fixes.md와 results_before.json에 있다. 발현 범위를 좁혀 확인한 내용은 diagnosis_addendum.md에 분리했다.
- 동결된 src/*.py·원본 YAML·파라미터·기존 검증 결과는 수정하지 않았다. 수정본은 src/audit/ 확장으로 추가해 기존 구현을 상속/재사용한다. README에는 새 감사 결과 안내만 덧붙였다.
- 새 데이터는 data/experiments/audit-20261030/에만 썼다. audit 내보내기는 기존 디렉터리와 data/synthetic 쓰기를 거부한다. 기준선은 Git에 코드·설정·해시 목록을 보관하고, 기존 실제 CSV는 원래 위치에 그대로 유지한다.
- 새 모델은 기본 실행을 대체하지 않는다. 기존 src/generate.py는 계속 baseline-v4를 만든다. audit-fix-v1은 별도 명령으로 선택한다.

## 2. 전체 구조와 감사 범위

| 영역 | 실제 역할 | 감사 방법 |
|---|---|---|
| world.py | 판매자·상품·구매자·예산·활동 기간·방문 후보의 외생 세계 | 코드 추적, 세계 해시·재빌드·변형 방지 확인 |
| market_simulator.py | 목록·방문·열람·프록시 입찰·재방문·마감의 사건 큐 | 최소 재현, 개별 수정 대조, 전체 18개 재실행 |
| keyrng.py | seed/목적/ID 기반 난수 | 1,800개 키의 호출 순서 불변성, 동일 정책 재실행 |
| generate.py | 종료 입력 검사와 CSV/metadata 직렬화 | 198 CSV 재생성 비교, 빈 시장 읽기/쓰기 |
| calibration와 A–F 설정 | 실측·논문·가정 및 보정값 | 사용 위치·이전 가정 검토, 변경 없이 보호 |
| sensitivity.py·mechanism_check.py | 전체 일정/일부 변경 민감도·지표 계산 | 의존성·기간 혼입·수익 정의를 분리 |
| validate.py·check_baseline.py | 가격·예산 재생, 통계, 해시/재현 검사 | 기존 구조 함수와 생성/해시 절차를 18개에 재사용 |
| BARISTA·실데이터 연구 | 입찰 시각 적합과 파라미터 근거 | 코드/기존 자료 역할 확인, CDF 역변환 회귀 검사 |

이번 감사는 원자료 4종의 전체 통계를 다시 추정하거나 논문 네 편의 모든 식·표를 재현한 작업은 아니다. 이전 보고서의 관측 결과를 정답으로 고정하지 않고, 아래 결론은 소스와 새 실험으로 확인했다. 원자료 재스캔·한국 이용자 외적 검증·BARISTA 전체 재적합은 하지 않았다.

## 3. 오류·설계·자료 부족의 분류

| 분류 | 발견 | 조치 |
|---|---|---|
| 구현 오류 | 구매자 leave_at 뒤에도 예약된 SNIPE 실행 | 신규 구매자 사건의 예약을 [join_at, leave_at)로 제한 |
| 잠재 구현 오류 | thickness가 아직 등록되지 않은 경매·soft 연장 전 시각을 셈 | 실제 열린 경매의 현재 end로 계산 |
| 구현 오류 | 이벤트 0건이면 CSV 변환 KeyError, 빈 표 헤더 누락 | 기존 직렬화에 빈 표 스키마만 보완 |
| 검증 누락 | 기존 구조 검사에 활동 기간 검사가 없음 | 원 구조 검사 + 활동 기간 + bid 이벤트 대응 검사 추가 |
| 통계 설계 | 동일 세계·동일 경매 반복을 iid 관측처럼 회귀 | 시드별 대응 차이, seed cluster의 탐색 회귀로 분리 |
| 모형 설계 | 선두/보유 대체재 회피가 시간 간격과 무관하게 지속 | 유지. 임의 충돌 패널티·재구매 창을 추가하지 않음 |
| 모형 설계 | outbid 뒤 10분 예외가 실제 최근 방문을 보장하지 않음 | 기존 ASSUMED 규칙으로 유지, 한계 명시 |
| 자료 부족 | 한국 활동 곡선·분 단위 충돌·수집품 대체성·알림 확인 자료 부족 | 경험적으로 검증됐다고 표현하지 않음 |

### 활동 종료 오류

최소 사례에서 활동 종료 1000분인 구매자가 1499.084분에 입찰했다. 기존 CSV에서도 초 단위 저장 오차를 제외하고 {bad_bids}건을 확인했고 모두 snipe였다. 실제 세계의 정밀 시간으로 재실행해도 {bad_bids}건이다. 기존 구조 검사는 18/18 통과하므로 과거의 구조 통과가 이 조건의 검증을 의미하지 않는다.

수정본의 새 입찰·방문·열람 이벤트는 활동 기간 안에서만 실행된다. 과거에 유효하게 낸 프록시 입찰은 구매자가 떠난 뒤에도 낙찰·정산될 수 있다. 활동 종료 시 보유 입찰을 취소하는 행동 규칙은 넣지 않았다.

### 시장 두께 오류의 제한된 발현 범위

미래 경매 포함은 **48시간 창** 통제에서 확인했다. baseline의 실제 창은 **6시간**, 최소 경매 기간은 **24시간**이다. 따라서 아직 시작하지 않은 경매가 기본 설정의 6시간 안에 끝날 수 없으며, 이번 18개에서 이 수정만으로 입찰 수가 달라지지 않았다. 6시간 창 전체 실행 통제에서도 입찰·이벤트가 동일했다. 이 잠재 오류를 기존 spillover의 원인으로 주장하지 않는다. 선택적 soft-close의 전체 경험적 타당성과 예산 재생 검사는 별도 과제로 남는다.

## 4. 대체성과 종료 충돌의 최소 통제

동일 구매자·상품·열람 시각·넉넉한 예산·평탄 활동을 고정하고 유사도와 종료 간격만 바꿨다. 열람은 양 경매에 동일하게 제공해 검색/주의력 경로를 제거했다. 수정 전후 결과는 동일하다.

| 유사도 | 종료 간격 | 입찰 수 | 대체재 회피 |
|---|---|---|---|
| 0 | 0분 | 2 | 0 |
| 0 | 180분 | 2 | 0 |
| 1 | 0분 | 1 | 1 |
| 1 | 180분 | 1 | 1 |

**대체재 회피는 작동하지만 이것만으로 '유사 경매를 3시간 띄우면 성과가 좋아진다'는 메커니즘이 생기지는 않는다.** 현재 보유/선두 상태는 종료 간격 뒤에도 지속한다. 이 통제는 전체 시장의 충돌 효과가 항상 0임을 증명하지 않는다. 전체 시장에서는 검색 노출·마감 임박 가중·예산 해제·참여가 함께 바뀐다. 그 총효과를 별도로 측정했다.

## 5. 난수와 경매 간 간섭

- 같은 세계와 일정에서 전체 입찰·결과를 반복 비교했고, 다른 일정을 실행한 뒤 원래 일정으로 돌아와도 재현됐다. 세계 객체도 변하지 않았다.
- 키 난수는 확인한 1,800개 키에서 호출 순서에 영향을 받지 않았다. 이는 난수의 통계적 독립성이나 모든 정책에서 좋은 공분산을 보장하는 증명은 아니다. 입찰 수·보유 수를 키에 쓰므로 상태가 달라지면 사용하는 키도 달라진다.
- 전역 visit_id는 다른 경매에서 방문이 추가되면 바뀔 수 있다. 이를 행동 변화로 세지 않았다. 경매별 의미 있는 입찰·상태를 비교했다.
- 관심 카테고리·구매자·예산을 완전히 분리한 두 구성요소에서 한쪽 종료를 바꿔도 반대쪽 입찰/상태는 같았다.
- C에서 경매 10%의 종료를 바꾸는 실험은 독립 세계 12개 × 변경 2회다. 수정 후 변경하지 않은 경매의 상태 변화 비율은 **{100*spill['mean']:.2f}%**, 95% 구간 [{100*spill['ci95_t'][0]:.2f}%, {100*spill['ci95_t'][1]:.2f}%]다. 같은 새 실험의 원본 엔진은 {100*oldspill['mean']:.2f}%다.

여기서 상태는 가격·선두·선두 최대액·입찰 수·입찰자 집합을 뜻한다. 단순 매출/낙찰자 변화율과 같지 않다. 공유 구매자·주의력·예산·보유 이력·카테고리 참여를 통해 간섭이 전파될 수 있다. 이 감사로 관측된 모든 간섭 경로를 일대일 증명한 것은 아니지만, '바꾸지 않은 경매가 변했으니 모두 난수 오류'라는 설명도 맞지 않는다. 변경한 경매만의 수익 증가로 정책 성과를 판정하면 주변 경매 손익을 놓치므로 전체 시장을 함께 보고한다.

## 6. 독립 시드 정책 비교와 불확실성

독립 세계 시드는 **1101–1112**, 시나리오는 전체 규모 B/C/D다. B에는 평탄 곡선과 12시간 피크 이동을 더했다. 모든 변형에서 먼저 만든 같은 외생 세계·상품·구매자·방문 후보를 보존하고 활동 입력만 바꿨다. 원 후보 흐름의 thinning 상한이 변경 곡선을 덮는지도 검사했다. 기존 E3처럼 cfg를 바꿔 World.build를 다시 만들면 방문 후보 수가 달라져 이후 순차 난수와 구매자 특성까지 바뀔 수 있다.

원본/수정본 각각 **21시 동시 마감 − 저녁 분산 마감**의 대응 차이를 먼저 만들고 시드 간 SD·SE·95% t 구간·시드 bootstrap 구간을 계산했다. 두 일정은 기간/노출 길이도 바꾸므로 **일정 변경의 총효과**이며 순수 시각/충돌 효과라고 부르지 않는다. 추천 알고리즘이나 판매자 TOP 3 선택을 평가한 실험도 아니다.

아래 지표는 mean(수익/상품 추정가), 유찰은 0이다. 표의 단위는 이 비율의 **퍼센트포인트**, 대괄호는 시드 12개로 계산한 95% t 구간이다. 실제 낙찰가가 몇 % 올랐다는 수치가 아니다.

| 셀 | baseline-v4 | audit-fix-v1 |
|---|---|---|
{chr(10).join(contrasts)}

수정본에서 B/C의 원 활동 곡선 조건은 구간이 0을 포함한다. D는 모형이 가정한 집중 이점이 나타난다. B의 피크를 옮기면 같은 외생 세계에서도 차이가 달라진다. 어떤 일정이 항상 이기도록 만들지 않았다. 수정 전후 정책 차이의 변화에 대한 대응 구간도 experiment_results.json에 있다.

기존 mechanism_check의 sum(수익)/sum(추정가)와 sensitivity의 mean(수익/추정가)는 서로 다르다. 새 원시 결과는 두 비율, KRW/경매, 판매율, 입찰자/경매를 각각 저장한다. 95% 구간은 모형이 맞다는 조건에서의 Monte Carlo 불확실성이며 한국 시장·가정의 불확실성이 아니다. 소수 클러스터·다중 비교의 한계가 있어 구간은 점별 탐색 결과로 해석한다.

### 반복 경매 관측의 회귀

C에서 시드 12개, 각 2회 perturbation, 변경 경매 합계 **1,200행/엔진**을 수집했다. seed·perturbation·auction_id를 보존해 독립 세계가 1,200개인 것처럼 취급하지 않는다. Δ활동 가중치·Δ동일 시리즈 충돌·Δ기간을 공변량으로 넣고 같은 세계 전체를 클러스터로 묶었다.

수정본의 충돌 계수는 **{c_beta:+.5f}**, seed-cluster SE **{c_se:.5f}**, 자유도 11의 95% 구간 **[{c_ci[0]:+.5f}, {c_ci[1]:+.5f}]**다. 음의 점추정이지만 0을 포함하므로 음의 충돌 효과를 확인했다고 말하지 않는다. Δ기간을 넣고 클러스터 SE를 썼다고 간섭과 누락 변수 문제가 없어지는 것도 아니다. 이 회귀는 직접 충돌의 인과 추정이 아닌 탐색적 연관이다. 기존 2개 세계에서 나온 iid SE를 그대로 재해석하지 않았다.

## 7. 기존 결과와 수정 후 차이

기존 전체 입찰 {n_bids:,}건 → 수정본 {fixed_bids:,}건. 활동 종료 위반 {bad_bids}건 → 0건. 순감소가 {n_bids-fixed_bids}건인 이유는 차단 이후 재입찰·예산·낙찰 경로가 다시 계산되기 때문이다. 원 CSV에서 146행만 삭제해 만든 데이터가 아니다.

아래는 각 시나리오 기존 시드 1–3 평균이다. 통계량을 다시 맞추기 위한 튜닝은 하지 않았다.

| 시나리오 | 총 입찰 수: 원본 → 수정 | 입찰자–경매 쌍당 입찰 수 | 낙찰가–입찰 수 기울기 | 활동 위반 합계 |
|---|---|---|---|---|
{chr(10).join(table)}

모든 통계량·가격 log SD·조회–입찰 기울기·막판 비율·재입찰 쌍 비율의 원본/수정/차이는 regression_results.json과 calibration_changes.csv에 저장했다. 원래 남아 있던 가격 분산·재입찰 비율·조회 관계의 불일치는 이번 수정으로 해결했다고 간주하지 않는다. 특히 입력 실측 낙찰가 SD를 잠재 가치 SD로 사용하는 것은 별도 ASSUMED 이전이다.

## 8. 회귀 검증 결과

| 검사 | 결과 |
|---|---|
| 원래 정의 파일 33개·CSV 198개 해시 | 변경 0 |
| 원본 엔진 18개 재생성 | 198/198 CSV 바이트 동일 |
| 기존 가격·증가분·선두·낙찰·예산 재생 검사 | 원본 18/18, 수정본 18/18 |
| 수정본 동일 세계 재실행 | 18/18, 198/198 CSV 동일 |
| 수정본 정밀 시간 활동 기간 검사 | 입찰·방문 이벤트 위반 0 |
| 확장 CSV 구조·활동 기간·입찰 이벤트 대응 | 18/18 |
| 경계·프록시 정산·빈 시장·동결 보호·통계 단위·BARISTA CDF·정의 불가 통계 JSON 회귀 테스트 | 11/11 |
| 분리된 시장 간 무간섭, 동일 정책 재실행, 외생 세계 비변형 | 통과 |

CSV의 ISO 시각은 초 단위여서 확장 CSV 검사에는 1초 허용치를 명시했다. 별도 in-memory 검사는 정확한 분 단위 실수 시간과 [join, leave)를 사용했다. BARISTA CDF 회귀 통과를 모든 데이터 적합도 검증으로 확대하지 않는다.

콜드스타트 F의 일부 카테고리는 낙찰 표본이 부족해 가격 log SD가 정의되지 않는다. 이 통계는 JSON의 null과 CSV의 공란으로 표시했다. 0으로 대체하거나 보정값을 바꾸지 않았다. 원본 기존 보고서의 표기는 보존한다.

## 9. 변경 파일과 실행법

| 파일/영역 | 수정 이유 |
|---|---|
| src/audit/simulator.py | 원 Market 상속, 활동 기간 보호와 실제 열린 경매 두께 |
| src/audit/export.py | 원 직렬화 재사용, 빈 표 스키마·버전 표기·덮어쓰기 차단 |
| src/audit/__init__.py·__main__.py | 수정본 버전과 명시적 생성 진입점 |
| validation/audit/common.py·controls.py | 최소 세계, 대체성×충돌, 난수·간섭 통제 |
| baseline_audit.py·regression.py·validate_dataset.py | 기존/수정본 데이터 감사·전체 회귀·활동 검사 |
| uncertainty.py·experiments.py | 독립 시드 대응 차이·클러스터 회귀·원시 식별자 보존 |
| test_audit.py | 확인된 오류와 통계 단위의 회귀 방지 |
| report.py·REPORT.md·README.md·진단/JSON/CSV | 재현 가능한 결과 및 해석·근거 보관 |
| AUDIT_FIX_v1.json | 수정본 소스·부모 기준선·수정 데이터 해시 |
| 프로젝트 README.md | 동결 원본과 선택 수정본의 구분 안내 |

프로젝트 폴더에서 PowerShell로 실행한다. OUT은 기존 결과를 덮지 않도록 매번 새 경로로 지정한다.

    .\\.venv\\Scripts\\python.exe validation/audit/test_audit.py
    .\\.venv\\Scripts\\python.exe src/audit/__main__.py --scenario config/scenarios/scenario_B.yaml --seed 1101 --out data/experiments/new-audit-run
    .\\.venv\\Scripts\\python.exe validation/audit/regression.py --out data/experiments/new-audit-regression --workers 4
    .\\.venv\\Scripts\\python.exe validation/audit/experiments.py --out data/experiments/new-audit-probes --workers 4

감사 결과 생성 경로는 data/experiments/audit-20261030/regression 및 probes다. regression은 baseline-v4/audit-fix-v1/audit-fix-v1-replay를 각각 둔다. 기존 원본 재현·통계 비교는 기존 validate의 함수를 재사용한 것이며, 기존 validation/results.json이나 그림을 덮는 CLI를 실행한 것은 아니다.

## 10. 남은 문제와 활용 판정

**수정본도 LAYER7 추천 성과의 주 평가 도구로 채택할 실증 근거는 부족하다.** 기능·회귀·콜드스타트·가정에 따른 메커니즘 탐색에는 사용할 수 있다. 실제 매출 개선율이나 보편적인 충돌 회피 효과를 주장하는 데 쓰지 않는다.

1. 한국 수집품 이용자의 요일/시간별 활동·알림 확인·세션·대체재 수량 수요를 관측해야 한다. 외국 플랫폼 곡선과 B2B 구조모형 결과는 한국 C2C의 실측 파라미터가 아니다.
2. 동시 마감의 직접 혼잡, 대체재 보유, 검색 노출, 예산 제약을 경험적으로 구분할 자료가 부족하다. 이번 2×2 통제와 전체 시장 총효과는 목적이 다르다.
3. 10분 재입찰 예외, 보유 대체재 회피, 알림·재방문의 시간 가용성·주의력 가중은 유지한 ASSUMED 규칙이다. 향후 변경은 학술 근거·새 가정·부작용과 별도 버전의 비교가 필요하다.
4. 세계 단위 N=12도 충분히 큰 표본은 아니다. 구간이 0을 포함한다는 것은 효과가 없다는 증명이 아니다. 반복 경매 수를 늘리는 것만으로 독립 세계 수가 늘지 않는다.
5. 가격 분산과 기존 통계 불일치, 낙찰분만 있는 원자료의 선택 편향, eBay식 프록시와 실제 LAYER7 입찰 규칙의 차이가 남는다.
6. 동결 모형은 24–72시간을 사용한다. 실제 LAYER7 명세의 1시간–7일 전체와 예약 시작은 이 감사의 검증 범위가 아니다. 기간을 확장하면 새 기준선에서 다시 검증해야 한다.
7. 선택적 soft-close 전체 재생 검사와 모든 극단 파라미터/모든 RNG 키의 수학적 성질은 이번 범위에 포함되지 않는다. 확인한 통제를 전체 보장으로 확대하지 않는다.

권하는 다음 단계는 충돌 회피의 성능을 끌어올리는 보정이 아니라, 실제 서비스에 등록/공개·예정 종료·추천/선택·방문/입찰의 시점 정보를 남기고 어떤 메커니즘을 식별할 수 있는지 먼저 설계하는 것이다. 새 수집·서비스 구현은 이번에 수행하지 않았다.

참고: [Bimpikis 저자판](https://web.stanford.edu/~kostasb/papers/managing_market_thickness.pdf)은 B2B 참여·잠식의 구조모형 근거이며 분 단위 C2C 충돌 계수의 실측 근거가 아니다. 대응 표본 구간은 [SciPy 문서](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_rel.html), 클러스터 공분산은 [statsmodels 공식 문서](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html)를 참고했다.
'''
    (HERE / 'REPORT.md').write_text(text, encoding='utf-8')
    changes = []
    for key, record in regression['datasets'].items():
        for metric, value in record['baseline_moments'].items():
            after = record['corrected_moments'][metric]
            if isinstance(value, (int, float)):
                changes.append({'dataset': key, 'metric': metric, 'baseline': value, 'corrected': after, 'delta': after-value})
            elif metric == 'log_price_sd_by_category':
                for category, number in value.items():
                    changes.append({'dataset': key, 'metric': metric+'/'+category, 'baseline': number,
                                    'corrected': after[category], 'delta': after[category]-number
                                    if number is not None and after[category] is not None else None})
    pd.DataFrame(changes).to_csv(HERE / 'calibration_changes.csv', index=False)
    codes = sorted((ROOT / 'src/audit').glob('*.py')) + sorted(HERE.glob('*.py'))
    data_root = ROOT / 'data/experiments/audit-20261030/regression'
    data_files = sorted(data_root.glob('scenario_*/seed_*/audit-fix-v1/**/*.csv'))
    expected = json.loads((ROOT / 'BASELINE_v4.json').read_text(encoding='utf-8'))
    protected_ok = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in expected['defining_files'].items())
    protected_ok &= all(hashlib.sha256((ROOT / 'data/synthetic' / name).read_bytes()).hexdigest() == sha for name, sha in expected['data_csv'].items())
    assert protected_ok and len(data_files) == 198
    manifest = {'label': 'audit-fix-v1', 'parent_label': 'baseline-v4', 'parent_commit': 'cc32802',
                'parent_manifest_sha256': hashlib.sha256((ROOT / 'BASELINE_v4.json').read_bytes()).hexdigest(),
                'frozen_parent_unchanged': bool(protected_ok),
                'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in codes},
                'corrected_csv_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in data_files},
                'parameter_changes': {}, 'assumed_rules_changed': [], 'empirical_recalibration': False}
    (ROOT / 'AUDIT_FIX_v1.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # Preserve the original README body and original line endings byte-for-byte.
    path = ROOT / 'README.md'
    raw = path.read_bytes()
    if b'validation/audit/REPORT.md' not in raw:
        nl = b'\r\n' if b'\r\n' in raw else b'\n'
        head, tail = raw.split(nl, 1)
        note = ('\n> 2026-10-30 독립 감사: 아래 기존 설명은 동결된 baseline-v4 기준이다. '
                '확인된 오류를 수정한 선택 엔진 audit-fix-v1과 검증 결과는 '
                '[감사 보고서](validation/audit/REPORT.md), [실행 안내](validation/audit/README.md)를 참고한다. '
                '기존 코드·설정·합성 데이터는 보존했다.\n').encode('utf-8').replace(b'\n', nl)
        path.write_bytes(head + nl + note + tail)
    if args.outputs:
        out = args.outputs.resolve()
        out.mkdir(parents=True, exist_ok=True)
        for file in ['REPORT.md', 'diagnosis_before_fixes.md', 'diagnosis_addendum.md', 'regression_results.json',
                     'experiment_results.json', 'extended_structure_results.json', 'calibration_changes.csv', 'results_before.json', 'results_after.json']:
            shutil.copy2(HERE / file, out / file)
        shutil.copy2(ROOT / 'AUDIT_FIX_v1.json', out / 'AUDIT_FIX_v1.json')
        for file in (ROOT / 'data/experiments/audit-20261030/probes').glob('*.csv'):
            shutil.copy2(file, out / file.name)
        files = codes + [ROOT / 'README.md', ROOT / 'BASELINE_v4.json', ROOT / 'AUDIT_FIX_v1.json']
        files += sorted(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.md', '.json', '.csv'))
        with zipfile.ZipFile(out / 'audit-code-and-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(set(files)):
                archive.write(file, file.relative_to(ROOT).as_posix())
    print(json.dumps({'baseline_protected': bool(protected_ok), 'baseline_bids': n_bids,
                      'corrected_bids': fixed_bids, 'activity_bad_before': bad_bids,
                      'corrected_csv_manifest_count': len(data_files), 'report': str(HERE / 'REPORT.md')}, indent=2))


if __name__ == '__main__':
    main()
