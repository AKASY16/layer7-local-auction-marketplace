# V2-B: known-surplus-v1 (실험 전용)

기존 `max(similarity)` 확률 포기만 대체하는 실험 모형 **하나**다. 기존 코드·보정·V2-A·기존 데이터는 수정하지 않는다. 기본 모드는 `legacy`이며 새 모형을 자동 채택하지 않는다.

```powershell
.\.venv\Scripts\python.exe -B src/v2_choice/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --model legacy --out data/experiments/새경로/legacy
.\.venv\Scripts\python.exe -B src/v2_choice/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --model known-surplus-v1 --out data/experiments/새경로/experiment
```

`--max-quote-age-min 60`처럼 정보 유효기간을 지정할 수 있다. 생략하면 마지막으로 알고 있는 종료까지 유효하다. 이는 실측된 시간이 아니라 ASSUMED 설정이다. 기본 실험의 무제한·60분·360분은 같은 모형의 민감도이며 최적값 선택 결과가 아니다. legacy 모드에는 이 인수를 넣지 않는다. 종료 정책 CSV 파서는 기존 기능 그대로 제공하나 이번 평가에서는 정책 최적화를 하지 않는다.

## 정보와 수식

실제 조회할 때만 개인 고정 WTP와 현재 필요한 입찰가·알려진 종료를 기록한다. 개인 WTP의 식과 값은 기존과 같고, 발견 시 평가하는 시점·cache 행 수는 달라질 수 있다. 자신의 실제 입찰 응답에서 자신의 가격·종료 정보도 얻는다고 가정한다. 다른 경매의 최신 가격·마감·낙찰 여부는 무료로 읽지 않는다.

현재 순이익 `U_i=v_i−q_i`와 대안 관련성 점수 `s_ij(v_j−q_j)`를 비교한다. 대안은 실제로 본 것 중 알고 있는 마감이 남아 있고, 남은 자유 예산으로 진입 가능하며, 아직 낙찰받지도 선두이지도 않은 경매다. U가 양수이고 더 나은 대안이 없을 때만 기존 입찰 스타일로 진행한다. 동점은 알고 있는 종료, 경매 ID 순이다. 다른 경매로 자동 이동하거나 새 방문을 만들지 않는다.

선두 상품의 약정과 낙찰 상품의 지출은 기존 예산 처리로만 반영한다. 같은 상품을 하나 샀다는 이유로 모든 추가 구매를 막거나 고유 가치를 차감하지 않는다. 미관측 대안은 비교하지 않는다. 종료 간격 벌점·WTP 상승·별도 경쟁 차감·추가 행동 난수는 없다.

이것은 기대 낙찰 효용의 구조 추정식이 아니다. 현재/과거 표시 가격으로 비교하는 근시안성, 유사도를 순이익 관련성으로 해석하는 것, 관측 가격을 다음 조회까지 유지하는 것, 자기 응답 정보, 동점 규칙 모두 **ASSUMED**다. 오래된 저가 대안에 끌려 실제로는 구매하지 못할 수 있다. 실험 결과가 좋아도 이러한 가정이 실증 검증된 것은 아니다.

## 재사용과 범위

`make_market(..., model='legacy')`는 원 `AuditMarket` 자체를 반환한다. 실험은 별도 `AlternativeMarket`이다. `consider.py`는 원 함수의 포기 블록만 새 gate로 바꾼 고정 사본이며 AST 검사로 prefix·이후 스타일/입찰/재방문 본문이 원본과 같은지 검증한다. 이벤트 루프·방문·호가·WTP·예산·outbid·watch·마감·정산은 그대로 상속한다. log·place_bid wrapper는 관측 정보만 갱신한다.

V2-A의 큰 trace를 사용하지 않는다. 선택에 필요한 마지막 조회 정보, 작은 카운터, 기존 엔진 로그만 유지한다. 비교 상세 trace는 통제 fixture에서만 켜며 기본값은 꺼져 있다. 핵심 CSV11개·metadata·작은 choice_counters.json을 새 경로로 저장한다. 기존 폴더 덮어쓰기는 거부한다.

사전 명세와 전체 결과는 `validation/v2_choice/`에 있다. 가격·선택 계수 보정과 V2-C 정책 최적화는 포함하지 않는다.
