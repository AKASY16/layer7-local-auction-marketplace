# V2-B 검증 안내

기존 파일을 덮어쓰지 않고 새 결과 경로를 사용한다. 원 V2-A 검증 도구의 해싱만 읽어 재사용하며 V2-A 소스를 수정하지 않는다.

```powershell
.\.venv\Scripts\python.exe -B validation/v2_choice/test_choice.py
.\.venv\Scripts\python.exe -B validation/v2_choice/references.py
.\.venv\Scripts\python.exe -B validation/v2_choice/evaluate.py --out data/experiments/v2b-20261031/새평가경로 --report validation/v2_choice/results/새평가.json --workers 2
```

이번 완료본은 evaluation-1 경로다. references는 기존 결과가 있으면 실패한다. 새 실행 이름을 쓸 때 분석·성능 스크립트의 입력 경로도 맞춘다. 원 calibration·audit·V2-A의 보고서를 갱신하지 않는다.

## 필수 검사

실제 제출 직전 budget headroom·고정 WTP cap·호가·활동 구간·열림 시각을 검사한다. 결과에서는 지출·약정·낙찰 정산·이벤트 순서·view/knowledge/WTP key 범위를 독립 확인하고 기존 CSV 구조 검사를 재사용한다.

legacy18건은 동결 audit CSV198개 바이트와 비교한다. 주 실험18건은 동일 World·시드·정책으로 한 번 더 실행해 전체 상태·선택 지식·카운터·난수/큐 스트림·CSV를 비교한다. 실험과 legacy 사이의 행동 차이는 오류로 취급하지 않는다. 두 정보 유효기간 민감도도 각각18건에서 같은 불변조건을 검사한다.

## 비교의 한계

J&S는 원3일 경매의 기존30% holdout을 다시 읽고 경매당 입찰자·bidder-auction당 입찰·재입찰 쌍 비율을 계산한다. 합성도 실제72h·입찰 있는 경매로 조건을 맞춘다. 원래 보정 표의 3개 시장 평균과 이번 pooled holdout은 집계가 달라 값이 다르다. 상품·시장 자체는 여전히 다르며 알려진 holdout이지 새로 숨긴 평가 자료가 아니다.

B-04는 신품·24–72h 범위·유찰 포함으로 정의를 맞춘다. 기간 혼합·DVD/수집품·공급·시작가가 달라 실서비스 정답이 아닌 이전 진단이다. B-03/B-04는 공유 자료 한 계열로 센다. 마스킹 ID로 이동 네트워크를 만들지 않는다.

A-01의 단일 상품·선택된 입찰 이력과 전체 합성 시장은 관측 범위가 달라 오차 점수를 만들지 않는다. 이동 지표 정의와 기술적 참조값만 나란히 제시한다. 원시 USD/KRW 가격 평균 오차도 계산하지 않는다. 기존 카테고리별 판매가격 log SD 대리값은 보조 표로 분리하고 채택 점수로 사용하지 않는다.

A–E는 큰 시장, F는 별도의 작은 시장 stress다. 같은 seed를 여러 시나리오에 썼다고 독립표본18개로 간주하지 않는다. 각 지표별 오차·변화와 시나리오·seed별 방향을 그대로 보고하고 임의 가중 합계나 결과에 맞춘 보정을 하지 않는다.
