"""Korean evidence report from fixed result tables. No simulator or tuning imports."""
import json
from pathlib import Path
import pandas as pd
from analyze_policy import interval
ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'validation/v2_policy/results'
OUT=Path(r'C:\Users\USER\Documents\Codex\2026-10-29\https-github-com-akasy16-layer7-local\outputs\v2c-policy-evaluation-20261031')
NAMES={'manual':'판매자 수동','uniform_valid':'유효 후보 무작위','fixed48h':'48h 고정','conservative':'보수적 TOP3','activity':'활동량 TOP3'}

def md(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def ci(row,scale=1,digits=2):
    if row is None:return '표본 없음'
    return f"{row['mean']*scale:+.{digits}f} [{row['low']*scale:+.{digits}f}, {row['high']*scale:+.{digits}f}] (n={int(row['n_seeds'])})"
def main():
    raw=json.loads((RES/'evaluation-2.json').read_text(encoding='utf-8'))
    verdict=json.loads((RES/'verdict.json').read_text(encoding='utf-8'))
    preservation=json.loads((RES/'preservation.json').read_text(encoding='utf-8'))
    frame=pd.read_csv(RES/'market_metrics.csv');u=pd.read_csv(RES/'seed_uncertainty.csv')
    paired=pd.read_csv(RES/'paired_market_differences.csv')
    spills=pd.read_csv(RES/'spillovers.csv');diagnostic=pd.read_csv(RES/'exposure_and_future_supply.csv')
    def get(f,p,metric,scope='large_ABCDE'):
        q=u[u.family.eq(f)&u.policy.eq(p)&u.metric.eq(metric)&u.scope.eq(scope)]
        return None if q.empty else q.iloc[0]
    def matched(f,p,metric,scenarios):
        q=paired[paired.family.eq(f)&paired.policy.eq(p)&paired.scenario.isin(list(scenarios))&paired.seed.le(3)]
        return pd.Series(interval(q.groupby('seed')['delta_'+metric].mean()))
    nominal=frame[frame.family.eq('nominal')&frame.scenario.ne('F')].groupby('policy').mean(numeric_only=True)
    absolute=md(['정책','등록당 수익 KRW','낙찰조건부 평균가 KRW','판매율 / 유찰률','입찰자/경매','기간 h'],[
        [NAMES[p],f'{nominal.loc[p,"revenue_per_listing"]:,.0f}',f'{nominal.loc[p,"price_sold_mean"]:,.0f}',
         f'{nominal.loc[p,"sold_rate"]:.2%} / {nominal.loc[p,"unsold_rate"]:.2%}',
         f'{nominal.loc[p,"bidders_mean"]:.3f}',f'{nominal.loc[p,"duration_mean"]:.2f}'] for p in NAMES])
    delta=md(['정책 vs 수동 (A–E)','등록당 수익 ΔKRW [t95%]','수익 % 차이 [t95%]','판매율 pp [t95%]','입찰자/경매 차이 [t95%]'],[
        [NAMES[p],ci(get('nominal',p,'revenue_per_listing'),digits=0),ci(get('nominal',p,'revenue_percent')),ci(get('nominal',p,'sold_rate'),100),ci(get('nominal',p,'bidders_mean'),digits=3)]
        for p in NAMES if p!='manual'])
    sensitivity=[]
    for family,label in [('nominal_matched3','저녁 기본'),('activity_weak','약한 피크'),('activity_flat','평탄'),('activity_day','주간 피크'),('activity_night','심야 피크')]:
        for p in ('conservative','activity'):
            sensitivity.append([label,NAMES[p],ci(get(family,p,'revenue_per_listing'),digits=1),ci(get(family,p,'revenue_percent')),ci(get(family,p,'sold_rate'),100),ci(get(family,p,'bidders_mean'),digits=3)])
    activity_table=md(['실제 ASSUMED 활동 (고정 저녁 사전값)','정책','등록당 수익 ΔKRW [t95%]','수익 % 차이 [t95%]','판매율 pp','입찰자 차이'],sensitivity)
    scenario_table=md(['시나리오','정책','수익 % 차이 [t95%]','판매율 pp','입찰자 차이'],[
        [s,NAMES[p],ci(get('nominal',p,'revenue_percent',s)),ci(get('nominal',p,'sold_rate',s),100),ci(get('nominal',p,'bidders_mean',s))]
        for s in 'ABCDEF' for p in ('conservative','activity')])
    behavior=[]
    for scenarios in ('BCD','BC'):
        for p in ('conservative','activity'):
            behavior.append(['nominal seed1-3 '+scenarios,NAMES[p],ci(matched('nominal',p,'revenue_percent',scenarios)),
                ci(matched('nominal',p,'sold_rate',scenarios),100),ci(matched('nominal',p,'bidders_mean',scenarios))])
    for f,scope in [('uptake20','large_BCD'),('choice_best','large_BCD'),('substitution_zero','large_BC'),
        ('substitution_high','large_B'),('model_known-surplus-v1','large_BC'),('model_known-surplus-followup-v1','large_BC')]:
        for p in ('conservative','activity'):
            behavior.append([f,NAMES[p],ci(get(f,p,'revenue_percent',scope)),ci(get(f,p,'sold_rate',scope),100),ci(get(f,p,'bidders_mean',scope))])
    behavior_table=md(['조건 / 구성 대형 시나리오','정책','수익 % 차이 [t95%]','판매율 pp','입찰자 차이'],behavior)
    aligned=[]
    for f in ('aligned_day','aligned_night'):
        actual='activity_day' if f.endswith('day') else 'activity_night'
        aligned.append([actual+' fixed prior BCD',ci(matched(actual,'activity','revenue_percent','BCD')),
            ci(matched(actual,'activity','sold_rate','BCD'),100),ci(matched(actual,'activity','bidders_mean','BCD'))])
        aligned.append([f,ci(get(f,'activity','revenue_percent','large_BCD')),ci(get(f,'activity','sold_rate','large_BCD'),100),ci(get(f,'activity','bidders_mean','large_BCD'))])
    aligned_table=md(['선언 사전값=가정 활동 BCD','수익 % 차이 [t95%]','판매율 pp','입찰자 차이'],aligned)
    cold=md(['콜드스타트 F 활동','정책','수익 % 차이 [t95%]','판매율 pp','입찰자 차이'],[
        [f,NAMES[p],ci(get(f,p,'revenue_percent','F')),ci(get(f,p,'sold_rate','F'),100),ci(get(f,p,'bidders_mean','F'))]
        for f in ('nominal_matched3','activity_day','activity_night','activity_weak','activity_flat') for p in ('conservative','activity')])
    st=pd.read_csv(RES/'supply_proximity_strata.csv')
    st=st[st.family.eq('nominal')&st.scenario.ne('F')&st.policy.isin(['conservative','activity'])]
    stratarows=[];stratarecords=[]
    for (mb,tb,p),g in st.groupby(['M_bin','T_bin','policy'],observed=True):
        byseed=g.assign(weighted_rev=g.revenue_delta*g.n_auctions,weighted_bid=g.bidders_delta*g.n_auctions).groupby('seed').sum(numeric_only=True)
        rev=interval(byseed.weighted_rev/byseed.n_auctions);bid=interval(byseed.weighted_bid/byseed.n_auctions)
        count=int(g.n_auctions.sum())
        stratarows.append([str(mb),str(tb),NAMES[p],count,ci(rev,digits=0),ci(bid,digits=3)])
        stratarecords.append(dict(M_bin=str(mb),T_bin=str(tb),policy=p,total_support=count,
            **{'revenue_'+k:v for k,v in rev.items()},**{'bidders_'+k:v for k,v in bid.items()}))
    strata_table=md(['등록시 M','기준 종료 근접 T','정책','경매 관측 지원','등록당 수익 ΔKRW [t95%]','입찰자 Δ [t95%]'],stratarows)
    pd.DataFrame(stratarecords).to_csv(RES/'nominal_strata_seed_summary.csv',index=False)
    spill_rows=[]
    for scenarios,label in [('BCD','대형 BCD'),('F','콜드스타트 F')]:
        for p in ('conservative','activity'):
            q=spills[spills.family.eq('uptake20')&spills.policy.eq(p)&spills.scenario.isin(list(scenarios))]
            direct=q[q.group.eq('adopted')].groupby('seed').revenue_delta_sum.sum().mean()
            other=q[q.group.eq('not_adopted')].groupby('seed').revenue_delta_sum.sum().mean()
            unchanged=q[q.group.eq('end_unchanged')]
            share=unchanged.outcome_changed_count.sum()/unchanged.n.sum() if unchanged.n.sum() else float('nan')
            spill_rows.append([label,NAMES[p],f'{direct:+,.0f}',f'{other:+,.0f}',f'{direct+other:+,.0f}',f'{share:.2%}'])
    spill_table=md(['범위','정책','수용 경매 수익 Δ KRW','미수용 경매 Δ','시장 합계 Δ','종료 미변경 중 결과 변화'],spill_rows)
    sp=pd.read_csv(RES/'spillover_seed_uncertainty.csv')
    spill_ci=md(['범위','정책','수용 경매 ΔKRW [t95%]','미수용 ΔKRW [t95%]'],[
        [scope,NAMES[p]]+[ci(sp[sp.scope.eq(scope)&sp.policy.eq(p)&sp.group.eq(group)&sp.metric.eq('revenue_delta_sum')].iloc[0],digits=0)
            for group in ('adopted','not_adopted')]
        for scope in ('BCD','F') for p in ('conservative','activity')])
    exposure=diagnostic[diagnostic.family.eq('nominal')&diagnostic.scenario.ne('F')]
    exposure_table=md(['정책','평균 기간 변화 h','등록 시 알려진 동일시리즈 근접','사후 실현 근접','당시 근접0이었지만 미래 근접 발생'],[
        [NAMES[p],f'{g.duration_delta.mean():+.2f}',f'{g.known_near_mean.mean():.3f}',f'{g.realized_near_mean.mean():.3f}',
         f'{g.future_series_near_despite_zero_known.sum()/g.zero_known_series_near_count.sum():.2%}' if g.zero_known_series_near_count.sum() else '표본 없음']
        for p,g in exposure.groupby('policy')])
    structure=json.loads((RES/'information_and_schedule_checks.json').read_text(encoding='utf-8'))
    text='''# V2-C 종료 시각 TOP3 정책 평가 보고서

2026-10-31 · 브랜치 `codex/v2c-policy-evaluation-20261031`

## 판정과 제품 제공 수준

모형 내부 판정: **보수적 TOP3 = {{CONSERVATIVE_VERDICT}}, 활동량 TOP3 = {{ACTIVITY_VERDICT}}**.
수익은 모든 등록에 대해 유찰을0으로 포함한다. 판정은 사전 기준과 아래의 공동
지표/가정 민감도에 근거하며, 실제 시장의 인과 효과나 미래 수익률 예측이 아니다.
여기서 수익은 비용·수수료를 공제하지 않은 낙찰 거래액이다. 플랫폼 매출이나
판매자 순이익을 모델링한 값이 아니다.

주 분석5시드 저녁 조건에서 activity는 수익 +4.94%, 판매율 +0.47pp, 입찰자
+0.43명이다. 활동 민감도를 **동일 seed1–3**에 맞추면 저녁 수익 +5.49%가
주간 −11.02%로 반전한다. 이때 판매율은 +0.48pp→−1.75pp, 입찰자는
+0.49명→−0.69명이다. 평탄 활동의 수익 +0.89%
구간은0을 포함한다. conservative는 기본 조건에서 수익 −3.01%, 판매율 −0.50pp,
입찰자 −0.28명이다. 이 수치는 각각의 모형 실험 요약이며 한국 시장 추정값이 아니다.

**현재 LAYER7에서 수익 최적화 자동 추천을 기본 적용할 근거는 부족하다.** 제공한다면
판매자가 확정하는 **실험용 기간별 종료 후보3개·등록 지원** 수준이다. 기존 수동
시각을 기본으로 유지하고 추천 후보로 강제 치환하지 않는다. '보수적'이라는 이름이나
'근거 부족' 라벨만으로 conservative-v0를 기본 추천으로 채택하지 않는다. 기본
설정에서 그 포트는 수익·판매·입찰자가 감소했다. `activity-v1`은 자체 활동 로그·
순위 안정성·실제 정책 효과 검증 전까지
shadow 비교에 둔다. 시뮬레이션에서 특정 조건이 유리해도 현재 실제 한국 활동,
판매자 수용과 유사상품 경쟁 조건이 그 조건에 해당하는지 검증되지 않았다.

## 1. 대상·출처·보존

기본 엔진은 기술 검증된 **audit-fix-v1(legacy)** 이다. 실제 한국 수집품 시장에
실증적으로 검증된 행동 모델이라는 뜻은 아니다. baseline-v4/V2-A/V2-B/V2-B.1과
기존 모든 코드·설정·데이터·검증 산출물을 보존했다. 기존 **3,491개 파일**의
크기·SHA256을 시작/종료에 비교해 변경0·삭제0을 확인했다(`.git/.venv/__pycache__`
제외, Python `-B` 사용). 기존 README의 미커밋 변경도 시작 상태 그대로다.
푸시·PR·배포·파라미터 재보정은 하지 않았다.

TOP3는 서비스 실행 코드가 아니라 사용자의 조사 보고서 4.4–4.7절에서 확인했다.
따라서 이번 코드는 **문서 정책의 평가용 이식(port)** 이다. 원래 미지정된 π·선택
방식을 임의의 검증된 값처럼 숨기지 않고 아래 가정으로 완성했다. 실제 배포된
정책의 성능을 검증했다고 말하면 안 된다. [정책 원문 사본](/experiments/auction-simulator/validation/v2_policy/reference_policy_report_v4.md),
[사전 고정 계획](/experiments/auction-simulator/validation/v2_policy/PREREGISTRATION.md).

## 2. 고정 정책과 정보 제한

| 정책 | 종료 시각 결정 | 해석 |
| --- | --- | --- |
| manual | World가 생성한 판매자의 원래 선호/기간에 따른 default_end | 실제 사람의 선택 자료가 아닌 모형 기준선 |
| uniform_valid | 등록+24–72h의97개 30분 격자 중 독립 키 난수1개 | 시간/기간 범위 기준선 |
| fixed48h | 등록+48h | 기간 기준선, 순수 시간대의 완전 통제는 아님 |
| conservative | 심야 회피→낮은 알려진 충돌→먼 종료거리→이른 시각, 기간3구간에서1개씩 | 자체 활동 자료가 없는 초기용 |
| activity | 심야 우선 회피 후 log(선언 활동)−log(1+알려진 충돌), 최소3h TOP3 | 현재는 검증되지 않은 shadow 정책 |

두 TOP3는 [24,40)/[40,56)/[56,72]h 또는 전체 후보에서 최소3h 간격을 지킨다.
주 판매자 선택 가정은 **TOP3 중 기존 수동 선택에 가장 가까운 것**이다. 보조
실험은 TOP3 중 추천 특징 순위가 가장 좋은 것. 실제 낙찰가를 보고 고르지 않는다.
이는 TOP3의 효과가 판매자 반응 가정에도 의존함을 드러내기 위한 분리다.

`C_i(t)=Σ sim(i,j) × max(0, 1−|end_j−t|/60분)`. 등록 시점에 이미 등록된 열린
경매의 공개 taxonomy 유사도·예정 종료만 쓴다. 등록 순서는 `(start_at,ID)`로
직렬화하며 확정된 일정을 다음 판매자에 반영한다. 동시 요청/확정 지연이 있는
운영 환경의 불일치까지 해결한 것은 아니다. 미래 등록 공급을 추정해 덧붙이지 않는다.

activity의 β=1·γ=0은 문서의 기존 휴리스틱 가정이다. π는 문서에 고정되지 않아
심야를 항상 뒤로 정렬하는 방식으로 완성했다. 따라서 다른 유한 π의 결과와 같다는
주장은 하지 않는다. 엔진에 충돌 벌점이나 WTP 조정은 추가하지 않았다. conservative는
활동량을 순위에 사용하지 않으며 trace의 activity/score는 같은 스키마의 진단값이다.

주 분석의 활동 사전값은 고정된 기존 저녁 곡선이며 한국 실측이 아니다. 추천 함수는
World·미래 입찰/낙찰·구매자 예산/WTP/스타일/appeal·실제 활동 배열에 접근하지
않는다. aligned_prior만 사전 선언한 모형 활동 곡선을 입력에도 맞춘 정보 일치
진단이다. 미래 결과를 읽지 않으며, 성과의 수학적 상한이나 실제 추정기의 성능은 아니다.

## 3. 실험·검증·불확실성

- 본 실행 **729개 시장**, 사전에 지정한 반복 **343개** 통과. 모든 본 실행을
  반복했다고 과장하지 않는다. 주 실험150개 전부와 각 민감도 조건 seed1을 반복했다.
- 같은 조건 반복에서 전체 상태/WTP 캐시/예산/로그/이벤트 큐 해시가 일치했다.
  nominal의 두 추천 ×6시나리오 seed1 =12개는 ordered RNG/heap도 반복 일치했다.
- 신규 계약/통제 테스트10개와 통계 단위/결측 처리 테스트2개 통과. legacy 수동18개는 기존11 CSV씩 **198파일**과
  일치했다. 미채택 모형 비교에서도 V2-B/B.1의 수동 기준을 이전 결과와 대조했다.
- 입찰 한도·예산·WTP·활동 구간·이벤트 순서·실제 관측 쌍·정산 불변조건 통과.
  추천은 등록+24–72h, TOP3 간격, 등록 시점 정보 제한 계약을 검증했다.
- 실제 활동만 바꾼 조건에서 고정 사전값 정책의 일정은 nominal과 {{FIXED_CHECKS}}개
  비교에서 정확히 같았다. 실제 활동/결과를 읽어 추천을 바꾸지 않았다는 추가 검사다.
- 처음의 evaluation-1은 집계 코드 중복 필드 오류로 결과 기록 전 실패했다.
  집계까지 테스트를 보완하고 동일 설계로 evaluation-2를 실행했다. 원래 설계 기록과
  오류 이력은 보존했다. 정책·표본·판정을 결과에 맞춰 바꾸지 않았다.

주 실험 A–F×5시드, 활동4조건×A–F×3시드, 수용20%/후보 선택/기존 대체 계수/
미채택 행동 모형/활동 사전값 일치를 분리했다. World를 복사하고 구매자 성향·
예산·활동 기간·방문 후보·판매자 기본 일정·상품을 그대로 둔다. 활동은 day(−7h),
night(+6h), weak(.3×기존+.7×flat), flat으로만 바꾼다. 평균1·기존 peak 이하라
기존 Poisson thinning cap을 넘지 않는다. 원래 판매자 종료 선호는 고정해
판매자/구매자 활동이 어긋난 상황도 의도적으로 시험한다.

정책 간 차이는 World 안에서 먼저 만들고 **독립 seed**를 통계 단위로 사용한다.
A–E는 같은 seed의5시나리오 평균 후 n=5, F는 따로다. 민감도는 n=3의 넓은 t95%
구간이다. 활동 비교의 저녁 기준은 같은 seed1–3을 사용한다. 경매 수를 표본 수로
늘리거나 이미 알고 있던 실측 자료를 새 독립 검증처럼 쓰지 않는다. 상대 수익은
시나리오 상대 차이의 동일 가중 평균이다. 다중 비교·모형 오류·실측 불확실성은
구간에 포함되지 않으며 확증적 실증 인과 검정이 아니다.
소표본 t 구간은 정규 근사라 비율의 가능한 범위를 벗어날 수 있다. 특히 F의
큰 구간을 사후 절단해 더 확실해 보이게 만들지 않았다.

## 4. 기본 정책 성과

아래 절대값은 A–E×5 World별 통계의 평균. 유찰은 수익0, 입찰자0을 포함한다.
시장 총수익은 각 실행의 `revenue_total`에 별도로 보존했다.

{{ABSOLUTE}}

{{DELTAS}}

[기본 정책 비교 그림](/experiments/auction-simulator/validation/v2_policy/results/nominal_policy_comparison.png).

낙찰 조건부 평균가만 비교하면 낙찰 표본 자체가 달라진다. 판매율·입찰자·유찰0
수익과 반드시 같이 읽어야 한다. 추천으로 종료 시각을 바꾸면 경매 기간과 노출도
함께 바뀌므로 이 차이를 **순수한 시간대 효과**라고 부를 수 없다.

## 5. 활동 곡선·피크 강도·평탄 조건

{{ACTIVITY_TABLE}}

판정의 공동 주 지표는 사전 고정한 **KRW 등록당 수익**이다. 상대%는 시나리오별
비율을 동일 가중한 보조 요약이라 원 단위 차이와 가중이 다르다. 예를 들어 주간
conservative의 상대% 구간은 양수지만, 주 지표 KRW 구간 하한은 약−0.62원으로
0을 포함한다. 경계적인 결과를 골라 성공 판정을 뒤집지 않았다. F처럼 세 시드에서
같은 변화가 반복되면 표본 t 구간 폭이0일 수 있으나 모형 밖 불확실성이0이라는 뜻은 아니다.

콜드스타트 F는 표본 크기가 다른 별도 시장이다. 다음 결과를 A–E에 합치지 않았다.

{{COLD}}

활동 사전값은 그대로인데 실제 모형 활동만 바뀌는 주 스트레스다. 동일한 추천이
유리해지는 조건과 불리해지는 조건을 구분한다. 평탄 조건에서도 가격/기간/공급/
예산/가용성 경로가 남으므로 단순히 모든 정책 차이가0이어야 한다고 기대하지 않는다.
평탄화는 기존 availability가 profile.max로 나누는 효과도 바꾸며, 이것도 실측된
사실이 아닌 기존 모형 가정이다.

[활동 민감도 그림](/experiments/auction-simulator/validation/v2_policy/results/activity_sensitivity.png),
[가정 활동 곡선](/experiments/auction-simulator/validation/v2_policy/results/assumed_activity_profiles.png).

아래 aligned 정보 일치 진단은 BCD에만 있으므로 위 전체 A–E 값과 바로 비교하지
말고 원 CSV의 같은 BCD·seed 조건과 대조해야 한다. 자체 한국 활동 로그를 확보한
추천기가 이렇게 잘 추정한다는 실증 증거는 아니다. 심야 우선 회피 제약도 그대로다.

{{ALIGNED}}

## 6. 시나리오·공급·근접·대체성

{{SCENARIOS}}

시나리오 C는 공급/대체성, D는 참여/주의 이점, E는 희소성 등 여러 속성이 다르므로
그 차이 전체를 공급 M 또는 근접 T의 인과 효과라고 해석하지 않는다. 원래 수동
기준의 등록 시점 동일시리즈 M=0/1–2/3+, 근접 T=0/1+에 따른 대응 차이·표본 수·
시드 구간을 별도 저장했다. 일부 T층은 표본이 적을 수 있으며 행 수를 독립 n으로
쓰지 않았다. [공급/근접 층화](/experiments/auction-simulator/validation/v2_policy/results/strata_seed_uncertainty.csv).

사전에 고정한 M/T층의 nominal A–E 요약은 다음과 같다. 같은 seed 안에서는 경매
관측 수로 가중하되 통계 단위는 seed다. 12,500경매 관측은25개 World·5개 시드에
속하며 독립 표본12,500개가 아니다. T=1+는1,048관측(약8.4%)이고 상품·시나리오
구성도 다르다. 정책별 지원 수는 같은 기준 집합을 반복 표시한다. M=0,T=1+는
정의상 표본이 없어 효과0으로 채우지 않았다. 이는 조건부 이질성, M/T의 독립 인과
효과가 아니다.

{{STRATA}}

{{BEHAVIOR}}

위 조건의 대형 시장 구성은 각각 BCD/BC/B이므로 A–E 전체와 같은 집합이 아니다.
동일 조건 안에서 수동 대비 방향을 비교한다. V2-B/B.1은 기술 불변조건을 통과했지만
행동의 실측 재현성이 충분하지 않아 미채택 상태다. 여기서 정책이 유리하다고 그
구매자 모형이 검증되는 것은 아니며, 방향이 바뀌면 모형 의존성의 경고다.

## 7. 전체 시장 간섭과 추천 수용

20% 수용자는 World와 독립 키 해시로 미리 선택했다. 실제 수용률 추정값이 아니다.
아래 KRW는 같은 seed에서 해당 시나리오의 시장들을 합친 후 시드 평균이다.
이득과 손실이 정확히 합쳐 전체 시장 변화가 되는지 검사했다.

{{SPILLOVER}}

같은 분해의 seed 단위 불확실성은 다음과 같다. 평균 미수용 손실이 항상 발생한다는
보장은 아니며 n=3의 구간을 함께 확인해야 한다.

{{SPILL_CI}}

[시장 이득 분해 그림](/experiments/auction-simulator/validation/v2_policy/results/partial_uptake_spillover.png).

종료 미변경 경매의 결과 변화는 낙찰/가격/입찰자/입찰 수/승자 중 하나가 달라진
경우다. 단순 global visit_id 변화는 세지 않았다. 모든 입찰 시각/경로 변화까지
포함한 상한이 아니라 이 결과 변수들에서 확인된 간섭이다. 수용 경매만의 성과를
플랫폼 전체 개선으로 대신하지 않았다.

## 8. 기간과 미래 공급의 미관측

{{EXPOSURE}}

동일시리즈 ±60분에 관한 표이며 전체 taxonomy 가중 C와 같지 않다. '당시 근접0'
이라도 나중에 등록한 경매 때문에 실제 근접이 생길 수 있다. 이 사후 정보는
**감사에만** 쓰고 추천 입력에 넣지 않았다. 모든 쌍을 양방향 합산한 미래 공급
비율은 시간 순서 대칭 때문에 약1/2가 될 수 있어 이를 새로운 경험적 발견으로
해석하지 않았다. 아직 등록되지 않은 경매를 아는 것처럼 혼잡 회피를 보장할 수 없다.

기간별 세 선택지와 거리 동점 규칙은 알려진 공급이 적은 먼 시점을 택할 수 있다.
그 결과의 노출 기간 증가까지 함께 평가했다. fixed48h·무작위 기준선을 공개하되
기간 차이의 완전 분리나 최적 시간의 식별로 포장하지 않았다.

## 9. 추천 근거의 신뢰 수준

| 근거 | 이번에 확인한 범위 | 신뢰·제품 표시 |
| --- | --- | --- |
| 기술 정합성 | 테스트·정보 계약·회귀·지정 반복·해시 | 시험한 범위에서 높음; 수익 보증과 무관 |
| 입력 데이터 충분성 | 실제 한국 활동/판매자 수용 자료 없음 | 부족; 합성 사건 수로 충분 라벨을 올리지 않음 |
| 순위 안정성 | 결정적 같은 입력 재현; 고정 prior 일정 동일 | 통계적 안정성/올바름 증거 아님; 실제 표본 부트스트랩 별도 |
| 정책 효과 | 고정된 모형 가정 안의 paired 차이·민감도 | 조건부 시뮬레이션 근거, 실제 효과 미검증 |
| 인과적 일반화 | 실제 한국 종료 시각 개입 자료 없음 | 주장 불가 |

코드/API의 input-purity나 재현성과 사회과학적 외적 타당성을 분리한다. 관측 논문의
종료 근접 회귀계수를 구매자 벌점·WTP·추천 가중치로 옮기지 않았다. 실데이터의
상관 관계나 B03/B04 중복 표본도 정책의 독립 인과 검증으로 세지 않았다.

## 10. LAYER7 제공안과 미해결 한계

1. TOP3를 보여 준다면 **시연/실험용 기간별 후보3개**와 기존 수동 선택을 함께
   제공하는 수준이다. 기존 conservative 포트를 '안전한 기본 추천'으로 도입하지 않는다.
   판매자 확인 없이 종료를
   자동 설정하거나 '낙찰가가 높아지는 시간'이라는 문구를 사용하지 않는다.
2. `data_sufficiency=INSUFFICIENT`, `effect_validation=SIMULATION_ONLY_REAL_EFFECT_UNVERIFIED`
   등을 분리해 관리한다. '같은 입력에 같은 추천'을 높은 효과 신뢰도로 표시하지 않는다.
3. 심야·유사 경매 현황은 규칙/사실로 설명할 수 있으나 종료 중복을 금지하거나
   충돌 회피가 언제나 이득이라고 안내하지 않는다. 등록 때 최신 공개 정보로 재확인하고
   판매자의 원래 선택 유지도 허용한다. 이번 평가에는 동시 요청/확정 지연이 없다.
4. 자체 활동의 시간대별 고유 사용자/관측일/후보별 지원 범위, 노출 TOP3·정책 버전·
   추천 시각의 정보 스냅숏·실제 선택·최종 종료·시장 결과를 기록한다. 활동 추정과
   실제 정책 효과 검증은 별개다. 결정론적 로그만으로 IPS/DR 인과평가를 하지 않는다.
5. 후속 실제 검증은 시장 간 간섭과24–72h 진행 경매의 carryover를 고려한 설계가
   필요하다. 판매자 자기 선택 비교나 개별 경매만의 무작위화로 시장 효과를 단정하지 않는다.

추가 한계는 고정 WTP, 미측정 실수요·다중 구매·재방문 가용성, 불충분한 C/T 경로,
사전값/기간/노출 혼입, 적은 seed, 다른 기간·품목의 과거 실측 자료, 실제 수용 행동
부재다. 보존된 기본 엔진도 실제 시장의 정답이 아니다. 이번 작업은 특정 시간이나
정책에 유리하도록 생성기를 보정하지 않았고, 이를 이유로 자동 적용을 밀어붙이지 않는다.

## 11. 산출물과 재현

추가 경로는 `src/v2_policy/`, `validation/v2_policy/`, `data/experiments/v2c-20261031/`.
`policy.py`는 공개 정보만 받는 일정 생성기, `design.py`는 고정183개 실험 묶음,
`evaluate_policy.py`는729시장/343반복·검증·체크포인트, `complete_tail.py`와
`complete_middle.py`는 같은 고정 조건의 후속 묶음을 추가 CPU에서 계산하는 실행
보조다. 표본을 추가하지 않는다.
`analyze_policy.py`는 seed 차이/구간/간섭/층화, `plots.py`는 독립 PNG/SVG를 생성한다.
첫 실패의 design registry와 technical-check도 보존하되 효과 추정에 섞지 않았다.

[실행 안내](/experiments/auction-simulator/src/v2_policy/README.md) ·
[전체 결과](/experiments/auction-simulator/validation/v2_policy/results/evaluation-2.json) ·
[시드별 구간](/experiments/auction-simulator/validation/v2_policy/results/seed_uncertainty.csv) ·
[판정 근거](/experiments/auction-simulator/validation/v2_policy/results/verdict.json) ·
[기존 파일 보존](/experiments/auction-simulator/validation/v2_policy/results/preservation.json).
Python/라이브러리 버전은 [environment.json](/experiments/auction-simulator/validation/v2_policy/results/environment.json)에 기록했다.
byte 동일성은 이 Windows/Python/라이브러리 환경 기준이며 다른 환경에서는 수치/
CSV 직렬화 차이를 별도로 검증해야 한다.
'''
    replacements=dict(CONSERVATIVE_VERDICT=verdict['conservative']['simulation_verdict'],ACTIVITY_VERDICT=verdict['activity']['simulation_verdict'],
        ABSOLUTE=absolute,DELTAS=delta,ACTIVITY_TABLE=activity_table,SCENARIOS=scenario_table,BEHAVIOR=behavior_table,
        ALIGNED=aligned_table,COLD=cold,STRATA=strata_table,SPILLOVER=spill_table,SPILL_CI=spill_ci,EXPOSURE=exposure_table,FIXED_CHECKS=str(structure['fixed_prior_profile_changes']))
    for key,value in replacements.items():text=text.replace('{{'+key+'}}',value)
    assert '{{' not in text and preservation['all_old_files_exact']
    (ROOT/'validation/v2_policy/REPORT.md').write_text(text,encoding='utf-8')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'V2-C_TOP3_정책평가_보고서.md').write_text(text,encoding='utf-8')
    def point(f,p,metric):
        r=get(f,p,metric)
        return {k:float(r[k]) for k in ('mean','low','high')}|{'n_seeds':int(r['n_seeds'])}
    summary=dict(n_markets=729,n_repeats=343,n_instrumented_RNG_heap_pairs=12,
        tests=12,technical_checks_pass=raw['all_mandatory_pass'],old_files_preserved=3491,
        verdict={p:v['simulation_verdict'] for p,v in verdict.items()},
        production='No automatic profit optimization; manual default + experimental reference choices; activity shadow',
        main_activity_revenue_percent=point('nominal','activity','revenue_percent'),
        matched3_activity_revenue_percent=point('nominal_matched3','activity','revenue_percent'),
        mismatched_day_activity_revenue_percent=point('activity_day','activity','revenue_percent'),
        main_conservative_revenue_percent=point('nominal','conservative','revenue_percent'),
        real_Korean_activity_validated=False,real_causal_effect_validated=False,no_push_no_PR=True)
    (RES/'decision_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(OUT/'V2-C_TOP3_정책평가_보고서.md')

if __name__=='__main__':main()
