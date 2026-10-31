# 2026-10-31 추가 자료와 사용처

사용자가 1031 폴더로 제공한 자료 5건을 아래 용도로 지정했다. 데이터/재현 패키지는 내부 파일 구조를 유지해 옮기고, 논문 PDF와 이상입찰 파생 자료는 용도에 따라 분리했다. 총 77개 파일, 124,787,446바이트다.

| 자료 | 사용처 | 프로젝트 내 위치 | 근거 계열 |
|---|---|---|---|
| A-01 | 구매자가 경쟁 경매 사이에서 어떻게 이동·탐색·선택하는지 분석 | data/external/end_time_recommendation/a01_bidders_curse | a01_bidders_curse |
| B-03 | 시작가·입찰 의사·구매자 행동 가정 검토 | data/external/end_time_recommendation/podwol_schneider_shared/b03_4ykkfn53js | podwol_schneider_shared |
| B-04 | 동일 상품 경매의 동시 진행·종료 시각 근접 경쟁·유사상품 수와 종료 충돌의 설명력 비교 | data/external/end_time_recommendation/podwol_schneider_shared/b04_2rf7n9mwwk | podwol_schneider_shared |
| KR-AUCTION | 유사상품 경쟁식의 학술적 근거 검토와 시뮬레이터 개선 | research/papers/competition/willingness-to-pay-and-competition-in-online-auctions-l6ipzf4ibz.pdf | chan_kadiyali_park_korean_auction |
| UCI-SHILL | 별도 이상입찰 탐지 기능의 보조 검증 자료 | data/external/fraud_detection/uci_shill_bidding/Shill Bidding Dataset.csv | uci_shill_bidding |

## A-01 — The Bidder’s Curse

구매자가 경쟁 경매 사이에서 이동·탐색·선택하는 방식을 분석하는 용도다. 설명서는 Lee·Malmendier의 The Bidder’s Curse 재현 자료로 식별된다. 입찰 단위·상품 단위·Buy-It-Now 자료, 설문, 설명서와 Stata 프로그램을 포함한다. 기존 원자료를 수정하거나 프로그램을 실행하지 않았다. 역할 지정은 해당 메커니즘이 이 자료로 이미 검증됐다는 뜻이 아니다.

## B-03·B-04 — 하나의 공유 자료 계열

두 묶음의 evidence_group은 모두 podwol_schneider_shared다. 같은 상위 폴더에 각각 출처 묶음을 보존했다. **서로 독립적인 두 데이터셋이나 두 번의 별도 검증 근거로 계산하지 않는다.** 파일·문서·논문별 역할은 구분하되, 행을 합치거나 학습/평가 표본을 나누기 전에 관측 단위·공유 원자료·경매/입찰자 식별자의 중복을 확인한다. 이번 이동 작업에서는 행 단위 중복률을 다시 추정하지 않았다. 내부 복사본·압축파일도 삭제하지 않았다.

- **B-03, Nonstandard Bidder Behavior in Real-World Auctions:** 시작가·입찰 의사·구매자 행동 가정을 검토한다. 관측 자료와 실험 자료를 구분한다. 설명서에는 일부 자료가 The Bidder’s Curse: Comment에도 쓰였다는 안내가 있어, 원 논문·후속 논문·공유 자료를 구분해 인용한다.
- **B-04, Search Costs and Equilibrium Price Dispersion in Auction Markets:** 다음 세 질문을 분석하는 데 사용한다.
  1. 동일 상품의 경매가 동시에 진행되면 낙찰 성과가 달라지는가?
  2. 종료 시간이 가까운 경매끼리 경쟁하면 입찰자 수나 낙찰가가 달라지는가?
  3. 시장에 존재하는 유사상품 수와 종료 시각 충돌 중 어느 변수가 성과를 더 잘 설명하는가?

원 출처 식별자는 폴더와 설명서 기준 Mendeley 4ykkfn53js 및 2rf7n9mwwk다. 외부 서버의 최신 버전·추가 파일·라이선스를 재조사한 목록은 아니다.

## 한국 경매 논문

**Willingness to Pay and Competition in Online Auctions**, Tat Y. Chan·Vrinda Kadiyali·Young-Hoon Park. 제공 PDF 표지는 최종 버전 March 2006이며 32쪽이다. 초록에서 한국 노트북 경매와 유사상품·동일 브랜드의 경쟁을 WTP 모형에 포함하는 연구임을 확인했다.

유사상품 경쟁식의 학술적 근거를 검토하고 시뮬레이터 개선에 활용할 자료로 지정한다. 식의 종속변수·유사성 정의·관측 시점·경쟁 범위·추정 대상을 원문과 대조해야 한다. **동시 등록된 유사상품 수**와 **종료 시각이 가까운 경매의 충돌**을 같은 변수로 간주하지 않는다. 한국 노트북 경매의 결과가 한국 수집품의 계수라는 뜻도 아니다. 이번에는 수식이나 계수를 코드/파라미터에 반영하지 않았다.

## UCI Shill Bidding

별도 이상입찰 탐지 기능의 보조 검증 자료다. 원 CSV에서 6,321행·13열, 경매 ID 807개·입찰자 ID 1,054개를 확인했다. Class 0은 5,646행, 1은 675행이다. 이는 파일 내부 식별자/라벨 수이며 실제 사람 수나 검증된 모델 성능이 아니다.

파생 특성·라벨 표로, 원시 입찰 이벤트 순서를 재생하는 자료가 아니다. 종료 시각 추천 실험과 분리해 보관하고, 이상입찰 보조 평가에서 학습·평가 경매의 중복을 통제한다.

## 보존과 현재 상태

- 원시 파일 내용과 내부 경로는 변경하지 않았다. 자료별 출발지·도착지·크기·SHA-256 및 이동 검증은 materials_2026-10-31_manifest.json에 기록한다.
- 시뮬레이터 코드·보정 파라미터·baseline-v4·기존 합성 데이터는 변경하지 않는다.
- 상태는 확보·배치·사용처 지정이다. 새 자료로 통계 추정·행동 모형 변경·이상입찰 모델 학습을 수행한 것은 아니다.
- 프로젝트 루트의 1031.zip은 이번 5개 자료 이동 대상에 포함하지 않고 원래 위치에 보존한다. 비워진 1031 폴더도 임의 삭제하지 않는다.
- 데이터·논문 보관 경로는 기존 .gitignore의 data/ 및 research/papers/ 규칙을 따른다. 자료 목록과 설명 문서는 별도로 관리할 수 있다.
