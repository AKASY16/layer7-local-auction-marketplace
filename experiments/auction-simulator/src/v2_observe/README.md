# V2-A 관찰 전용 엔진

`audit-fix-v1`을 상속하는 opt-in 엔진이다. 기존 엔진·설정·보정·데이터를 수정하지 않는다. V2-B 선택 모델은 포함하지 않는다.

```powershell
.\.venv\Scripts\python.exe -B src/v2_observe/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --out data/experiments/새경로/on
.\.venv\Scripts\python.exe -B src/v2_observe/__main__.py --scenario config/scenarios/scenario_A.yaml --seed 1 --no-observer --out data/experiments/새경로/off
```

`data/experiments` 아래 존재하지 않는 새 하위 디렉터리만 허용한다. `--end-times`는 기존과 같은 종료 정책 CSV를 받고 24–72시간 정책 검사를 재사용한다. `src`가 Python path에 있다면 `v2_observe.simulator.simulate(world, ends, seed, observer=True/False)`로도 사용한다.

## 행동 보존

`run`, `push`, `wtp`, `place_bid`, 예산 계산, proxy, watch·재방문·스나이프 동작은 부모 함수를 그대로 상속한다. `visit`, `consider`, `log`, `thickness`, `schedule_alerts`, `outbid`, `close`는 부모 호출 전후에 독립 저장소에 기록하는 wrapper다. 기존 큐·로그·cache·구매 상태에 진단 행을 추가하지 않는다.

관찰 코드는 난수를 호출하지 않는다. 기존 `wtp_log.get()`만 읽고 `wtp()`를 미리 호출하지 않는다. 캐시가 없으면 `not_evaluated_by_legacy` 및 빈 값으로 남긴다. `cached_quote_surplus_after_legacy`는 실제 기존 평가 후의 캐시와 조회 당시 최소가를 뺀 진단값이다. 기대 낙찰 이익·행동 공식·순위나 새 WTP가 아니다.

원본 World/config/items는 한 실행 동안 고정된다는 기존 계약을 따른다. 관찰 cache는 정적인 상품 관계만 담고 열림·마감 상태는 매번 읽는다. 순회 중 `cat_open[없는키]`를 사용하지 않아 defaultdict를 관찰 때문에 바꾸지 않는다.

## 독립 진단표

기존 audit CSV 11개는 동일하게 내보내고 `diagnostics/`에 6개 표를 추가한다. 빈 표도 열을 갖는다.

| 표 | 기록 |
|---|---|
| participation | N과 원래 방문 배수·열람 배수. organic 방문 후보의 수락 여부와 실제 조회 시점의 진단을 구분 |
| market_context | M과 1·3·6·12·24h T. 등록 직후/조회 직전 구분, 현재·예정 마감 간격 분리 |
| awareness_events | A. 실제 view만 반영, 그 시점의 표시 가격·마감·발견 순서·직전 정보. 이벤트 이력으로 당시 A 재구성 가능 |
| known_alternatives | 마지막 실제 조회의 정보만 가진 A의 최종 이력. 현재 열려 있거나 최신 가격이라는 뜻은 아님 |
| purchase_state | Q. 초기/판단 전후/상회당함 전후/정산 전후의 지출·약정·선두·낙찰을 분리 |
| decision_context | 기존 결정 이유, view 순서, 기존 WTP 캐시의 전후 존재·값과 제출 입찰 수 |

M은 현재 `[start,end)`에서 실제 LIST 처리된 다른 경매를 센다. 등록 시 같은 시각이라도 아직 LIST 처리되지 않은 경매는 보지 않는다. T는 같은 M의 부분집합이고 live/scheduled 각각의 gap을 쓴다. 이는 행동의 마감 동률 규칙을 바꾸지 않는 진단 정의다. 동일 상품 SKU가 없는 합성 World에서 `catalog_proxy_count`는 category/subcategory/series/condition/rarity의 속성 일치 수일 뿐이며 **검증된 동일 상품 수나 B-04의 영화 버전 일치가 아니다.** 식별 속성이 없으면 해당 집계는 unknown으로 남긴다.

A는 구매자에게 서버의 모든 최신 가격을 제공하지 않는다. 다른 상품의 가격·soft extension은 재조회 없이 A에 반영되지 않는다. 자신의 입찰·알림에서 얻을 수 있는 모든 정보를 모델링하는 완전한 지식 모형도 아니다. V2-A의 범위는 실제 view의 관찰이다.

초기 Q와 활동 종료 이후 기존 proxy 정산은 관리 상태 기록이며 새로운 구매자 행동이 아니다. 희망 구매 수량·실물 인도·복수 소장 선호는 추정하지 않는다.

시간은 World.origin 이후 분이며 origin과 UTC offset을 metadata에 명시한다. `trace_id`는 관찰 기록 순서이고 원 큐 번호가 아니다. `engine_log_length`는 기존 로그 append 위치다. 실제 큐 순서는 검증 도구에서 별도로 전수 비교한다.

Q와 WTP는 합성기의 잠재 진실을 포함한다. 진단표를 그대로 추천 학습 입력으로 사용하지 않는다. metadata에 역할·가정·시간·행 수·잠재 정보 표를 기록한다.

## 비용과 한계

기록은 메모리에 모은 뒤 CSV로 내보낸다. 비용은 실제 조회 수·열린 경쟁 경매 수에 따라 늘어난다. 표본 추출·trace 생략은 기본값에 없다. 성능 수치는 `validation/v2_observe/results`와 구현 보고서를 참고한다. trace 저장을 위한 스트리밍·집계 인덱스는 필요하면 별도 최적화 대상으로 남긴다.
