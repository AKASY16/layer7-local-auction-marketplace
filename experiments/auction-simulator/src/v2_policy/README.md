# V2-C 종료 시각 추천 정책 평가

기존 시뮬레이터를 수정하지 않는 **평가용 정책 이식**이다. 출처는
`validation/v2_policy/reference_policy_report_v4.md` 4.4–4.7절. 원 서비스에
배포된 추천기 성능을 측정한 것이 아니다. 수치/판매자 선택이 미지정된 부분의
완성 사항과 ASSUMED 조건은 `validation/v2_policy/PREREGISTRATION.md`에 있다.

`policy.py`는 World나 시뮬레이터를 import하지 않는다. 공개 상품 필드와 등록 시점의
공개 경매 스냅숏, 사전 선언한24h 활동 곡선만 받는다. 미래 결과·입찰·개인 WTP·
예산·실제 활동 배열은 입력 계약에 없다. `conservative`는 활동량을 순위에 사용하지
않는다(출력 activity/score는 같은 스키마의 진단값). `activity`만 그 점수를 사용한다.

새 추천 규칙이 실제 구매자 행동에 벌점을 주거나 WTP를 변경하지 않는다. 기존
`audit.simulator.Market`을 기본으로 실행하며, 보존된 V2-B/B.1은 스트레스 비교에만 쓴다.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/test_policy.py
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/evaluate_policy.py --workers 3 --name my-new-experiment
```

출력은 `data/experiments/v2c-20261031/<name>/`의 새 경로만 사용한다. 이미 완료된
실험은 덮어쓰지 않는다. 중단한 같은 코드의 완료 체크포인트는 `--resume`으로
해시를 확인해 재사용한다. 불완전 파일은 삭제하지 않고 새 실험 경로를 사용한다.
전체729회와 사전 지정343회 반복을 수행하므로 실행 시간이 길다. worker 수는
처리 속도만 바꾸며 정책·시드·표본 수를 변경하지 않는다.

최종 실험은 `evaluation-2`. `evaluation-1_design.json`은 집계 코드 오류가 있던
실패 실행 기록이며 보존한다. `technical-check`는 F의 입출력 계약 확인으로 본
효과 추정에 포함하지 않는다. 자세한 이력은 `ERRATA.md`.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/analyze_policy.py --name evaluation-2
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/plots.py
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/spillover_intervals.py
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/freeze.py
.\.venv\Scripts\python.exe -B -X utf8 validation/v2_policy/build_report.py
```

시뮬레이션에서 나오는 변화는 일정 변경의 **모형 내부 총차이**다. clock-hour와
노출 기간이 함께 바뀌며 시장 간섭도 포함한다. 실제 한국 이용자 활동, 판매자
수용 행동, 실제 종료 변경의 인과 효과는 검증되지 않았다.
