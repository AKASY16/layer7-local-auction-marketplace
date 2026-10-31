# LAYER7 합성 경매 시장

## 현재 상태 (2026-10-31)

경매 종료 시각 정책을 검증하려고 만든 합성 경매 시장 시뮬레이터와 실험 기록이다. 담당은 유선엽(@AKASY16)이다. 관련 이슈: #75(합성 시나리오·비교 평가), #72(마감 시간 추천 API), #76(통합 시연).

> **원시 데이터셋과 합성 데이터셋은 개인정보 보호 문제로 업로드하지 않는다.** 원시 데이터(eBay·Swoopo·MaxSold·ShopGoodwill 등)에는 실제 이용자 아이디가 들어 있고 라이선스도 불명확하다. 합성 데이터는 이 원시 데이터로 보정해 만든 것이라 함께 제외했고, 아래 명령으로 다시 만들 수 있다. 실험 결과 CSV·JSON과 실행 로그도 올리지 않았다. 보고서에서 이런 파일을 가리키던 링크는 "(미업로드)"로 표시했다. 원본 전체는 담당자 로컬에 보관한다.

| 구분 | 대상 |
|---|---|
| 사용 | audit-fix-v1 엔진(`src/audit/`), V2-A 관찰 모드(`src/v2_observe/`) |
| 시연 숫자 출처 | V2-C 보고서 `validation/v2_policy/REPORT.md`(5절 활동 곡선별 결과, 그림은 `validation/v2_policy/results/*.png`) |
| 보관 | baseline-v4 원본 코드(audit-fix-v1이 상속함), 감사·민감도·V2-A 보고서, 논문·데이터 분석 기록 |
| 옮기지 않음 | V2-B·V2-B.1 구매자 대안 선택 모형(채택 보류)과 V2-C 실행 코드. 쓰는 곳이 없어 담당자 로컬에만 보관한다. V2-C 보고서에 나오는 V2-B·V2-B.1 언급은 당시 기록이다 |
| 기각 | Retailrocket 쇼핑 활동 곡선으로 구매자 활동 시간을 대신하는 재검증. 수집 국가·시간대 미상, 2015년 자료, 일반 쇼핑 행동, 비상업 라이선스라 기각했고 실행 코드와 기록은 옮기지 않았다 |

**쓰지 않는 용도**: 종료 시각 추천이 거래액·낙찰가를 올린다는 효과 측정이나 인용. 결과가 구매자 활동 시간 가정에 따라 뒤집힌다(V2-C 활동량 TOP3: 저녁 피크 +5.5%, 낮 피크 −11.0%). 서비스의 마감 추천(#72)은 후보와 근거를 보여주고 판매자가 확정하며, 시뮬레이션 결과를 그 성과 근거로 쓰지 않는다.

**쓰는 용도**: 시연용 합성 시장 데이터, 입찰 API 부하·마감 직전 몰림 테스트, 추천 로직이 제약(기간, 새벽 회피, 후보 간격)을 지키는지 확인하는 통합 테스트, "같은 시간대 유사 경매 수" 같은 정보 표시의 정답지(V2-A 진단표).

**LAYER7 P1 규칙과 다른 점** (`docs/03-auction-policy.md`, `docs/02-requirements.md` 기준)

| 항목 | LAYER7 P1 | 시뮬레이터 |
|---|---|---|
| 입찰 | 수동입찰만 (자동입찰은 후순위) | eBay식 자동(프록시) 입찰. `bids.csv`를 서비스에 재생할 때는 `price_after` 흐름을 수동 입찰로 변환 |
| 가격 단위 | 1만 원 미만 100원, 5만 원 미만 500원, 10만 원 미만 1,000원 … | 1만 원 미만 500원, 5만 원 미만 1,000원, 10만 원 미만 2,000원 … (가정) |
| 경매 기간 | 1시간–7일, 예약 시작 가능 | 24–72시간만 |
| 마감 | 연장 없음 | 연장 없음 (일치) |
| 금액 상한 | 1,000만 원 | 별도 규칙 없음 (생성된 낙찰가 최대 약 97만 원이라 실제로 넘는 경우는 없음) |
| 상품군 | #62에서 확정 예정 | TCG·피규어·레트로 게임·한정판 굿즈 (가정) |
| 구매 희망·참여 가능 시간 (#70) | 구매자가 직접 등록 | 없음. 구매자 활동 시간은 생성기 내부 가정 |

**실행** (Python 3.12, 이 폴더에서)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python src/generate.py --all
.venv/Scripts/python validation/audit/test_audit.py
.venv/Scripts/python src/audit/__main__.py --scenario config/scenarios/scenario_F.yaml --seed 1 --out data/experiments/demo-F-1
```

- `src/generate.py --all`은 baseline-v4 합성 데이터(`data/synthetic`, 18개 시장)를 만든다(1–4분). 감사 테스트의 동결 해시 검사와 `validation/audit/regression.py`가 이 데이터를 쓴다.
- 해시는 Windows에서 만든 값이다. Linux에서 다시 만들어 보면 공개 CSV는 줄바꿈(CRLF)만 다르고 내용이 같았고, `hidden/buyers_latent.csv`만 일부 실수의 마지막 자리가 달랐다.
- 이 폴더만 `.gitattributes`로 줄바꿈 변환을 껐다. 동결 해시가 원래 파일 바이트 기준이기 때문이다.
- 출력 폴더는 `data/experiments/` 아래의 새 경로여야 한다. 기존 폴더를 덮어쓰는 요청은 거부한다.
- 원시 데이터가 필요한 보정 분석(`calibration/statistical_analysis/`)과 일부 V2 검증 스크립트는 저장소만으로 다시 돌릴 수 없다. 보정 결과는 `calibration/parameters.yaml`, 숫자별 출처는 `calibration/parameter_sources.csv`에 있다.

---

> 2026-10-30 독립 감사: 아래 기존 설명은 동결된 baseline-v4 기준이다. 확인된 오류를 수정한 선택 엔진 audit-fix-v1과 검증 결과는 [감사 보고서](validation/audit/REPORT.md), [실행 안내](validation/audit/README.md)를 참고한다. 기존 코드·설정·합성 데이터는 보존했다.

LAYER7(수집품 경매 플랫폼)의 경매 종료 시각 추천 실험에 쓸 합성 데이터와 그 생성기다. 실데이터 4종(Jank & Shmueli eBay, Swoopo, MaxSold, ShopGoodwill)과 논문 4편(BARISTA, Roth & Ockenfels, Simonsohn, Bimpikis et al.)을 근거로 만들었다.

- 추천 알고리즘은 들어 있지 않고, 성능 평가도 하지 않았다.
- Spring Boot 프로젝트와 DB는 건드리지 않았다.
- 합성 데이터는 LAYER7 실사용자 행동을 대신하지 못한다. 생성기는 자기 가정만 재현할 뿐이다. 어떤 것이 데이터에서 왔고 어떤 것이 가정인지는 `calibration/parameter_sources.csv`의 `class` 열에 적혀 있다.

## 폴더

```text
research/            원자료 목록(source_inventory.csv), 데이터 분석(dataset_analysis.md), 논문 분석(literature_review.md), 논문 PDF
calibration/         parameters.yaml, parameter_sources.csv(근거표), build_parameters.py, tune.py, tuned.yaml
  statistical_analysis/  analyze_*.py, results/*.json (실데이터 통계)
src/                 barista.py, world.py(외생 세계), market_simulator.py(이산 사건), generate.py(CLI), keyrng.py, config.py, sim_stats.py
config/              baseline.yaml, scenarios/scenario_A..F.yaml
data/synthetic/      scenario_X/seed_N/ (6 시나리오 x 3 시드 = 18개)
validation/          validate.py, validation_report.md, results.json, figures/
```

## 다시 만들기

Python 3.12 기준이다.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip install -r requirements.txt
```

원자료 분석부터 다시 돌리려면 아래 순서로 실행한다. 원자료 기본 경로는 `~/Desktop/Data`이고, 환경변수 `LAYER7_DATA`로 바꿀 수 있다.

```bash
.venv/Scripts/python research/inventory.py --work <압축을 풀 임시 폴더>
```

```bash
cd calibration/statistical_analysis && ../../.venv/Scripts/python analyze_jank_shmueli.py && ../../.venv/Scripts/python analyze_maxsold.py && ../../.venv/Scripts/python analyze_goodwill.py && ../../.venv/Scripts/python analyze_swoopo.py <임시 폴더>
```

```bash
.venv/Scripts/python calibration/build_parameters.py
```

`calibration/tune.py`는 일부 ASSUMED 행동 파라미터를 eBay 3일 경매 적률에 맞추는 격자 탐색이다. 결과는 이미 `tuned.yaml`에 있으므로, 다시 돌린 뒤에는 `build_parameters.py`를 한 번 더 실행해야 반영된다.

생성과 검증:

```bash
.venv/Scripts/python src/generate.py --all --smoke
```

```bash
.venv/Scripts/python src/generate.py --all
```

```bash
.venv/Scripts/python validation/validate.py
```

- 시나리오 하나는 약 10초, 18개 전체는 3–4분 걸린다.
- 같은 설정과 시드는 바이트 단위로 같은 CSV를 만든다. `metadata.json`의 `generated_at`만 다르다.

```bash
.venv/Scripts/python validation/mechanism_check.py
```

`mechanism_check.py`는 같은 세계에 종료 시각 배치 4개(21시 집중, 저녁 분산, 아무 시각, 격일 묶기)를 적용해서, 시나리오별 가정이 어떤 방향의 효과를 내는지 보여 준다. 추천 정책 평가가 아니다.

## 동결 기준선과 평가 활용 판정

- **동결 상태:** 현재 데이터와 코드는 `baseline-v4`로 동결돼 있다.
  - `BASELINE_v4.json`에 코드·설정·파라미터 33개와 데이터 CSV 198개의 SHA-256을 기록했다.
  - `python validation/check_baseline.py`는 이 파일들을 확인하고, 18개 데이터셋을 다시 생성해 바이트 단위로 비교한다.
- **변경 규칙:** 생성기를 바꾸면 새 기준선 라벨을 만든다. 실험 결과는 `data/experiments/`에 쓴다.
- **남은 불일치:** `validation/known_discrepancies.md`에 정리했다.
- **종료 시각 민감도 실험:** 결과는 `validation/sensitivity/sensitivity_report.md`에 있다. 판정 기준은 결과를 보기 전에 `decision_criteria.md`로 고정했다.
  - 시간대 효과는 가정한 한국 활동 곡선에서만 나온다. 곡선을 평탄화하면 효과가 사라진다.
  - 유사 경매 충돌의 효과는 감지되지 않는다.
  - 따라서 이 시뮬레이터는 LAYER7 추천기의 **주 평가 도구로 쓸 수 없다.**
  - 기준 문구대로 판정하면 "사용 안 함"이고, 해석상으로는 "제한적 사용"이다. 제한적 사용이란 기능·회귀·콜드스타트 테스트를 뜻하며, 효과 크기는 인용하지 않는다.

## 검증 결과 요약

자세한 내용은 `validation/validation_report.md`에 있다. 보정은 4차까지 했다.

- **구조 검증과 재현성.** 18개 모두 통과했다. 가격 경로, 최소 증가분, 낙찰자, 예산을 처음부터 끝까지 재생해서 확인했다.
- **실데이터와 맞는 항목.** 실데이터 기준은 eBay 3일 경매(J&S)와 Goodwill이다.
  - 경매당 입찰자 수
  - 입찰자당 입찰 수 (2.0 대 2.06)
  - 경매 간 입찰 수 분산 (NB size 2.0–2.3 대 2.06)
  - 낙찰가–입찰 수 기울기 (0.73–0.83 대 0.755)
  - 막판 입찰 비율
  - 입찰 시각 분포의 3단계 구조
  - 입찰자 집중도 (Gini)
- **맞지 않는 항목.**
  - 재입찰 쌍 비율이 낮다 (0.31 대 0.44).
  - 종료 5분 안에 마지막 입찰이 있는 경매가 많다 (0.55–0.62 대 0.48).
  - 피규어·한정판 낙찰가 분산이 크다 (log 표준편차 1.3–1.4 대 0.85–0.89).
  - 조회–입찰 탄력도가 크다.
  - 판매율 86–90%는 보정할 근거가 없었다.
- **종료 시간대 효과.** 가정한 한국 활동 곡선 때문에 크게 나온다. 저녁 종료가 낙찰가÷가치 기준 +15~28%p다(A만 +1.6%p).
- **같은 시각 집중의 이득.** 시나리오 D에서만 나타난다(입찰자 +0.21명).

## 데이터셋 한 개의 파일

| 파일 | 내용 | 추천기에 줘도 되는가 |
|---|---|---|
| sellers.csv | 판매자, 주력 카테고리, 등록 수/일, 선호 종료 시각 | 예 (판매자 본인 이력) |
| items.csv | 카테고리, 세부 분류, 시리즈, 상태, 희소도, estimated_value, similarity_group, appeal | appeal은 아니오(생성기 내부 매력도). estimated_value는 판매자 추정가로 간주 |
| item_similarity.csv | 같은 카테고리 상품 쌍의 유사도(규칙은 metadata.json) | 예 |
| buyers.csv | 구매자, 주 관심 카테고리, 팔로우 카테고리, 가입 시각 | 예 |
| auctions.csv | 시작, 예정 종료, 판매자 기본 종료, 실제 종료, 시작가, 증가 규칙, 상태 | 예정 종료 이전 정보만 |
| visits.csv | 방문(원인: organic / listing_alert / outbid_notice / watch_return / snipe), 열람, 입찰, 막판 입찰 실패 | 시점 이전 행만 |
| bids.csv | bid_id, auction_id, buyer_id, bid_time, bid_amount(제출한 최대액), bid_type, price_after | 시점 이전 행만 |
| outcomes.csv | 낙찰자, 낙찰가, 입찰 수, 고유 입찰자, 판매 여부 | 아니오(결과) |
| hidden/buyers_latent.csv | 예산, 활동률, 시간대 이동, 입찰 유형, 재입찰 성향, 가격 수준, 활동 기간 | 아니오 |
| hidden/valuations.csv | 열람한 (구매자, 경매)의 WTP | 아니오 |
| hidden/decisions.csv | 입찰하지 않은 이유(WTP 미달, 예산, 대체재 보유, 보류 등) | 아니오 |
| metadata.json | 생성 일시, 시드, 시나리오, 파라미터 버전, 생성기 버전, 행 수, 해시 | – |

- 시각은 모두 KST(+09:00) ISO-8601이다. 기준 시각은 `baseline.yaml`의 `start_date`이고 기간은 30일이다.
- 금액은 KRW다.
- 하드클로즈다. 입찰은 예정 종료 시각까지만 받는다.
- 가격은 eBay식 프록시 규칙으로 정한다. 선두는 2위 최대액 + 증가분을 내며, 자기 최대액을 넘지 않는다.

## 종료 시각을 바꿔 다시 시뮬레이션하기

```bash
.venv/Scripts/python src/generate.py --scenario config/scenarios/scenario_B.yaml --seed 1 --end-times my_ends.csv --out data/experiments/B1_my_policy
```

**입력.** `my_ends.csv`의 컬럼은 `auction_id, scheduled_end_at`(오프셋 포함 ISO)이다. 없는 경매는 판매자 기본값을 쓴다. 각 경매의 종료는 시작 후 24–72시간 안이어야 한다.

**같게 유지되는 것.** 같은 시드면 세계는 같다. 판매자, 상품, 구매자, 예산, 가치, 방문 후보 흐름이 이에 해당한다.

**다시 계산되는 것.** 종료 시각에 따라 달라지는 사건은 모두 다시 계산한다. 어떤 방문을 실제로 할지(시장 두께), 무엇을 볼지(곧 마감 가중), 입찰, 재입찰, 막판 입찰, 낙찰이 그렇다.

**공통 난수.** 구매자×경매×목적 단위의 키 난수를 쓴다(`src/keyrng.py`). 그래서 두 정책의 차이는 행동이 실제로 달라진 곳에서만 생긴다.

**코드에서 직접 쓰기** (`src/`를 `sys.path`에 넣은 상태에서):
```python
import config as C, world as W, market_simulator as MS
cfg = C.load("config/scenarios/scenario_B.yaml")
w = W.build(cfg, seed=1)
ends = {a["auction_id"]: a["default_end_at"] for a in w.auctions}   # 분 단위
ends[17] = ends[17] - 180                                             # 경매 17을 3시간 앞당김
m = MS.simulate(w, ends, seed=1)
```

**주의할 점.**
- 공통 난수를 써도 비교가 완전히 공정해지지는 않는다. 정책에 따라 방문 수락과 열람 대상이 달라지면, 그 이후의 키 난수는 다른 상황에서 쓰인다.
- 추천기를 평가할 때는 여러 시드에 걸쳐 결과를 보고, 정책 간 차이의 분산도 함께 보고해야 한다.
- 추천 점수식은 이 시뮬레이터의 행동 수식(방문 탄력도, 곧 마감 가중, 대체재 회피)을 그대로 베끼지 말고 독립적으로 설계해야 한다. 베끼면 시뮬레이터가 자기 가정을 확인해 줄 뿐이다.

## 시나리오

| ID | 이름 | 핵심 설정 | 근거 |
|---|---|---|---|
| A | 균등 시장 | 구매자 활동 70% 평탄화, 판매자 종료 시각 균등 | 기준 비교용 (가정) |
| B | 인기 시간 집중 | 판매자 종료가 피크에 수요보다 1.5배 몰림 | Simonsohn 2010 비율 |
| C | 유사 상품 경쟁 | 시리즈 2개/카테고리, 대체 유사도 0.95, 두께 탄력 0.05 | 방향만 Bimpikis 2020, 크기는 가정 |
| D | 시장 집중 이점 | 방문 두께 탄력 0.47, 방문당 열람 수가 두께에 비례, 대체 유사도 0.4 | Bimpikis 2020 그림 13 (B2B 구조모형) |
| E | 희소 수집품 | 시리즈 60개/카테고리, 희귀 비율↑, 유사도 0.3, 가치 분산 0.4 | 가정 |
| F | 콜드스타트 | 구매자 150, 경매 50, 판매자 12 | 가정 |

각 시나리오의 가정과 근거의 한계는 `config/scenarios/*.yaml`과 `validation/validation_report.md`에 적혀 있다.

## 생성기가 하지 않는 것

- 한국 수집품 구매자의 실제 시간대 활동을 재현하지 않는다. 활동 곡선은 가정이다.
- 결제 실패, 취소, 허위 입찰(쉴링), 판매자 재등록, 가격 학습, 추천 노출 효과, 친구·커뮤니티 유입, 외부 시세 변동을 모형화하지 않는다.
- 가치(WTP)는 경매 중에 변하지 않는다. 다른 입찰을 보고 가치를 고치는 공통 가치 효과가 없다.
- 시나리오 간 결과 차이는 설정한 메커니즘의 결과다. 실제 시장에서 그 크기가 그렇다는 증거가 아니다.

## 2026-10-31 추가 연구 자료

[사용처·보관 위치](research/materials_2026-10-31.md)를 참고한다. A-01과 B-03/B-04 공유 자료 계열은 종료 시각 추천·구매자 행동 검토, 한국 경매 논문은 경쟁 모형 검토, UCI Shill Bidding는 별도 이상입찰 보조 검증용이다. 새 자료를 확보·분류했으며 기존 코드나 보정값에 반영한 것은 아니다.
