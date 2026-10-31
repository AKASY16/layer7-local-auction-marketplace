"""Build the reviewable Korean handoff from fixed results; no simulator imports."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_followup/results'
DEST=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\v2b1-recheck-20261031')

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    data=json.loads((RES/'evaluation-1.json').read_text(encoding='utf-8'))
    bench=json.loads((RES/'benchmark.json').read_text(encoding='utf-8'))
    preservation=json.loads((RES/'preservation.json').read_text(encoding='utf-8'))
    aggregate=pd.read_csv(RES/'aggregate_metrics.csv')
    flow=pd.read_csv(RES/'followthrough_by_case.csv')
    detail=pd.read_csv(RES/'followthrough_details.csv')
    gaps=pd.read_csv(RES/'paired_gap_changes.csv')
    scenario=pd.read_csv(RES/'metric_seed_differences.csv')
    names={'legacy':'legacy (audit-fix-v1)','v1':'known-surplus-v1','v2b1':'V2-B.1'}
    mt=[]
    for metric,label,fmt in [('n_bids','입찰 수','.1f'),('bidders_mean_pos','양의 입찰 경매당 입찰자','.3f'),
        ('bids_per_pair','구매자–경매당 입찰','.3f'),('repeat_pair_share','재입찰 쌍 비율','.2%'),
        ('sold_rate','판매율','.2%'),('multi_auction_bidder_share','복수 경매 입찰자 비율','.2%'),
        ('switch_rate','연속 입찰 중 경매 이동','.2%'),('open_switch_share','이동 중 직전 경매가 열린 비율','.2%'),
        ('log_price_sd_figure','피규어 낙찰가 log SD','.3f'),
        ('log_price_sd_limited_goods','한정판 낙찰가 log SD','.3f'),
        ('log_price_sd_retro_game','레트로 낙찰가 log SD','.3f')]:
        mt.append([label]+[format(float(aggregate[aggregate.scope.eq('A_to_E')&aggregate.variant.eq(v)].iloc[0][metric]),fmt) for v in names])
    metric_table=table(['지표 (A–E 15개 World 평균)']+list(names.values()),mt)
    flow_table_rows=[]
    totals={}
    for variant in ('v1','v2b1'):
        r=flow[flow.variant.eq(variant)].sum(numeric_only=True);totals[variant]=r
        n=r.unique_buyer_targets
        flow_table_rows.append([names[variant],int(r.deferral_events),int(n)]+
            [f'{int(r[k]):,} ({r[k]/n:.2%})' for k in ('target_revisited','target_bid','target_purchased')])
    flow_table=table(['모형','보류 이벤트','첫 구매자–대안 쌍','재조회','이후 입찰','최종 낙찰'],flow_table_rows)
    reasons=detail.groupby('variant').first_revisit_reason.value_counts().unstack(0).fillna(0)
    reasons_table=table(['첫 재조회 결과','V2-B','V2-B.1'],[[k,int(r.get('v1',0)),int(r.get('v2b1',0))] for k,r in reasons.iterrows()])
    scenarios=[]
    for s in 'ABCDEF':
        q=scenario[scenario.scenario.eq(s)&scenario.baseline.eq('v1')].set_index('metric')
        r=q.loc['n_bids']
        scenarios.append([s,f"{r.mean_delta:+.1f}",f"[{r.ci95_low:.1f}, {r.ci95_high:.1f}]",
            f"{q.loc['repeat_pair_share','mean_delta']*100:+.3f} pp",f"{q.loc['sold_rate','mean_delta']*100:+.3f} pp"])
    scenario_table=table(['시나리오','입찰 수 Δ','시드 t 95% 구간','재입찰 쌍 Δ','판매율 Δ'],scenarios)
    gaprows=[]
    for metric,g in gaps[gaps.scenario.ne('F')&gaps.baseline.eq('v1')].groupby('metric'):
        d=g.delta_abs_gap
        gaprows.append([metric,f'{d.mean():+.6f}',int(d.lt(0).sum()),int(d.gt(0).sum()),int(d.eq(0).sum())])
    gap_table=table(['외부 참조 절대 차이 (B.1 − V2-B)','평균 Δ','감소','증가','동일'],gaprows)
    absolute_rows=[]
    for label,metric,target,fmt in [('J&S 혼합 입찰/쌍','bids_per_pair',2.0618489583333335,'.3f'),
        ('J&S 혼합 재입찰 쌍','repeat_pair_share',.4244791666666667,'.2%'),
        ('B04 입찰자','b04_bidders_mean',2.4671201814058956,'.3f'),
        ('B04 판매율','b04_sold_rate',.6031746031746031,'.2%'),
        ('B04 낙찰가 log SD','b04_sold_log_price_sd',.5625736515275936,'.3f')]:
        absolute_rows.append([label,format(target,fmt)]+[format(float(aggregate[aggregate.scope.eq('A_to_E')&aggregate.variant.eq(v)].iloc[0][metric]),fmt) for v in names])
    absolute_table=table(['참조 (전이 진단)','실측']+list(names.values()),absolute_rows)
    w=pd.read_csv(RES/'window_metrics.csv');w=w[w.scenario.ne('F')]
    windowrows=[]
    for window in ('near72','terminal24'):
        for mode in names:
            g=w[w.window.eq(window)&w.variant.eq(mode)]
            windowrows.append([window,names[mode],int(g.n_positive.sum()),f'{g.bidders_mean_pos.mean():.3f}',
                f'{g.bids_per_pair.mean():.3f}',f'{g.repeat_pair_share.mean():.2%}'])
    window_table=table(['보조 설계','모형','양의 입찰 경매 총수','경매당 입찰자','입찰/쌍','재입찰 쌍'],windowrows)
    b=bench['medians'];mem=bench['Python_allocation_peak_small_world_bytes']
    cost_table=table(['모형','초 (3회 중앙값)','소규모 Python 할당 peak'],
        [[names[v],f'{b[k]:.3f}',f'{mem[k]:,} B'] for v,k in [('legacy','legacy'),('v1','known-surplus-v1'),('v2b1','known-surplus-followup-v1')]])
    text='''# V2-B.1 구매자 대안 선택·이동: 원인 감사·구현·검증·판정

2026-10-31 / 로컬 브랜치 `codex/v2b1-recheck-20261031`

## 판정

**수정 필요, 정식 채택 보류. 실험 모드는 보존한다. 기본 모형은 legacy 그대로다.**

보류한 대안을 실제로 다시 확인하는 연결은 개선됐다. 그러나 이는 연결 규칙이
작동했다는 증거이며, 현실의 구매자를 더 잘 설명한다는 독립적인 실증 증거는 아니다.
V2-B 대비 재입찰 일부가 회복됐지만 기존 legacy보다 실측 행동을 일관되게 잘
재현하지 못한다. 가격 분산과 시장별 효과도 혼재한다. 실패한 필수 조건은 없다.
불변조건 실패로 폐기할 모형은 아니지만, 그대로 기본 엔진에 채택할 근거도 없다.
V2-C, 추천 정책 최적화, 목표 수치에 맞춘 보정, 푸시·PR을 수행하지 않았다.

## 1. 보존과 비교 범위

시작 시 프로젝트의 기존 파일 **2,735개**를 크기·SHA256으로 기록했다.
종료 시 삭제 0, 내용 변경 0을 확인했다. `.git`, `.venv`, `__pycache__`는 해시
검사에서 제외했다. 모든 Python 실행에 `-B`를 사용했다. 원래 미커밋 파일도
보존 대상에 포함했다. `README.md` 등에 표시되는 기존 변경은 이번 수정이 아니다.

`baseline-v4`, `audit-fix-v1`, V2-A, V2-B 소스·설정·합성 데이터·기존 검증 산출물을
모두 보존했다. 추가 경로는 `src/v2_followup/`, `validation/v2_followup/`,
`data/experiments/v2b1-20261031/` 세 곳이다. 보존 확인은 [preservation.json](/experiments/auction-simulator/validation/v2_followup/results/preservation.json).

비교는 A–F × seed 1/2/3의 기존 18개 World, 같은 seller_default, hard-close다.
A–E는 500개 경매씩인 15개 실행을 같은 비중으로 요약하고 소규모 F는 분리했다.
같은 시드의 다른 시나리오나 반복 입찰을 독립 실측 표본으로 간주하지 않았다.
legacy는 동결 audit-fix-v1을 뜻하며 baseline-v4 자체로 오인하면 안 된다.

## 2. 원인 감사: 확인된 사실과 추정

먼저 V2-B만 수동 관찰하는 subclass로 18개를 재실행했다. 이전 V2-B의 각 11 CSV,
ordered RNG fingerprint, ordered heap fingerprint와 **18/18 완전히 일치**했다.
감사 때문에 실제 구매자에게 새 정보·WTP·방문을 주지 않았다.

### 보류 원인 분리

- `choice_better_known_alternative` 68,655회: 알려진 다른 경매가 더 나아 현재 입찰 보류.
- `choice_no_positive_surplus` 758회: 0 이하 잉여이므로 구매하지 않음.
- `budget` 188,893회, `price_above_wtp` 158,729회: 기존 가격·자금 불가 경로.
- `deferred` 145,178회: 원래 모델의 조기 입찰 유예/watch 행동. 대안 보류와 다르다.
- 알림/재방문의 unavailable, 스나이핑 계획/실패는 별도 사유다.

**정보 노후화는 구매자가 아는 보류 사유로 기록하면 안 된다.** 구매자는 실제
가격이 바뀌었는지 모르므로, 정보 노후화 여부는 감사자가 사후 대조한 별도 분류다.
예산 부족과 정보 불일치 등은 동시에 나타날 수 있어 서로 배타적인 원인 비율로
합산하지 않았다. 관련 원자료는 [cause-audit](/experiments/auction-simulator/validation/v2_followup/results/cause-audit/summary.json).

### 이후 실제 행동

반복 보류를 중복 독립 표본으로 세지 않고, **World 내 첫 구매자–대안 경매 쌍**을
사용했다. 첫 보류 직후의 이벤트 순서부터 `min(당시 기지 종료시각, 구매자 활동 종료)`
직전까지 추적했다. 같은 시각/방문 안에서 뒤에 일어난 조회도 인정했다. 낙찰은
그 창 안에 실제 입찰하고 최종 winner가 된 경우이며 정산은 활동 종료 뒤여도 인정한다.

{{FLOW}}

모형마다 보류 대상 집합과 최초 시점이 달라 분모도 다르다. 이 표의 전환율은
각 모형 내 조건부 기술통계이며, 같은 사람·대상·시점에 대한 인과적 처리 효과가
아니다. 약 +9.8pp의 재조회 증가 자체를 현실성의 외부 검증으로 해석하지 않았다.

V2-B에서 재조회도 입찰도 없는 15,843쌍은 다음처럼 나뉜다.

- 4,744쌍: 남은 창 안에 실제 성립한 이후 방문/조회 기회가 없음. 이를 단순히
  '관심을 잃었다'고 해석할 수 없다. 활동 종료·방문 미발생·가용성 등과 구분 불가능하다.
- 11,099쌍: 다른 조회는 있었으나 표적은 다시 보지 않음. 그중 **4,685쌍**만
  다음 일반 방문 기회가 있었다. 나머지에는 같은 방문의 남은 조회나 다른 종류의
  방문만 있는 경우가 포함된다. 따라서 새 방문을 강제로 만들면 안 된다.
- 19,599쌍: 표적은 재조회했지만 창 안의 표적 입찰이 끝내 없음.

첫 재조회 결과를 실제 CSV의 visit_id·구매자·경매로 연결한 분류는 다음과 같다.
이 후속 사유 분석의 마감 창 판정은 CSV의 초 단위 시각을 사용한다. 주 전환율
표는 full-precision 엔진 이벤트 순서로 집계했다.

{{REASONS}}

`sniper_already_planned`는 이전 계획/불가 기록과 sniper 스타일을 확인한 뒤
분류했다. 원 코드가 이미 계획된 스나이핑에는 새 결정 로그를 쓰지 않는 경로다.
재조회를 안 한 것과 입찰을 안 한 것은 다른 문제다. 특히 첫 재조회 예산 부족
8,825건에는 다른 구매/commitment 변화도 섞일 수 있어 전부 오래된 가격 탓으로
돌리지 않았다. 조기 유예와 스나이핑을 즉시 입찰로 바꾸는 것은 이번 범위가 아니다.

### 오래된 가격 정보의 기여: 무엇까지 확인됐나

V2-B 대안 보류 68,655회에서 선택 대상의 실제 현재 ask가 마지막 관측 ask와
달랐던 비율은 **37.95%**다. 그 대안의 실제 ask가 현재 가용 예산을 넘은 경우는
11.14%, 개인 WTP 이상이 된 경우는 2.26%다. 보류 대상 quote 나이는 평균
494.89분, 중앙값 71.83분이다. 나이만 오래됐다고 실제 가격이 바뀐 것은 아니다.

**이미 알고 있던 경매들만** 감사 시점 현재 정보로 대조했을 때 현재 경매를
입찰 허용으로 바꿀 보류는 **12.04%**였다. 이는 같은 결정 시점의 정보 불일치
진단이다. 이 정보는 실행 엔진에 입력하지 않았다. 현재 가격을 아는 가상 구매자
모형을 채택하거나 미래 가격을 제공한 실험도 아니다. 전체 시장의 입찰 수·가격·
실측 오차 중 '정확히 몇 %가 노후화 때문'이라는 인과적 기여율은 식별하지 못했다.
입찰 허용 뒤에도 조기 유예·스나이핑·예산 변화가 있고 경매 간 간섭도 발생한다.

별도 통제 테스트에서는 실제 가격만 상승시키고 구매자 기지 quote를 그대로 두면
V2-B가 계속 보류하고, 실제 재조회로 quote를 갱신한 뒤에는 원래 경매 입찰이
가능해지는 경로를 확인했다. 이는 국소 메커니즘 증명이지 시장 전체의 손실 추정은 아니다.

이전 V2-B의 quote TTL 민감도(60분/360분)에서 입찰 수가 5,206.4→5,814.4/
5,620.1로 회복됐던 것은 참고 증거다. 하지만 TTL은 대안 자체를 비교에서 제거하는
다른 행동 가정이므로 신선한 가격 정보의 순수 인과 효과라고 해석하지 않았다.

**확인된 설계 한계:** 기존 V2-B에는 보류한 대안을 기억해 후속 조회로 연결하는
상태/경로가 없다. 이는 코드의 의도와 다른 오류로 확정한 것이 아니라, V1의 설계
한계다. '구매자는 보류 후 반드시 이동한다'는 실측 사실까지 확인한 것은 아니다.
이에 따라 연결 모형 하나를 ASSUMED 실험으로만 구현했다.

## 3. 단일 개선 모형과 정보 경계

구현 전 [PRE_IMPLEMENTATION.md](/experiments/auction-simulator/validation/v2_followup/PRE_IMPLEMENTATION.md)에 설계·평가를 기록했다.
기존 V2-B 비교식 자체는 유지한다.

`U_i = 개인 WTP_i − 마지막 관측 ask_i`

`S_ij = 상품 유사도_ij × (개인 WTP_j − 마지막 관측 ask_j)`

기지 종료 시각이 남아 있고 자기 선두/낙찰 보유 대상이 아니며 현재 예산으로
가능한, 실제 발견한 대안만 비교한다. 최대 S가 현재 U보다 좋으면 기존과 같이
보류한다. 동점에는 기존의 기지 종료시각·ID 순서를 사용한다. 현재 잉여가 0
이하면 구매하지 않는다. 이 근시안적 ask 잉여는 기대 최종 효용과 같지 않다.

새로 저장하는 상태는 `의향[구매자] = (최신 보류 대상, 생성 visit_id)` 하나다.

1. 기존 일반 방문이 rate·시간대·활동 조건을 통과해야 한다. 새 후보/RETURN을
   의향 때문에 만들지 않는다.
2. **다음의 다른 일반 방문** 첫 기존 조회 슬롯에서 의향 대상을 재확인한다.
   슬롯을 대체하므로 K를 늘리지 않는다. 동일 방문 내 같은 경매 중복은 생략한다.
3. 요청 전에는 자기 기지 정보와 구매/예산 상태만 확인한다. 기지 만료·자기 보유·
   기지 ask도 감당 못하는 상태면 취소한다. 요청한 페이지의 서버 가용성 검사만
   실제 start/end/closed를 읽는다. 여기서 다른 경매 가격을 선택식에 주지 않는다.
4. 실제 페이지를 본 뒤에만 ask/종료 시각을 갱신하고 동일 비교식·입찰 스타일을
   실행한다. 새 의향은 다음 방문까지 기다려 같은 방문 내 왕복 조회를 막는다.
5. 기존 알림·outbid·watch·snipe의 대상은 바꾸지 않는다. 자연스럽게 표적을 보면
   의향은 소거된다. 실제 재조회 뒤 기존 watch/snipe 규칙이 예약할 수 있는 후속
   이벤트는 정상적인 행동 경로 차이다.

WTP·예산·proxy 입찰·낙찰 정산·참여 N·경쟁 공급 M·종료 근접 T의 공식은 변경하지
않았다. 종료 충돌 벌점, 미래/미관측 가격, WTP 상승, 성과용 계수는 없다.

**새 조정 가능한 연속 계수는 0개**다. 다만 '가장 최근 의향 하나', '다음 일반
방문 첫 슬롯 우선', '한 방문 한 재확인·중복 제거'는 새 **이산 설계 가정**이다.
모두 ASSUMED이고, A-01에서 추정한 법칙이 아니다. 기존 가격 기억의 TTL은 추가하지
않았다. 이번에는 요청대로 모형 하나만 구현해 다른 슬롯 배분 대안의 민감도는
검증하지 않았다. 따라서 파라미터가 없다고 행동 가정에 강건하다는 뜻은 아니다.

런타임은 [simulator.py](/experiments/auction-simulator/src/v2_followup/simulator.py).
감사의 전지적 대조는 validation 디렉터리에만 있으며 런타임이 이를 import하지 않는다.

## 4. 검증 결과

- 신규 단위/통제 테스트 **12/12**, 기존 V2-B 테스트 **13/13** 통과.
- 전체 비교 **18 World × 3모드 = 54개 새 데이터셋**, 구조 검증 54/54 통과.
- legacy·known-surplus-v1 각 18개 실행의 11 CSV가 기존 결과와 일치(총 396파일 비교).
- V2-B.1 18/18에서 같은 World·시드·정책 반복 실행의 전체 상태 해시, WTP 캐시,
  예산, 로그, ordered RNG, heap, CSV가 일치했다. 다른 모형과 이벤트 수가 다른 것은
  정상이며 서로 같은 RNG 소비를 강제하지 않았다.
- 감사 ON/OFF B.1의 11 CSV도 18/18 일치, 소규모 통제 테스트에서 ordered RNG/
  heap도 일치. 감사자가 보는 현재 진실이 행동에 유입되지 않았다.
- 입찰 직전 ask≤입찰한도≤개인 WTP/예산 headroom, 구매자 활동 구간, 경매 시간,
  실제 조회한 쌍의 WTP만 생성, 낙찰 정산·최종 잔액·commitment 불변조건 통과.
- 기존 일반 방문 기회가 모든 모형에서 정확히 같고, B.1의 해당 방문 조회 수가
  원 슬롯 상한을 넘지 않았다. 동일 방문 중복 조회와 같은 방문 연쇄 재조회도 방지했다.
- 부모 visit/run/입찰/정산 함수를 그대로 상속하는 테스트, 미관측 대안 가격을
  접근하면 실패하는 통제 테스트, 미래 quote를 거부하는 기존 테스트를 통과했다.

V2-B 원인 감사 18회와 본 비교·재현·감사 총 90회 외에 단위·성능 실행을 수행했다.
세부는 [evaluation-1.json](/experiments/auction-simulator/validation/v2_followup/results/evaluation-1.json),
[신규 테스트 로그](/experiments/auction-simulator/validation/v2_followup/results/unit-tests.txt),
[기존 테스트 로그](/experiments/auction-simulator/validation/v2_followup/results/parent-unit-tests.txt).

## 5. 행동·가격·실측 적합도

### 동일 World 비교

{{METRICS}}

V2-B 대비 입찰 수 +83.3회/World(+1.60%)지만 legacy 대비 −810.5회(−13.29%)다.
V2-B에서 줄었던 입찰의 약 9.3%만 회복했다. 이것을 '노후화에 기인한 손실의
9.3% 회복'이라고 바꿔 말할 수는 없다. 평균 판매율은 V2-B 대비 +0.147pp다.
가격 분산은 피규어 소폭 감소, 한정판/레트로는 소폭 증가로 혼재한다.

재조회 성공 20,739회 중 원래 표본 슬롯의 경매가 달라진 경우는 16,358회다.
중복 슬롯 3,859개를 생략했다. A–E의 구매자–경매 고유 조회 쌍은 평균
29,115.0→28,737.3(약 −1.30%)로 줄었다. 기존 의향에 주의를 쓰는 만큼 새로운
발견이 줄어드는 비용이다. 구매 전환율 증가와 함께 반드시 보고해야 한다.

새 보류 대상의 가격 불일치는 33.01%, 현재 정보 대조 시 입찰 허용으로 바뀌는
보류는 11.10%로 남았다. quote 나이 중앙값은 0분, 평균은 418.33분이다. 일부 즉시
관측을 늘렸지만 다른 대안들의 가격 기억 문제와 스타일·예산 제약을 해결하지는 못했다.

### 시나리오·불확실성

아래 Δ는 B.1−V2-B, 각 시나리오 3개 독립 시드의 paired 차이다. t 구간은 시뮬레이션
시드 변동만 나타내며 실측 표본 불확실성, 모형 오류, 다중 비교를 포함하지 않는다.

{{SCENARIOS}}

A–E 입찰 수는 14/15개 실행에서 증가했으므로 하나의 시나리오에서만 작동한 것은
아니다. 하지만 B에서는 평균 판매율 감소, E에서는 평균 재입찰 쌍 비율 감소다.
입찰 수 Δ의 시나리오별 구간은 모두 0을 포함한다. n=3에서 일반적인 우월성을
확정할 수 없다. F는 V2-B 대비 입찰 +4회, 판매율 변화 0, 재입찰 쌍 +0.067pp로 작다.
F를 A–E와 동일한 시장 크기의 추가 표본으로 합치지 않았다.

### 실측 참조의 관측 단위와 결과

- **A-01:** 유효 선정 이력 138경매·804입찰자·2,348입찰. 복수 경매 입찰자
  22.01%, 이동 25.58%, 이동 시 직전 경매가 열려 있는 비율 62.28%는 참고 기술통계다.
  한 상품/선정 이력/다른 기간의 자료를 여러 카테고리 전체 시장과 동일 표본으로
  취급하지 않았다. 이동 정의는 앞선 A-01 분석과 같은 시간·경매ID 정렬이며 같은
  시각 순서의 한계도 유지된다. B.1의 열린 경매 간 이동 비율은 V2-B보다 조금
  증가했지만 legacy보다 낮다. **22% 등에 맞춘 오차 점수/튜닝은 하지 않았다.**
- **B-04:** B-03과 중복인 한 자료 계열이다. 독립 검증 두 번으로 세지 않는다.
  신규/배송비 known≤10/비reserve/auction 조건의 unique listing 중 1–3일은
  441경매·266낙찰, 평균 입찰자 2.467, 판매율 60.32%, log 낙찰가 SD 0.563이다.
  모델의 new·24–72h 범위만 대조한다. DVD와 수집품·공급·시작가·기간 구성 차이로
  외적 전이 진단이다. USD/KRW 평균 가격 차이나 마스킹 ID의 개인 이동을 평가하지
  않았다. B.1은 입찰자 차이가 평균 증가, 가격 SD 차이는 거의 변하지 않았다.
- **J&S:** 기존에 이미 알려진 30% auction CRC holdout. 정확72h는 35경매·234쌍,
  평균 입찰자 6.686, 입찰/쌍 1.996, 재입찰 쌍 44.87%다. 모델의 정확72h 양의
  입찰 경매는 A–E 전체에 **3개**뿐이므로 전체 정확72h 성능 점수는 계속 금지했다.
  3/5/7일 pooled holdout의 입찰/쌍 2.06185, 재입찰 쌍 42.45%는 기간 혼합 전이
  진단만 허용했다. B.1은 V2-B 대비 이 두 참조 차이를 대체로 줄였지만 legacy보다
  나쁜 실행이 각각 10/15, 13/15다. fresh blind holdout이라는 주장도 하지 않았다.
- **상품별 가격 proxy:** figure 0.846, limited 0.894, retro 1.367은 이전부터
  사용한 다른 상품 전이값이다. intrinsic WTP의 실측 정답으로 사용하지 않는다.
  TCG의 가정 SD는 실측 참조로 점수화하지 않았다.

아래는 A–E 15개 실행에서 **V2-B 대비** 참조 절대 차이의 변화다. 음수는 차이
감소다. 서로 다른 단위/외적 참조를 하나의 점수로 합산하지 않았다.

먼저 참조와의 절대 수준을 같이 표시한다. 기간·상품·시장 차이가 남는 전이 비교다.

{{ABSOLUTE}}

{{GAPS}}

한정판은 9/15에서 차이가 작아졌어도 나머지의 증가 폭 때문에 평균은 악화됐다.
유리한 실행 수나 특정 지표만 골라 성공으로 판정하지 않았다. 실제 KRW 낙찰가의
P10/P25/P50/P75/P90·평균·log SD를 전 시나리오별로 보존했고
[분포표](/experiments/auction-simulator/validation/v2_followup/results/sold_price_quantiles.csv)와
[ECDF 그림](/experiments/auction-simulator/validation/v2_followup/results/sold_price_ecdf.png)을 제공한다.
그림은 A–E 낙찰들을 모은 기술통계이며 iid 검정이나 다른 통화 가격 수준 비교가 아니다.

## 6. J&S 72시간 표본 부족: 별도 평가 설계

기존 World나 종료 정책을 바꾸지 않고, 구현 전에 두 보조 설계를 고정했다.

1. **60–72h 전체 경매:** 실제72h와 근접한 구간의 양의 입찰 경매. 범위는 결과를
   보고 고른 것이 아니다. 표본을 늘리지만 기간 일치가 근사적이다.
2. **마지막24h 공통 관측 창:** 창 안에 입찰이 있는 경매/쌍만 비교. 기존 World
   기간 24–36/36–48/48–60/60–72h로 분리한 결과도 모두 저장했다. J&S 참조는
   34경매·147쌍, 입찰자 4.324, 입찰/쌍 1.966, 재입찰 쌍 46.94%다. 경매 전체
   입찰자/재입찰과 다른 추정 대상이며, 앞선 기간의 경로 효과도 남는다.

{{WINDOWS}}

양의 입찰 경매 총수는 모든 실행의 합이며, 나머지 값은 World별 조건부 지표의
평균이다. 15개 World나 그 안의 반복 입찰을 15개 이상의 독립 실증 표본으로
간주한 신뢰구간은 제시하지 않았다.

근접72h에서는 입찰/쌍이 1.963→1.988로 참조 1.996에 가까워지고 입찰자 수도
6.859→6.851로 조금 가까워진다. 그러나 재입찰 쌍 29.85%는 참조 44.87%에 크게
못 미친다. 마지막24h도 재입찰은 29.36%로 참조 46.94%보다 낮고 legacy 30.92%보다
낮다. 정의를 맞춘 단위/창에서도 모든 행동 지표가 함께 개선되지는 않는다.

**해결 범위:** 분석 가능한 보조 표본은 확보했으나 '정확72h 경매 전체 결과'의
표본 부족 자체를 해결했다고 주장하지 않는다. 그 주장은 추가 실측의 기간별 자료
또는 별도 사전 고정한72h 검증 시장이 필요하다. 이번에는 그 시장을 만들거나
기존 종료 정책을 바꿔 결과를 맞추지 않았다. 세부는
[window_metrics.csv](/experiments/auction-simulator/validation/v2_followup/results/window_metrics.csv).

## 7. 성능 비용

같은 PC·A seed1(1500구매자/500경매/30일), World 생성 이후 init+run만 3회씩
순서를 회전해 측정했다. 검증·CSV 출력·전지적 감사·전체 observer는 제외했다.

{{COST}}

B.1은 V2-B 대비 시간 **+4.4%**, legacy 대비 **+26.4%**다. 메모리는 별도의
200구매자/60경매/10일에서 World 생성 이후 Python tracemalloc peak를 측정했고
V2-B 대비 약 **+1.8%**다. 전체 시장의 process RSS나 GPU VRAM 수치가 아니다.
주 진단은 counters와 구매자별 마지막 의향/방문 상태뿐이며 전체 선택 trace를
쌓지 않는다. 감사 CSV는 검증 실행에만 기록한다. [benchmark.json](/experiments/auction-simulator/validation/v2_followup/results/benchmark.json).

## 8. 변경 파일과 재실행

| 추가 파일/경로 | 이유 |
| --- | --- |
| `src/v2_followup/__init__.py`, `simulator.py` | 독립 모드·세 모형 factory·기존 슬롯 기반 의향 재확인 |
| `src/v2_followup/run.py`, `README.md` | 새 경로 전용 CLI, 기본 legacy, 가정·실행 안내 |
| `validation/v2_followup/cause_audit.py` | 원형을 바꾸지 않는 quote/후속 행동 감사 |
| `PRE_IMPLEMENTATION.md` | 구현 전 근거·수식·가정·평가 범위 고정 |
| `test_followup.py`, `evaluate_followup.py` | 통제·불변조건·회귀·동일 시드 반복·조회 상한 검증 |
| `window_metrics.py` | 수정 없는 J&S 보조 창/기간 설계 |
| `analyze_followup.py`, `distributions.py` | 전체 개선/악화·시드 차이·전환 사유·가격 분포 |
| `benchmark.py`, `build_report.py` | 재현 가능한 비용 측정·보고서 생성 |
| `results/`, `REPORT.md`, `V2_B_1_v1.json` | 감사/54개 결과 요약·테스트·판정·해시 |
| `data/experiments/v2b1-20261031/evaluation-1/` | 54개 새 데이터셋과 B.1 감사 이벤트 |

기존 파일 수정/삭제는 없다. Python 함수 API/CLI로 세 모형을 전환할 수 있다.
[실행 안내](/experiments/auction-simulator/src/v2_followup/README.md).
테스트는 프로젝트 루트에서 `python -B -X utf8 validation/v2_followup/test_followup.py`.
전체 평가/원인 감사는 재실행 시 **새 출력 디렉터리 이름으로** 실행해야 하며 기존
경로가 있으면 거부한다. 보고서/분석은 이 새 실험의 파생 산출물만 갱신할 수 있다.

## 9. 남은 문제와 다음 판단의 조건

1. 실제 사람이 대안을 기억한 후 언제/어떤 방문 슬롯을 써서 다시 확인하는지
   자료가 없다. A-01의 입찰 이동만으로 페이지 재확인 규칙을 추정할 수 없다.
2. '현재 ask 잉여'는 최종 가격 불확실성을 무시한다. B.1은 이 가정을 고치지 않았다.
   quote 재확인으로도 남은 11.10%의 현재 정보 판단 불일치는 미해결이다.
3. 예산·조기 유예·스나이핑은 독립적인 미전환 원인이며, 표적 재조회만으로 해결되지 않는다.
4. 새 발견 감소와 오래된 의향에 대한 주의 편향 비용이 있다. 한 슬롯 우선이라는
   이산 가정의 다른 형태까지 검증하지 않았으므로 결과를 일반화할 수 없다.
5. 3개 시드와 다른 시장의 이미 알려진 참조로는 독립적 외적 타당성을 증명하기 어렵다.
   실제 LAYER7의 발견→보류→조회→입찰 로그, 조건이 맞는 경매/상품/기간 자료가 필요하다.

따라서 이번 구현은 **수정할 근거가 있는 탐색 실험으로 유지하되 채택은 보류**한다.
후속 판단은 관측 가능한 행동 경로의 재현성과 참조 오차의 일관된 개선을 기준으로
해야 한다. 종료 추천 수익이 좋아진다는 이유로 수치나 규칙을 조절하지 않는다.
'''
    for k,v in dict(FLOW=flow_table,REASONS=reasons_table,METRICS=metric_table,SCENARIOS=scenario_table,
        GAPS=gap_table,ABSOLUTE=absolute_table,WINDOWS=window_table,COST=cost_table).items():text=text.replace('{{'+k+'}}',v)
    report=ROOT/'validation/v2_followup/REPORT.md'
    report.write_text(text,encoding='utf-8')
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'V2-B.1_원인분석_구현_검증_판정_보고서.md').write_text(text,encoding='utf-8')
    summary=dict(verdict='REVISE / DEFER ADOPTION; preserve experimental mode; default legacy',
        n_worlds=18,mandatory_pass=data['all_mandatory_pass'],new_tests=12,parent_tests=13,
        all_previous_files_exact=preservation['all_old_files_exact'],n_preserved=preservation['old_files'],
        no_push_no_PR_no_V2C=True,benchmark=bench)
    (RES/'final_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(report)

if __name__=='__main__':main()
