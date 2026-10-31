# 공개 경매 데이터는 규칙 기반 추천기까지만 받쳐준다

> 조사 기준일: 2026-10-30. **문서 버전: v4 (2026-10-30, 구현 정책 및 내부 정합성 수정).** 검증 수준 표기는 다음과 같다. **[직접 검증]** 파일을 실제로 내려받아 열고 스크립트로 집계함. **[부분 확인]** 앞부분, 샘플 행, 스키마, 메타데이터만 봄. **[웹 페이지만]** 랜딩 페이지나 문서만 읽음. **미확인** 근거를 찾지 못함. 검증용 다운로드 파일과 분석 스크립트는 세션 scratchpad(`(당시 로컬 작업 폴더)/`)의 `downloads/`, `downloads2/`, `scripts/`, `scripts2/`에 있다. 이 보고서는 법률 자문이 아니다.

## 1. 핵심 결론

**현재 공개된 데이터만으로 할 수 있는 일은 세 가지다. 규칙·점수 기반 추천기(접근법 A)를 설계하고, 그 파라미터를 대략 보정하고, 외국·과거 플랫폼 데이터에서 예측 모델을 오프라인으로 실험하는 것까지다. "LAYER7에서 종료 시각을 바꾸면 입찰이 늘어나는가"라는 인과 효과와 TOP 3 추천 정책의 실제 효과는 공개 데이터로 평가할 수 없다.** 직접 내려받아 확인한 데이터셋은 10개가 넘는다. 그러나 수집품 도메인이면서, 절대 종료 시각과 개별 입찰 로그를 함께 담고, 판매자가 24–72시간 안에서 종료 시각을 고르는 구조인 공개 데이터셋은 하나도 없었다. 시간 단위로 종료 시각을 분석할 수 있고 성과 데이터도 있는 실데이터는 네 개뿐이다. 첫째는 Jank & Shmueli eBay 데이터 중 Palm M515 7일 경매 **158건**짜리 파일로, 절대 시각이 들어 있지만 2003년 데이터이고 시간대가 표기돼 있지 않다. 둘째는 MaxSold 경매 **24,621건**이다. 종료 시각을 플랫폼이 정하기 때문에 **97.6%가 19–21시에 몰려 있고**, 24–72시간 경매는 0.9%에 불과하다. 셋째는 Swoopo 페니옥션 12.1만 건이다. 입찰이 들어올 때마다 종료 시각이 연장되므로 종료 시각이 입찰 행동의 결과로 정해진다. 넷째는 GitHub `silentdirectivellc-hub/ebay-sold-comps` 저장소에 들어 있는 **ShopGoodwill 낙찰 경매 2,678행**(2026-06~09)이다. 이 데이터는 처음 조사에서 놓쳤고 사용자가 알려 준 뒤 직접 내려받아 확인했다. 실제 종료 시각(분 단위, 시간대 미표기), 입찰 수, 낙찰가, 판매자 ID가 있고 LEGO·레코드·필름카메라처럼 수집품에 가까운 품목이다. 다만 시작 시각, 개별 입찰 로그, 유찰 경매가 없다. eBay 쪽 경로도 막혀 있다. eBay API License Agreement는 eBay Content로 알고리즘을 학습시키거나 ML을 수행하거나 합성 데이터셋을 만드는 것을 명시적으로 금지한다 ([eBay API License Agreement](https://developer.ebay.com/join/api-license-agreement)). 따라서 실무적 권고는 다음과 같다. 출시 단계에서는 공개 데이터와 문헌에서 얻은 **사전값으로 동작하는 규칙 기반 추천기**를 쓴다. XGBoost/LightGBM(접근법 B)은 MaxSold 같은 공개 데이터에서 A와 비교하는 오프라인 실험으로만 둔다. 출시 초기 추천은 결정론적으로 만든다. 데이터가 부족하거나 추천 순위가 매우 불안정하면 기간 구간별로 분산한 보수적 TOP 3를 제시하고, 활동 데이터와 순위 안정성이 확보되면 점수 우선·최소 간격 방식으로 전환한다. 추천과 판매자의 선택을 로그로 남긴다. 보수적 정책에는 심야 종료 회피와 이미 등록된 유사 경매와의 충돌 회피만 적용하고 "추천 근거 부족"으로 표시한다. 이 라벨은 데이터 충분성과 추천 순위 안정성만 나타낸다. 추천을 따랐을 때 성과가 좋아지는지는 별도의 검증 상태로 관리한다. 실제 효과를 검증하기 위한 무작위화는 나중에 평가 설계와 함께 도입한다. 종료 시각과 입찰 수의 상관은 종료 시각을 바꿨을 때의 인과 효과를 증명하지 못한다는 점, 그리고 Bimpikis et al.이 증명한 것과 LAYER7이 빌려 쓰는 가설이 다르다는 점이 이 보고서 전체의 전제다.

## 2. 데이터셋 전체 비교표

### 2.1 요약 비교표: 시간 단위로 쓸 수 있는 실데이터는 네 개뿐이다

"실제 종료 시각" 열에는 타임스탬프 유형(절대, 상대, 날짜만, 없음)과 시간대 정보를 함께 적었다. 확인한 데이터셋 가운데 **타임스탬프를 무작위로 바꾼(randomized) 데이터는 없었다**. 활용 가능성은 LAYER7 종료 시각 추천에 얼마나 직접 쓸 수 있는지를 기준으로 매겼다. 규모가 커도 종료 시각 정보가 없으면 낮게 평가했다.

| 데이터셋 | 경매 건수 | 실제 종료 시각 포함 여부 (유형·시간대) | 개별 입찰 로그 | 최종 성과 데이터 | 활용 가능성 | 데이터 품질 | 다운로드 링크 |
|---|---|---|---|---|---|---|---|
| **Jank & Shmueli eBay 입찰 이력** (Kaggle `auction.csv` = Drive 표준 파일 9개) | 628 (입찰 10,681, 입찰자 3,388) | **없음**. 상대 시간뿐(bidtime = 시작 후 경과 일수, 기간 3/5/7일). 시간대 해당 없음 | **있음** (eBay 사용자명, 평점) | 낙찰가(price), 시작가 | 중상 | 중 (bidder NA 16행, Private 9행) | [Kaggle](https://www.kaggle.com/datasets/onlineauctions/online-auctions-dataset), [Drive](https://drive.google.com/drive/folders/1tr3Q1A2UDGUZsEMs06fsKAhWmCmE-_0N) |
| **Palm M515 7일 158건 Visualization** (Drive 전용) | 158 (실입찰 3,643, 입찰자 1,122) | **복원 가능**. 절대 입찰 시각과 절대 시작 시각(초 단위)이 있고, 종료 = 시작 + 7일로 추정. **시간대 표기 없음(미확인)** | **있음** | 입찰액. 낙찰가는 Curve Clustering 파일과 결합해야 함 | **상** (유일한 조합) | 중하 (표본 작음, `*` 행 324개) | [Drive Palm 폴더](https://drive.google.com/drive/folders/1hO1k7VNKQ5ggnb6JSXKe5RQ4GvUYCRrQ) |
| **MaxSold** (HF `jpearce610/auction_data`, `item_data`, `bid_data`) | 24,621 (물품 3,033,289, 입찰 33,593,686) | **있음**. 절대 시각, ISO 8601 초 단위, **UTC offset 포함**(-0400 15,967건, -0500 7,150건 → 미 동부). 물품별 `item_end_time`에 연장 입찰 반영 | 있음. **단, 입찰자 ID 없음** | 총 낙찰액, 총 입찰 수, 조회수(경매·물품) | 중상 | 중 (1969 자리표시 17건) | [HF auction_data](https://huggingface.co/datasets/jpearce610/auction_data) |
| **Swoopo 페니옥션** (BU) | outcomes 121,470행 / traces 7,353건 | **있음**. 분 단위, 모든 행에 **"PDT" 라벨**(겨울 포함 → 실제 시간대 모호). traces는 초 단위, 시간대 미표기 | **있음** (입찰자 60,537명, 2009-10~12) | finalprice, placedbids | 중 | 중 (형식 불량 102행) | [tar.gz](https://people.bu.edu/zg/swoopo-dataset.tar.gz) |
| **eBayAuctions.csv** (Shmueli et al., DMBA) | 1,972행 (**고유 1,626**) | **없음**. 종료 요일(endDay)과 기간만. 시간대 미확인 | 없음 | ClosePrice, Competitive? | 하~중 | 하 (**완전 중복 17.5%**) | [raw GitHub](https://raw.githubusercontent.com/gedeck/dmba/master/src/dmba/csvFiles/eBayAuctions.csv.gz) |
| **UCI Shill Bidding** (#562) | 807 (행 6,321) | **없음**. 0–1로 정규화한 상대 시점 특징뿐 | 없음 (파생 특징, ID 마스킹) | 가격 없음, 사기 라벨(Class) | 하 | 중 (반자동 라벨) | [UCI zip](https://archive.ics.uci.edu/static/public/562/shill+bidding+dataset.zip) |
| **GSA 잉여물자 아카이브** (HF govauctions) | 13,837 lot | **날짜만** (YYYY-MM-DD, UTC) | 없음 | 확정가 아닌 current_or_final_bid, bid_count, sold | 하~중 | 중 | [HF CSV](https://huggingface.co/datasets/govauctions/us-gsa-surplus-auctions) |
| **GSA Auctions API** (실시간 스냅샷) | 1,060 lot (2026-10-30) | **날짜만**. 과거 이력 없음 | 없음 | biddersCount·highBidAmount (457건만) | 하 | 중 (담당자 PII 포함) | [API 문서](https://gsa.github.io/auctions_api/fields) |
| **NBER eBay Best Offer** | 경매 아님 (listing 약 9,800만) | listing 종료는 **날짜만**. 제안 시각은 초 단위, 시간대 미표기 | 제안(offer) 로그, 익명 구매자 ID | item_price, 제안 상태 | 하~중 (활동 곡선 보조) | 높음 (5.9GB, 부분 확인) | [NBER](https://www.nber.org/research/data/best-offer-sequential-bargaining) |
| **Mario Kart Wii eBay** (OpenIntro) | 143 | **없음** (duration 일수만) | 없음 | n_bids, total_pr | 하 | 중 | [CSV](https://www.openintro.org/data/csv/mariokart.csv) |
| **Pokémon Card Sold-Price Reference** | 0 (카드 508장 시세 집계) | 없음 | 없음 | 판매가 중앙값 | 하 (기준가 피처용) | 중 | [Kaggle](https://www.kaggle.com/datasets/ryanheger/pokemon-card-sold-price-reference) |
| **Copart** (rebrowser 무료 표본) | 26,600행 표본 (전체 3,221,500건은 유료) | saleDate + saleTime(HHMM) + saleTimeZone. 정해진 라이브 경매 일정 | 없음 | **highBid 100% 마스킹** | 하 | 하 | [Kaggle](https://www.kaggle.com/datasets/rebrowser/copart-dataset) |
| **Mercari MerRec** | 경매 아님 (이벤트 12.7억 건) | 해당 없음 (stime 이벤트 시각, 시간대 미확인) | 해당 없음 (조회 등 이벤트) | 고정가 | 하~중 (활동 곡선 참고) | 높음 | [HF](https://huggingface.co/datasets/mercari-us/merrec) |
| **ShopGoodwill 낙찰 경매** (GitHub `ebay-sold-comps`의 `goodwill-*.csv` 12개) | 2,678행 (중복 96행 → 약 2,582건, 판매자 144명) | **있음**. 절대 시각 분 단위(`2026-06-20T18:00:00`). **시간대 표기 없음(미확인)**. 시작 시각·기간 없음 | 없음 (경매당 입찰 수 `bids`만) | sold_price_usd(낙찰가), bids, seller_id, category | **상** (수집품 + 판매자 ID) | 중 (낙찰분만, 키워드별 1–3일 창, LEGO 파일은 item_id·category 공란) | [GitHub](https://github.com/silentdirectivellc-hub/ebay-sold-comps) |
| 같은 저장소의 eBay 판매 기록 (`castiron.csv` 등 15개) | 570행 | **날짜만** (`2026-09-18`) | 없음 | sold_price_usd, condition. 입찰 수 없음 | 하 | 중 (제3자 스크래퍼 수집) | 같은 저장소 |

표를 읽는 요령은 간단하다. 절대 종료 시각, 입찰 로그, 성과 데이터를 모두 갖춘 행은 Palm 158, MaxSold, Swoopo 셋뿐이다. 셋 다 LAYER7과 경매 구조가 다르다. Palm 158은 표본이 작고, MaxSold는 종료 시각을 판매자가 아니라 플랫폼이 정하며, Swoopo는 페니옥션이다. ShopGoodwill은 입찰 로그가 없는 대신 **실제 종료 시각, 입찰 수, 낙찰가, 판매자 ID를 경매 단위로 함께 가진 유일한 최근(2026년) 수집품 경매 데이터**다. 나머지는 요일·기간 수준의 거친 근거나 보조 피처의 원천일 뿐이다.

### 2.2 데이터셋별 13개 필수 항목

#### (1) Jank & Shmueli "Modeling Online Auctions" eBay 입찰 이력 (Palm 7일 158건 파일 포함)

이 데이터는 이전 문헌 노트에서 "경매별 종료 시각이 있다"고 소개됐다. 직접 열어 보니 표준 파일 9개에는 **시작 후 경과 일수만 있다**. 결정적인 정보는 Drive에만 있는 파일 두 개에 들어 있다.

| 항목 | 내용 |
|---|---|
| 1. 이름·공식 출처 | Jank & Shmueli, *Modeling Online Auctions*(Wiley, 2010) companion site ([datasets 페이지](https://www.modelingonlineauctions.com/datasets)). Kaggle `onlineauctions/online-auctions-dataset`은 재배포본이다 ([Kaggle API view](https://www.kaggle.com/api/v1/datasets/view/onlineauctions/online-auctions-dataset)) |
| 2. 다운로드 경로 | Google Drive 폴더의 파일 14개를 `uc?export=download`로 로그인 없이 받았다 ([Drive](https://drive.google.com/drive/folders/1tr3Q1A2UDGUZsEMs06fsKAhWmCmE-_0N)). Kaggle zip은 공개 API `/api/v1/datasets/download/...`로 로그인 없이 받았다(2026-10-30 기준) |
| 3. 공개 연도·수집 기간 | 책 2010년, Kaggle 2016-11-13. Palm 158 파일은 **경매 시작 2003-03-16~2003-05-18, 입찰 시각은 2003-05-25까지**. Cartier·Xbox 수집 기간은 **미확인** |
| 4. 규모 | 표준: 경매 628건, 입찰 10,681건, 입찰자 3,388명(Cartier 18/21/97건, Palm 95/54/194건, Xbox 35/21/93건, 각각 3/5/7일 경매). Palm 158: 경매 158건, 3,967행. Curve Clustering: 경매 149건, 3,166행, **판매자 71명** |
| 5. 형식 | CSV. Palm 158 파일에는 빈 열 10개가 붙어 있다 |
| 6. 주요 컬럼 | 표준 `auctionid, bid(proxy bid), bidtime(시작 후 일수), bidder, bidderrate, openbid, price(낙찰가)`. Kaggle본에는 `item, auction_type`이 추가돼 있다. Palm 158은 `Auction ID, Bid Amount, Bid Time & Date, Auction Start, Bidder ID, Bidder Rating`. Curve Clustering은 `… Closing Price, Opening Bid, Seller, Seller Rating, # Bids, End Date` |
| 7. 실제/합성 | 실데이터(eBay 입찰 이력) |
| 8. 종료 시각 관련 컬럼 | 표준 파일은 **상대 시간**이라 "마감 몇 분 전" 계산만 된다. Palm 158은 **절대 시각**(`%b-%d-%y %H:%M:%S`, 파싱 실패 0건)이고 종료는 시작+7일로 추정했다. 추정 종료 이후 입찰이 0건이고, 최대 입찰 시각이 최대 추정 종료와 정확히 같다는 것이 근거다. **시간대는 표기가 없어 미확인**이다. Curve Clustering의 End Date는 날짜만 있다 |
| 9. 행동·경쟁 분석 | 가능하다. 입찰자의 24.0%가 2개 이상 경매에 참여했고 최대 24개였다. 품목을 넘나든 입찰자는 0명이다. **경매의 31.7%는 마지막 입찰이 마감 1분 이내, 72.5%는 1시간 이내**에 들어왔다. Palm 158에서는 ±1시간 안에 함께 끝난 경매 수가 평균 0.35건(최대 2건)이라, 공급 충돌의 변동 폭이 매우 작다 |
| 10. ML 학습 가능성 | 낮음~중간. 628건이면 GLM 수준이고, 절대 시각이 있는 경매는 158건뿐이다 |
| 11. 대표성·편향 | 2003년 전후 eBay 3개 품목이다. Xbox(당시 현행 게임기)와 Cartier(고가 시계)가 수집품에 가까운 정도다. 158건은 전수가 아니라 표본이므로 동시 경쟁 경매 수가 과소 측정된다 |
| 12. 라이선스 | **명시 없음**. 사이트에 "© Jank and Shmueli" 표기만 있고, Kaggle 원본은 "Unknown"이다. 재업로드본(noeyislearning)의 CC0 표기는 재업로더가 단 것이라 근거가 되지 못한다. 연구·재배포·상업 이용 조건 모두 **미확인** |
| 13. 실제 검증 | **[직접 검증]** Drive 14개 파일, Kaggle 원본, GitHub 미러 2곳 모두 확인했다. Kaggle `auction.csv`는 Drive 9개 파일과 경매 ID 집합이 정확히 같다 |

#### (2) MaxSold 경매·물품·입찰 데이터 (Hugging Face `jpearce610`)

| 항목 | 내용 |
|---|---|
| 1. 이름·출처 | "maxsold-auction-data", "maxsold-item-data", "MaxSold Bid History Dataset"(metadata 기준). 업로더 jpearce610이 MaxSold에서 수집한 것으로 보이며, **MaxSold 공식 배포는 아니다** ([HF auction_data](https://huggingface.co/datasets/jpearce610/auction_data), [HF bid_data](https://huggingface.co/datasets/jpearce610/bid_data), [HF item_data](https://huggingface.co/datasets/jpearce610/item_data)) |
| 2. 접근 경로 | parquet 파일을 `resolve/main/...`로 로그인 없이 받을 수 있다(auction 9.7MB, bid 286MB, item 306MB). 행 단위 JSON은 datasets-server rows API로 받는다 |
| 3. 연도·기간 | HF 업로드 2026-01~02. 직접 집계한 종료 시각 범위는 **2015-03 ~ 2026-02-03**(2021년 3,520건, 2025년 2,887건, 2026년 103건) |
| 4. 규모 | 경매 24,621행(17열), 물품 3,033,289행, 입찰 33,593,686행 ([bid_data metadata](https://huggingface.co/datasets/jpearce610/bid_data/resolve/main/metadata.json)) |
| 5. 형식 | Parquet. enriched_*(LLM 기반 물품 속성)와 engineered_*(파생 피처, UTC 'Z'로 정규화)도 별도로 있다 |
| 6. 주요 컬럼 | 경매 테이블: `auction_starts, auction_ends, auction_last_item_closes, auction_extended_bidding(_interval/_threshold), auction_item_count, auction_total_viewed, auction_total_winning_price, auction_total_bid_count`. 물품 테이블: `item_viewed, item_starting_bid, item_current_bid, item_end_time, item_bid_count, item_bidding_extended`. 입찰 테이블: `bid_time, bid_amount, bid_is_proxy` ([first-rows](https://datasets-server.huggingface.co/first-rows?dataset=jpearce610/auction_data&config=default&split=train)) |
| 7. 실제/합성 | 실데이터. 단, enriched_item_data의 속성은 AI가 생성했다고 명시돼 있다 |
| 8. 종료 시각 관련 | **절대 시각, 초 단위, UTC offset 포함.** 종료 시각은 **19–21시가 97.6%**이고, 분은 :00/:15/:30/:45뿐이다. 플랫폼이 정한 슬롯으로 보인다. 요일은 목 8,167건, 수 5,759건 순이고 토요일은 684건이다. 기간 중앙값은 171.5시간이며 **24–72시간 경매는 0.9%**다. 마지막 물품 마감은 예정 종료보다 중앙값 21분 늦다(연장 입찰 효과) |
| 9. 행동·경쟁 분석 | 공급 밀집도는 계산할 수 있다. UTC 시간 슬롯당 평균 3.72건, 최대 24건이고, **경매의 53.1%가 다른 경매 5건 이상과 같은 슬롯을 공유**한다. 반면 입찰자 ID가 없어서 경매 사이를 오가는 구매자는 추적할 수 없다 |
| 10. ML 학습 가능성 | 규모로는 공개 데이터 중 최고다(물품 300만 개, 조회·입찰·가격 라벨). 그러나 종료 시각의 분산이 매우 작아 "종료 시각 → 성과" 효과를 식별하는 힘은 낮다 |
| 11. 대표성·편향 | 캐나다(온타리오 GTA 중심) 이사·유품 정리(estate) 묶음 경매이고, 6–7일 경매다. 수집품 C2C와 다르다. 이 계산 결과는 경매 23,121건, 즉 93.9% 표본 기준이다(rows API 15페이지 실패) |
| 12. 라이선스 | **불확실.** 아래 2.4절에서 따로 정리했다 |
| 13. 실제 검증 | 경매 테이블은 **[직접 검증]**(93.9%), 물품은 무작위 3,000행 **[직접 검증]**, 입찰 테이블은 **[부분 확인]**(pyarrow가 없어 286MB 파일을 집계하지 못함) |

#### (3) Swoopo 페니옥션 데이터셋 (Byers, Mitzenmacher, Zervas)

| 항목 | 내용 |
|---|---|
| 1. 출처 | Boston University, [Swoopo Dataset 페이지](https://people.bu.edu/zg/swoopo.html). 관련 논문은 arXiv 1001.0592 ([PDF](https://arxiv.org/pdf/1001.0592)) |
| 2. 접근 | `swoopo-dataset.tar.gz`(29,654,013 bytes)를 로그인 없이 받았다 |
| 3. 기간 | outcomes 종료 시각 2008-08-20 ~ 2009-12-12, traces 2009-10-01 ~ 2009-12-12 (직접 집계). 논문 요약은 "121,419건, 2008-09-08부터"라고 적고 있어 직접 집계와 조금 다르다 |
| 4. 규모 | outcomes 121,470행(형식 불량 102행, 시각 파싱 성공 121,368건). traces는 입찰 2,049,972건, 경매 7,353건, 입찰자 60,537명 |
| 5. 형식 | TSV 2개와 README |
| 6. 주요 컬럼 | outcomes `auction_id, product_id, retail, finalprice, bidincrement, bidfee, winner, placedbids, endtime_str, flg_*`. traces `bid_time, bid_ct(카운트다운 잔여 초), bid_user, bid_butler, bid_final` 등 |
| 7. 실제/합성 | 실데이터(저자들이 라이브 경매를 관측해 기록) |
| 8. 종료 시각 관련 | `"19:52 PDT 09-16-2008"` 형식의 **분 단위 절대 시각**이다. **121,368건 모두 "PDT" 라벨**이 붙어 있어 겨울철(PST 기간)에도 PDT로 표기된다. 그래서 실제 시간대가 모호하다. 종료 시각 분포는 거의 평탄하다(시간대별 최소 4,281건, 최대 6,288건) |
| 9. 행동·경쟁 분석 | 입찰자 ID와 초 단위 입찰 시각이 있어 시간대별 활동량과 경매 간 입찰자 이동을 분석할 수 있다(약 10주 분량). 같은 product_id 경매와 같은 시간대에 끝나는 비율은 8.0%다 |
| 10. ML | 규모는 충분하다(경매 12만 건, 입찰 205만 건) |
| 11. 편향 | **입찰할 때마다 카운트다운이 연장되므로 종료 시각이 내생적으로 정해진다.** 판매자가 고르는 고정 마감과 구조가 근본적으로 다르다. 경품형 전자제품 중심이고 입찰 수수료 구조도 특이하다. README는 2010-03-21 이전 판의 `*_secs_added` 값에 오류가 있다고 경고한다 |
| 12. 라이선스 | **명시 없음**(저자 문의 안내만 있음). 재배포·상업 이용 조건은 **미확인** |
| 13. 실제 검증 | **[직접 검증]** 전체 파일을 받아 집계했다 |

#### (4) eBayAuctions.csv ("Competitive auctions on eBay", DMBA 교재)

| 항목 | 내용 |
|---|---|
| 1. 출처 | Shmueli, Bruce, Gedeck et al. 데이터마이닝 교재. 패키지 저장소는 `gedeck/dmba`, `mlba-python`, R `mlba`다 ([R 문서](https://github.com/gedeck/mlba/blob/main/mlba/man/eBayAuctions.Rd)) |
| 2. 경로 | [eBayAuctions.csv.gz](https://raw.githubusercontent.com/gedeck/dmba/master/src/dmba/csvFiles/eBayAuctions.csv.gz). 압축하지 않은 경로는 404다 |
| 3. 기간 | 데이터 "© 2016". 저자 문서에 따르면 **2004년 5–6월** eBay 거래다 ([gedeck ch01.qmd](https://github.com/gedeck/ai-assisted-statistics-for-data-scientists/blob/main/code/R/ch01.qmd)) |
| 4. 규모 | 1,972행 8열. **완전 중복 행이 346개라 고유 행은 1,626개**다 |
| 5. 형식 | CSV(gzip) |
| 6. 컬럼 | `Category(18종), currency(US/EUR/GBP), sellerRating, Duration(1/3/5/7/10일), endDay(요일), ClosePrice, OpenPrice(USD 환산), Competitive?(입찰 2건 이상이면 1)` |
| 7. 실제/합성 | 실데이터를 경매 단위로 요약한 것 |
| 8. 종료 시각 관련 | **종료 요일만 있다.** 시·분·날짜가 없고, 요일의 기준 시간대도 미확인이다. 중복을 제거하지 않은 경쟁 비율은 월 0.673, 토 0.427이다 |
| 9. 행동·경쟁 분석 | 불가능하다. 경매 ID, 판매자 ID, 입찰자 ID가 모두 없다 |
| 10. ML | 소규모 분류 baseline 정도다. **중복을 먼저 제거하지 않으면 무작위 분할에서 누수가 생긴다** |
| 11. 편향 | 2004년 데이터이고 여러 통화가 섞여 있다. 카테고리 샘플링 방식은 미확인이다 |
| 12. 라이선스 | 저장소마다 표기가 다르다. dmba와 mlba-python은 MIT, R mlba는 GPL이고, 데이터 자체에는 "Copyright 2016 Galit Shmueli and Peter Bruce"가 붙어 있다. 저장소 라이선스가 데이터에도 적용되는지는 불명확하다 ([LICENSE](https://github.com/gedeck/dmba/blob/master/LICENSE)) |
| 13. 실제 검증 | **[직접 검증]** Kaggle 재업로드본(CC0 표기)과 내용이 같음을 확인했다 |

#### (5) UCI Shill Bidding Dataset (#562)

| 항목 | 내용 |
|---|---|
| 1. 출처 | UCI ML Repository, Alzahrani & Sadaoui ([UCI](https://archive.ics.uci.edu/dataset/562/shill+bidding+dataset), [arXiv 1806.00656](https://arxiv.org/abs/1806.00656v1)) |
| 2. 경로 | [zip](https://archive.ics.uci.edu/static/public/562/shill+bidding+dataset.zip), DOI 10.24432/C5Z611 |
| 3. 기간 | UCI 기증 2020-03. 논문에 따르면 2017년 3–6월 eBay iPhone 7 경매를 수집했다 |
| 4. 규모 | 6,321행 13열, 경매 807건. (경매, 입찰자) 쌍이 한 행이다 |
| 5. 형식 | zip 안의 CSV |
| 6. 컬럼 | `Bidder_Tendency, Bidding_Ratio, Successive_Outbidding, Last_Bidding, Auction_Bids, Starting_Price_Average, Early_Bidding, Winning_Ratio`(모두 0–1 정규화), `Auction_Duration`, `Class` |
| 7. 실제/합성 | 실데이터에서 만든 **파생·정규화 특징** |
| 8. 종료 시각 관련 | **없음.** Last_Bidding(기간의 90% 이후)과 Early_Bidding(기간의 25% 이내)은 상대 시점을 정규화한 값이다 |
| 9. 행동·경쟁 분석 | 사실상 불가능하다. Bidder_ID가 `x***y` 형태로 100% 마스킹돼 있어서, 계산상 나오는 "입찰자 73.8%가 여러 경매 참여"는 신뢰할 수 없는 상한값이다 |
| 10. ML | 사기 탐지 분류용이다. Class는 클러스터링 기반 반자동 라벨이다 |
| 11. 편향 | 단일 상품(iPhone 7)이다 |
| 12. 라이선스 | **CC BY 4.0**(UCI 메타데이터). 연구·재배포·상업 이용이 가능하고 출처 표기 의무가 있다 |
| 13. 실제 검증 | **[직접 검증]** |

#### (6) GSA 미국 정부 잉여물자 경매 (HF 아카이브 + 공식 API)

| 항목 | 내용 |
|---|---|
| 1. 출처 | GovAuctions.app이 정리한 [HF govauctions/us-gsa-surplus-auctions](https://huggingface.co/datasets/govauctions/us-gsa-surplus-auctions), GSA 공식 [Auctions API](https://gsa.github.io/auctions_api/fields) |
| 2. 경로 | HF CSV(2,442,264 bytes). API는 `api.gsa.gov/assets/gsaauctions/v2/auctions`이며 공개 DEMO_KEY로 호출에 성공했다 |
| 3. 기간 | HF 아카이브는 종료일 2026-05-06 ~ 2026-10-08이고 월간 갱신된다. API는 현재 진행 중이거나 예정된 경매만 준다 |
| 4. 규모 | HF 13,837 lot(16열). API 1,060 lot(2026-10-30 기준) |
| 5. 형식 | CSV/JSON, API는 JSON/XML |
| 6. 컬럼 | HF `category, condition, state, current_or_final_bid, bid_count, sold, ended_at`. API `aucStartDt, aucEndDt, biddersCount, highBidAmount, inactivityTime` 등 34개 |
| 7. 실제/합성 | 실데이터 |
| 8. 종료 시각 관련 | **날짜만 있다**(UTC). 시(hour) 단위 분석은 할 수 없다 |
| 9. 분석 | 날짜 단위 공급 밀집은 분석할 수 있다. **같은 종료일에 같은 카테고리 lot이 10개 이상인 경우가 90%**다. 수·화요일에 몰리고 토·일요일은 22건뿐이다 |
| 10. ML | 약하다(입찰 로그 없음, bid_count 중앙값 1) |
| 11. 편향 | B2G 잉여물자(차량, 중장비)이고 collectibles 카테고리는 1건이다. API 응답에는 계약담당관 이름·이메일·전화가 들어 있다 |
| 12. 라이선스 | HF 아카이브는 **CC BY 4.0**. API 이용조건 세부는 **미확인** |
| 13. 실제 검증 | HF는 전체 **[직접 검증]**, API는 현재 스냅샷 **[직접 검증]**. Kaggle 사본은 메타데이터만 봤다 |

#### (7) NBER eBay Best Offer Bargaining Data (Backus, Blake, Larsen, Tadelis)

| 항목 | 내용 |
|---|---|
| 1. 출처 | [NBER 데이터 페이지](https://www.nber.org/research/data/best-offer-sequential-bargaining). eBay가 연구용 공개를 승인했고 PII를 제거했다 |
| 2. 경로 | `anon_bo_lists.csv.gz`, `anon_bo_threads.csv.gz`, `bargaining_data.zip`(약 5.9GB), [Codebook.xlsx](https://nber.org/bargaining/Codebook.xlsx) |
| 3. 기간 | 2012-05-01 ~ 2013-06-01 |
| 4. 규모 | listing 약 9,800만 건 |
| 5. 형식 | gzip CSV |
| 6. 컬럼 | lists `anon_slr_id, auct_start_dt, auct_end_dt, view_item_count, wtchr_count, meta_categ_id, item_price`. threads `anon_byr_id, offr_price, src_cre_date, response_time` 등. Collectibles, Toys & Hobbies, Video Games, Sports Mem Cards 카테고리가 있다 |
| 7. 실제/합성 | 실데이터(익명화) |
| 8. 종료 시각 관련 | listing 시작·종료는 **날짜(str9)**만 있다. 제안 시각은 초 단위지만 시간대가 표기되지 않았다 |
| 9. 분석 | 구매자 활동의 시간대 곡선을 추정할 수 있다. 앞부분 13,581건 표본에서 0–3시는 낮고(178–219건) 10–20시는 높았다(약 650–808건). 단, 판매자 순으로 정렬된 편향 표본이다 |
| 10. ML | 규모는 매우 크지만 **경매가 아니라 고정가+흥정** 데이터다 |
| 11. 편향 | 2012–13년 미국 eBay |
| 12. 라이선스 | "research purposes", QJE 2020 인용 필수. 상업 이용은 **불명확** |
| 13. 실제 검증 | **[부분 확인]** 코드북과 두 파일의 앞 400KB만 봤다 |

#### (8) ShopGoodwill 낙찰 경매 (GitHub `silentdirectivellc-hub/ebay-sold-comps`)

처음 조사에서는 찾지 못했고, 사용자가 저장소를 알려 준 뒤 2026-10-30에 저장소 전체(zip)를 내려받아 12개 `goodwill-*.csv`를 스크립트로 집계했다.

| 항목 | 내용 |
|---|---|
| 1. 출처 | GitHub [silentdirectivellc-hub/ebay-sold-comps](https://github.com/silentdirectivellc-hub/ebay-sold-comps). 업로더는 가격 가이드 사이트(flipworth.silentdirectivellc.com)를 운영하는 업체로 보인다. 원천은 shopgoodwill.com의 로그인 없는 buyer API라고 README에 적혀 있다 |
| 2. 접근 | `data/goodwill-*.csv`. 저장소 zip: `https://codeload.github.com/silentdirectivellc-hub/ebay-sold-comps/zip/refs/heads/main` |
| 3. 연도·기간 | 저장소 생성 2026-09-19. 종료 시각 2026-06-20 ~ 2026-09-19. 키워드마다 최신 N건을 한 번 수집한 것이라 **파일마다 창이 1–3일**(일부 낚시용품은 수 주) |
| 4. 규모 | 12개 파일 2,678행. 낚시 계열 파일끼리 겹쳐 (title, ended_at, price) 완전 중복 96행 → 약 2,582건. 판매자 144명, 상위 5명이 25.6%. README 표는 6개 파일 1,926행만 적고 있어 실제 파일 수(12개)와 다르다 |
| 5. 형식 | CSV (UTF-8) |
| 6. 컬럼 | `item_id, title, sold_price_usd, bids, ended_at, seller_id, category, keyword`. seller_id는 지역 Goodwill 매장 번호. LEGO 파일 438행은 item_id·category·keyword가 비어 있음 |
| 7. 실/합성 | 실데이터. README에 "Nothing simulated"라고 적혀 있고, 행 내용(실제 상품명, 불규칙한 분 단위 시각)도 그에 부합한다. 원 리스팅과 대조하지는 않았다 |
| 8. 종료 시각 추천에 쓸 컬럼 | `ended_at`(초까지 표기, 실질적으로 분 단위), `bids`, `sold_price_usd`, `seller_id`, `category`. **시간대 표기 없음**(UTC인지 태평양 시간인지 미확인). 종료 시각의 79.7%가 18–20시, 43.8%가 18시에 몰려 있다. 시간대를 알아야 이 집중을 해석할 수 있다. **시작 시각과 경매 기간이 없다** |
| 9. 행동·경쟁 분석 | 입찰자 ID와 개별 입찰이 없어 구매자 행동은 분석할 수 없다. 공급 경쟁은 계산할 수 있다. 같은 키워드에서 ±30분 안에 끝나는 다른 경매 수의 중앙값은 LEGO 117건, 의류 장신구 57건, 필름카메라 27건, 낚시용품 0–4건으로 **밀집도 변동이 크다**. 판매자 ID가 있어 판매자 고정효과를 넣을 수 있다 |
| 10. ML | 2,600건 안팎이라 Poisson/NB GLM, 판매자·카테고리 랜덤효과 모형에 적당하다. 부스팅의 이득은 기대하기 어렵다. 키워드별 수집 창이 짧아 시간대 효과와 수집 시점이 섞인다 |
| 11. 편향·누락 | **낙찰된 경매만 있다**(bids=0 행이 0개) → 유찰률은 모델링할 수 없고 생존 편향이 있다. 1입찰 낙찰이 29.2%. 요일 분포(토 816, 월 634, 일 496)는 수집일(2026-06-20 토 ~ 06-22 월)에서 생긴 인공물이다. 미국 Goodwill 매장이 판매자라 개인 C2C 수집품 시장과 다르다. 품목은 LEGO·레코드·카메라·시계·장신구·낚시용품이고 TCG·피규어는 없다 |
| 12. 라이선스 | 저장소 LICENSE는 **CC0 1.0**(업로더 표기). 그러나 원 데이터는 ShopGoodwill 플랫폼의 것이고, ShopGoodwill 이용약관이 자동 수집·재배포를 허용하는지는 **미확인**이다(robots.txt `Crawl-delay: 120`). MaxSold와 같은 이유로 "업로더 표기 CC0, 원 플랫폼 약관 미확인 → 불확실"로 본다. 같은 저장소의 eBay 570행은 제3자 스크래핑 도구로 수집됐다고 METHOD.md에 적혀 있어 eBay 약관과 충돌할 소지가 크다 |
| 13. 실제 검증 | **[직접 검증]** 저장소 전체를 내려받아 README·METHOD·LICENSE와 12개 CSV를 열고 행 수, 판매자 수, 종료 시각 분포, 동시 종료 밀집도, 중복을 집계했다 |

#### (9) 기타 후보: 보조용이거나 사용 불가

| 데이터셋 | 출처·접근 | 기간·규모·형식 | 시간 컬럼 | 실/합성 | 분석·ML·편향 | 라이선스 | 검증 |
|---|---|---|---|---|---|---|---|
| Mario Kart Wii eBay (OpenIntro `mariokart`) | [CSV](https://www.openintro.org/data/csv/mariokart.csv), [문서](https://rdrr.io/cran/moderndive/man/mario_kart_auction.html) | 수집 연도 미확인. 143행 CSV | duration(일)만, 종료 시각 없음 | 실데이터 | 레트로게임에 가깝지만 종료 시각이 없음. 수업용 | OpenIntro(CC BY-SA로 알려짐, **미확인**) | [직접 검증] |
| Pokémon Card Sold-Price Reference | [Kaggle ryanheger](https://www.kaggle.com/datasets/ryanheger/pokemon-card-sold-price-reference), [HF rrhagentbiz](https://huggingface.co/datasets/rrhagentbiz/pokemon-card-sold-price-reference) | 2026, 카드 508장, CSV 44KB | 없음 | 실제 eBay 판매가의 **중앙값 집계** | "유사 상품 기준가" 피처로만 쓸 수 있음 | CC BY 4.0 | [직접 검증]. 두 사본이 같은 데이터인지는 미확인(둘 다 508장) |
| Mercari MerRec (KDD 2025) | [HF](https://huggingface.co/datasets/mercari-us/merrec) | 2023년 6개월, 12.7억 행 parquet | stime(이벤트), 시간대 미확인 | 실데이터(익명) | 고정가 C2C. 시간대별 조회 활동 분포 참고용 | **CC BY-NC 4.0** | [부분 확인](first-rows) |
| Copart (rebrowser) | [Kaggle](https://www.kaggle.com/datasets/rebrowser/copart-dataset) | 무료 표본 26,600행. 전체 유료 | saleDate, saleTime, saleTimeZone | 실데이터 | highBid 100% 마스킹. 라이브 일정 경매 | CC BY-NC 4.0 | [직접 검증](표본) |
| Copart/IAAI (dominiklavcel) | [Kaggle](https://www.kaggle.com/datasets/dominiklavcel/copart-and-iaai-car-auctions-dataset) | 590MB CSV, 2025-12~2026-03 | sale_date `'03/11/2026 14:00 UTC'` | 실데이터(제3자 수집) | 입찰 수 없음. YOLO .pt 파일이 동봉돼 있어 열지 않음 | Unknown | [부분 확인](앞 257행) |
| Steam Market CS:GO | [Kaggle](https://www.kaggle.com/datasets/leawind/steam-market-price-dataset-csgo) | 241MB, 아이템 20,575개 | timestamp(ms), 경매 아님 | 실데이터 | 시세·거래량만 있음 | Unknown | [부분 확인](파일 1개) |
| TCGapi/tcg-price-history | [HF](https://huggingface.co/datasets/TCGapi/tcg-price-history) | README는 "100K<n<1M"이지만 실제 파일은 **5행짜리 sample.json** | date(일별) | 첫 행이 `example-charizard-base` → **예시·홍보용** | 사용 불가 | MIT | [직접 검증] |
| DMC 2006 (eBay 매출 예측) | [Kaggle 사본](https://www.kaggle.com/api/v1/datasets/view/oscarm524/prediction-of-auction-sales), [DMC](https://www.data-mining-cup.com/reviews/dmc-2006/) | 미확인 | **미확인** | 미확인 | 미확인 | CC0 표기(재업로더) | [웹 페이지만] |
| USA online auctions 2019 | [Kaggle](https://www.kaggle.com/api/v1/datasets/view/shaswat1/usa-online-auctions-2019) | 이벤트 단위 집계 | 미확인 | 실데이터로 보임 | 입찰 단위가 아님 | CC BY-NC-SA 4.0 | [웹 페이지만] |
| 온비드 OpenAPI (한국자산관리공사) | [data.go.kr 15157222](https://www.data.go.kr/data/15157222/openapi.do), [15157220](https://data.go.kr/catalog/15157220/openapi.json) | 매시간 갱신 | 문서상 입찰 시작·종료 일시와 개찰일시가 있음. **실제 필드는 미확인** | 실데이터 | 봉인입찰 공매라 구조가 다름 | 이용허락 제한 없음(문서상) | **미확인**(서비스키 발급 필요) |
| 온비드 용도별 통계 | [data.go.kr 15054750](https://www.data.go.kr/catalog/15054750/fileData.json) | 2013–2025 연간 CSV | 없음(연간 집계) | 실데이터 | 입찰참가자수·경쟁률 집계뿐 | 제한 없음 | [웹 페이지만] |

### 2.3 "Goodwill" 데이터셋 정정과 사용할 수 없는 후보

**정정: "Goodwill" 데이터는 존재한다.** 처음 조사에서는 찾지 못했지만, 사용자가 알려 준 GitHub `silentdirectivellc-hub/ebay-sold-comps` 저장소에 ShopGoodwill 낙찰 경매 CSV 12개가 있었다. 직접 내려받아 검증한 결과는 2.2절 (8)에 정리했다. 처음 조사가 놓친 이유는 이 저장소가 2026-09에 만들어졌고, 저장소 이름이 "ebay"로 시작하며, Kaggle·Hugging Face에 등록되지 않았기 때문으로 보인다. 아래는 처음 조사의 검색 기록이다. 다른 경로에서 찾은 것이 도구뿐이었다는 점은 그대로 유효하다.

처음 조사의 검색 기록: Kaggle API에서 `search=shopgoodwill`과 `search=goodwill+auction` 검색 결과는 0건이었다 ([Kaggle API 검색](https://www.kaggle.com/api/v1/datasets/list?search=shopgoodwill)). 이름이 비슷한 `jamesbond64/goodwill`은 기부·환경영향 엑셀 두 개뿐이다 ([파일 목록](https://www.kaggle.com/api/v1/datasets/list/jamesbond64/goodwill)). GitHub에서 나온 것은 스크립트, 스나이핑 툴, API 래퍼 같은 도구뿐이었다 ([scottmconway/shopgoodwill-scripts](https://github.com/scottmconway/shopgoodwill-scripts)). Apify의 유료 스크래퍼 문서에는 endTime(UTC)과 numBids 필드가 있다고 적혀 있다 ([Apify](https://apify.com/automation-lab/shopgoodwill-scraper)). 하지만 이것은 데이터셋이 아니라 수집 도구다. ShopGoodwill robots.txt는 `Crawl-delay: 120`이고 이용약관의 수집 조항은 미확인이다 ([robots.txt](https://shopgoodwill.com/robots.txt)). 해커톤 저장소 `7thcapitalist/Hackhaton`의 shopgoodwill fixture CSV는 실데이터인지 합성인지 확인하지 않았다 ([GitHub](https://github.com/7thcapitalist/Hackhaton)). 처음 보고서는 이 결과만 보고 "Goodwill 데이터셋 제안은 혼동이나 환각일 가능성이 높다"고 판단했는데, **이 판단은 틀렸으므로 철회한다.**

사용 불가로 분류한 것은 다음과 같다. `keywordbarrage/ebay-scraper`(HF)는 데이터 파일 없이 봇 탐지 우회를 홍보하는 유료 스크래핑 광고라 사용하지 않기를 권한다. TCGapi는 예시 5행뿐이다. 입찰 로그가 있다고 보고된 DealDash 트레이스(경매 134,568건, 입찰 1.74억 건, [논문 PDF](https://www.cs.uchicago.edu/~ravenben/publications/pdf/auction-ht18.pdf)), Augenblick(2016)의 Swoopo 대규모 데이터([RePEc](https://ideas.repec.org/a/oup/restud/v83y2016i1p58-86..html)), BigDeal 페니옥션 데이터는 **공개 여부를 확인하지 못했다**. ADAPT(AAAI 2024) 저장소에는 코드만 있고 데이터는 없다 ([GitHub](https://github.com/YogaWang7/ADAPT)). Bring a Trailer, Catawiki, 야후옥션, Taobao 사법경매, PSA·Goldin·Heritage 결과 아카이브, 번개장터·중고나라·당근은 공개 정적 데이터셋을 찾지 못했다. 유료 Apify 스크래퍼만 있었고, 이를 이용하면 약관 위반 소지가 있다.

### 2.4 노트 간 충돌 정리: MaxSold 라이선스는 "불확실"이 정답이다

**MaxSold(`jpearce610/auction_data`) 라이선스와 출처.** 한 노트는 "HF 태그에 license 없음, 플랫폼 불명(MaxSold류 추정)"이라고 적었다. 다른 노트는 "MaxSold, 업로더 metadata에 `cc-by-4.0`"이라고 적었다. 두 기록은 서로 다른 위치를 본 것이라 둘 다 맞다. Hugging Face 데이터셋 카드 태그에는 라이선스가 없다. 반면 저장소 안의 `metadata.json` 파일에는 업로더가 `"license": "cc-by-4.0"`이라고 적어 두었다 ([metadata.json](https://huggingface.co/datasets/jpearce610/auction_data/resolve/main/metadata.json)). 같은 메타데이터의 데이터셋 이름이 "maxsold-auction-data"이므로 출처 플랫폼은 MaxSold로 보는 것이 타당하다. 그러나 **원저작물은 MaxSold 플랫폼의 데이터이고, MaxSold 이용약관이 수집과 재배포를 허용하는지는 미확인**이다. 업로더 한 사람의 CC BY 4.0 표기는 원권리자의 허락을 대신하지 못한다. 그래서 이 보고서는 라이선스를 "업로더 표기 CC BY 4.0, 원 플랫폼 약관 미확인 → 불확실"로 적는다. 비영리 캡스톤 분석에 쓰더라도 재배포와 상업 이용은 하지 않기를 권한다. 수집 기간도 노트마다 다르다. 한 노트는 "첫 행 2015-03, 전체 기간 미확인"이고 다른 노트는 93.9% 표본으로 2015-03 ~ 2026-02-03을 집계했다. 후자를 채택한다.

**그 밖의 충돌.** 수집품 노트는 "Kaggle은 로그인 없이 받을 수 없어 미확인"이라고 적었다. 다른 두 노트는 Kaggle 공개 API(`/api/v1/datasets/download/...`)로 로그인 없이 실제 파일을 받았다. 실제 다운로드 기록을 채택한다. 문헌 노트가 2차 자료로 인용한 "Cartier 1,953건, Palm 5,917건, Xbox 2,811건"은 경매 수가 아니라 **입찰 수**다. 직접 집계한 3/5/7일 파일 입찰 수의 합과 정확히 일치한다. UCI Shill의 라이선스와 기간을 "미확인"으로 적은 노트도 있었지만, UCI 메타데이터(CC BY 4.0)와 원 논문(2017년 3–6월)으로 확인됐다. Bimpikis et al.의 추천 시스템 효과는 방법론 노트에 "약 3%", 문헌 노트에 "1.6%"로 적혀 있다. 전문을 읽은 working paper PDF는 1.6%이고, 약 3%는 구버전 요약에 나온 수치다. 출판본의 정확한 수치는 미확인이다 ([Stanford PDF](https://stanford.edu/~kostasb/papers/managing_market_thickness.pdf), [SUFE 요약](https://academicnewsletter.sufe.edu.cn/info/390869)). Einav et al.(2015)이 종료 시각을 다뤘는지에 대해 방법론 노트는 "미확인"이라고 했다. 그러나 문헌 노트가 전문 4.D절에서 종료 시각과 요일 변이 분석을 확인했으므로 이를 채택한다.

## 3. 가장 유용한 데이터셋 TOP 3

**1위: Jank & Shmueli eBay 입찰 이력, 특히 Palm 7일 158건 + Curve Clustering 파일.** 메커니즘이 LAYER7에 가장 가깝다. eBay는 C2C, 고정 마감(hard close), proxy bidding 구조다. **절대 시각, 입찰자 ID, 같은 상품의 동시 경매**를 한 번에 볼 수 있는 공개 데이터는 이것뿐이다. 표준 파일에는 LAYER7의 최대 기간과 같은 **3일(72시간) 경매가 148건**(Cartier 18, Palm 95, Xbox 35) 있다. 경매의 31.7%가 마감 1분 안에, 72.5%가 1시간 안에 마지막 입찰을 받았다는 사실은 "종료 순간 접속해 있는 구매자 수"를 추천 점수의 중심 변수로 삼을 근거가 된다. 입찰자 24%가 같은 품목의 여러 경매에 재등장한다는 사실은 대체 경매로 수요가 이동한다는 근거다. Curve Clustering 파일에는 판매자 ID(71명, 최다 판매자는 40건)가 있어 판매자 내 비교도 일부 할 수 있다. 한계도 크다. 절대 시각이 있는 경매는 158건뿐이고, 2003년 데이터이며, 시간대가 표기돼 있지 않다. 동시 종료 경매가 ±1시간 평균 0.35건이라 공급 충돌의 계수를 추정할 만한 변동이 없다. 라이선스도 명시돼 있지 않다.

**2위: ShopGoodwill 낙찰 경매(`ebay-sold-comps`).** 2026년 데이터이고 LEGO·레코드·필름카메라·시계처럼 **LAYER7 품목에 가장 가까운** 공개 경매 데이터다. 경매마다 실제 종료 시각, 입찰 수, 낙찰가, 판매자 ID가 함께 있다. 그래서 4.4절 점수식의 두 축을 실제로 맞춰 볼 수 있다. 하나는 종료 시간대별 입찰 수이고, 다른 하나는 같은 키워드 경매가 ±30분 안에 몇 건 끝나는지(LEGO 중앙값 117건, 낚시용품 0–4건으로 변동이 크다)다. 판매자 ID로 판매자 고정효과를 넣으면 "숙련 판매자가 좋은 시간대를 고른다"는 교란도 일부 통제할 수 있다. 치명적인 한계는 다섯 가지다. ① **낙찰된 경매만 있어** 유찰 위험을 추정할 수 없다. ② 시간대 표기가 없어 18–20시 집중(79.7%)이 미국 저녁인지 UTC 오전인지 모른다. ③ 시작 시각과 기간이 없어 24–72시간 조건을 점검할 수 없다. ④ 키워드마다 1–3일 창만 수집해 요일·시간대 효과와 수집 시점이 섞인다. ⑤ 원 플랫폼 약관은 미확인이다. 따라서 **시간대별 입찰 수와 공급 밀집의 관계를 탐색하는 데만** 쓴다. 여기서 나온 밀집 수치(LEGO 117건 같은 값)나 회귀 계수를 추천 점수의 가중치로 옮기지 않는다. 표본이 특정 키워드와 짧은 수집 기간에 몰려 있어 플랫폼 전체의 경쟁 수준을 대표하지 않기 때문이다. 인과 추정이나 유찰 모델에도 쓰지 않는다.

**3위: MaxSold.** 절대 시각(UTC offset 포함), soft close 설정, 물품 300만 개의 조회·입찰·가격을 함께 가진 유일한 대규모 공개 데이터다. 공급 밀집 피처(같은 슬롯에서 끝나는 경매 수)를 실제로 계산해 성과와 연결할 수 있다. **경매의 53.1%가 다른 경매 5건 이상과 종료 슬롯을 공유**하므로 밀집도의 변동도 Palm 158보다 훨씬 크다. 연장 입찰 때문에 실제 마감이 예정보다 중앙값 21분 늦다는 점은, LAYER7이 soft close를 도입하면 "종료 시각"이 범위 개념으로 바뀐다는 것을 보여준다. 한계는 치명적이다. 종료 시각을 플랫폼이 19–21시 슬롯으로 정해 **시간대 효과를 식별할 변동이 거의 없다**. 6–7일 묶음 유품 경매라서 24–72시간 경매는 0.9%뿐이다. 입찰자 ID가 없고 라이선스도 불확실하다.

**참고(4위): Swoopo traces.** 입찰자 60,537명의 초 단위 입찰 기록으로 **시간대별 구매자 활동 곡선**과 동시 경매 사이의 구매자 이동을 직접 추정할 수 있다. outcomes의 종료 시각은 하루 전체에 거의 고르게 퍼져 있어, 종료 시각 변동이 적은 MaxSold와 상호 보완된다. 그러나 페니옥션은 입찰할 때마다 마감이 연장되므로 "종료 시각 → 성과" 관계를 LAYER7에 옮길 수 없다. "PDT" 라벨이 연중 고정돼 있어 시간대가 모호하고 라이선스도 명시돼 있지 않다. 그래서 활동 곡선의 **모양**을 사전값으로 쓰는 데 한정한다.

5위 이하인 eBayAuctions(DMBA)는 "요일이 경쟁 여부와 상관있다"는 거친 기준선과 수업용 분류 실습에만 쓸 수 있다. 중복 17.5%를 반드시 제거해야 한다. GSA 아카이브는 날짜 단위 공급 밀집의 사례로만 쓸 수 있다.

## 4. 추천 알고리즘 구현 전략

### 4.1 Bimpikis et al.이 증명한 것과 LAYER7이 빌리는 가설은 다르다

Bimpikis, Elmaghraby, Moon, Zhang(2020)은 Management Science 66(12):5783–5822에 실렸다. DOI는 10.1287/mnsc.2019.3497이다 ([EconPapers](https://econpapers.repec.org/RePEc:inm:ormnsc:v:66:y:12:i:2020:p:5783-5822)). 이 논문이 **실증적으로 증명한 것은 자연실험 하나**다. 미국 대형 소매업체의 반품·재고를 처분하는 B2B 경매 플랫폼에서, Market A가 iPhone 경매 종료일을 주 5일 균등 배치에서 화·목 두 날로 몰았다. 그러자 대조군 Market B 대비 **기기당 가격이 7.3% 올랐고(p<0.01) 경매당 입찰자가 0.49명 늘었다.** 입찰 금액 자체는 거의 변하지 않았으므로, 효과는 참여 증가에서 나왔다. 같은 날 Galaxy S3 경매가 한 건 늘 때마다 대당 최종가가 −$7.63 떨어졌다는 잠식 근거도 실증 결과다. 표본은 Market A 679건, Market B 497건(2013-02 ~ 2015-10)이고, 데이터는 **비공개(proprietary)**다 ([Stanford PDF](https://stanford.edu/~kostasb/papers/managing_market_thickness.pdf)). "시장 두께와 가격의 역U자 관계", "공급이 많으면 균등 배치가 최적", "추천 알림으로 그날 수익 +1.6%", "모든 입찰자에게 두께를 공개하면 −28.3%" 같은 결과는 다르다. 이들은 위험중립, 사적가치, 외생적 일일 방문 시각, 정상상태 신념 같은 가정을 둔 **구조모형의 반사실 시뮬레이션**이다.

| 구분 | 내용 | LAYER7에서의 위상 |
|---|---|---|
| 증명됨 (B2B, iPhone 로트) | 종료일을 모으면 참여가 늘고 가격이 오른다(+7.3%). 같은 날 대체재가 늘면 가격이 떨어진다 | 방향성을 시사하는 근거. 수치를 옮겨 쓰면 안 됨 |
| 모형 가정에 의존 | 역U자, 공급 수준별 최적 정책, 추천 +1.6%, 전면 공개 −28.3% | 가설 |
| LAYER7이 빌리는 가설 | 판매자 한 명이 24–72시간 안에서 고를 때 "활성 구매자가 많고 유사 경매 동시 마감은 적은 슬롯"이 유리하다 | **검증되지 않은 설계 가설** |
| 구조적 차이 | 논문은 플랫폼이 모든 경매의 종료일을 통제했다. LAYER7은 판매자가 고르고 시스템은 추천만 한다. 논문은 일 단위였고 LAYER7은 시간 단위다 | 식별 전략을 이전할 수 없음 |

full-information 정책이 역효과를 냈다는 시뮬레이션 결과는 LAYER7에 중요한 경고다. **모든 판매자에게 같은 TOP 3를 보여주면 플랫폼이 쏠림을 직접 만들어 낸다.** 그래서 4.5절의 순차 갱신과 4.6절의 최소 간격으로 쏠림을 줄인다. 무작위화는 평가 단계(6.4절)에서 더한다.

### 4.2 실증 문헌은 "저녁 마감이 좋다"는 통설을 지지하지 않는다

종료 시각 효과에 대한 eBay 실증은 엇갈린다. 가장 큰 규모로 잘 식별된 연구는 Einav, Kuchler, Levin, Sundaresan(2015, AEJ: Micro 7(2):215–247, DOI 10.1257/mic.20130046)이다. 같은 판매자가 같은 상품을 조건만 바꿔 올린 matched listings를 비교했고, 종료 시각 변이가 있는 세트 129,955개에서 **종료 요일 효과는 작고, 자정–오전 5시 마감만 약간 불리하며, 기간 효과도 작고 견고하지 않다**고 보고했다 ([Einav PDF](https://web.stanford.edu/~leinav/pubs/AEJmicro2015.pdf)). Simonsohn(2010, Management Science 56(7):1060–1073, DOI 10.1287/mnsc.1100.1180)은 반대 방향을 보여준다. 피크 입찰 시간대에 경매가 불균형하게 많이 마감되고, 그 시간대의 판매율과 가격은 더 낮았다. 전략적으로 시각을 고른 판매자일수록 피크에 몰렸다("competition neglect") ([IDEAS](https://ideas.repec.org/a/inm/ormnsc/v56y2010i7p1060-1073.html)). 기간 효과는 플랫폼마다 부호가 다르다. Haruvy & Popkowski Leszczyc(2010, DOI 10.1287/deca.1090.0149)의 현장실험에서 eBay는 긴 경매가 약 11% 높았지만 지역 사이트에서는 효과가 없거나 반대였다 ([EconPapers](https://econpapers.repec.org/RePEc:inm:ordeca:v:7:y:2010:i:1:p:99-106)). Lucking-Reiley et al.(2007)은 동전 경매 461건에서 긴 기간이 높은 가격과 연관됨을 보였다 ([IDEAS](https://ideas.repec.org/a/bla/jindec/v55y2007i2p223-233.html)). Roth & Ockenfels(2002, AER 92(4))는 고정 마감 eBay에서 막판 입찰이 연장 마감 Amazon보다 훨씬 많다고 보고했다 ([NBER w7729](https://nber.org/papers/w7729)). LAYER7의 마감 규칙(hard/soft close) 선택이 종료 시각의 의미 자체를 바꾼다는 뜻이다. eBay가 트레이딩카드 카테고리에서 extended bidding을 시험했다는 보도도 이 맥락에서 참고할 만하다 ([Cllct](https://www.cllct.com/sports-collectibles/auctions/ebay-testing-extended-bidding-for-trading-cards)).

구매자 집중과 공급 경쟁에 관한 문헌은 일관된 방향을 가리킨다. 구매자는 대체 가능한 동시·후속 경매를 넘나들며 입찰한다. Anwar, McMillan, Zheng(2006, European Economic Review)은 동시 경매에 교차 입찰한 낙찰자가 더 낮은 가격을 냈다고 보고했다 ([EconPapers](https://econpapers.repec.org/RePEc:wpa:wuwpmi:0505001)). Zeithammer(2006, JMR)는 같은 타이틀의 후속 경매가 있으면 현재 입찰이 낮아진다는 것을 eBay DVD 데이터로 보였다 ([Chicago Booth Review](https://www.chicagobooth.edu/review/strategic-bidding-ebay)). Pilehvar, Elmaghraby, Gopal(2017, Management Science, DOI 10.1287/mnsc.2016.2444)은 B2B 입찰자가 인근 유사 경매 가격에 반응한다고 보고했다 ([IDEAS](https://ideas.repec.org/a/inm/ormnsc/v63y2017i5p1493-1518.html)). 같은 흐름에 Peters & Severinov(2006)의 이론([IDEAS](https://ideas.repec.org/a/eee/jetheo/v130y2006i1p220-245.html)), Backus & Lewis(2025, RES, DOI 10.1093/restud/rdae031)의 동적 수요 추정([IDEAS](https://ideas.repec.org/a/oup/restud/v92y2025i2p837-872..html)), Hendricks & Sorensen의 겹치는 eBay 경매 동학([NBER w25002](https://www.nber.org/papers/w25002)), Coey, Larsen, Platt(2020, AER)의 마감 있는 구매자의 탐색([NBER PDF](https://nber.org/system/files/working_papers/w22038/w22038.pdf))이 있다. 이것이 "유사 경매 충돌 패널티"의 근거다. 다만 희소한 수집품은 iPhone이나 DVD보다 대체 가능성이 낮아 잠식이 더 약할 수 있다. **유사도를 어떻게 정의하느냐가 결과를 좌우한다.**

종료 시각 최적화와 스케줄링 연구는 드물다. **판매자 한 명의 종료 시각 추천을 정면으로 다룬, 구현 가능한 알고리즘 논문은 찾지 못했다.** 가장 구체적인 구조는 Bimpikis et al.의 반사실 프레임워크다(정책 4종 × 공급 6단계, 임계값 κ와 비율 η로 정의한 추천 알림). Pinker, Seidmann, Vakrat(2003, Management Science, DOI 10.1287/mnsc.49.11.1457.20584)는 연구 아젠다를 정리한 리뷰다 ([EconPapers](https://econpapers.repec.org/RePEc:inm:ormnsc:v:49:y:2003:i:11:p:1457-1484)). 요청받은 "Gonzalez/Hoppe", "Vakrat & Seidmann 기간 논문", "Kim/Li auction calendar"는 정확한 서지를 찾지 못해 **미확인**으로 남긴다. 판매자 전략의 효과가 전반적으로 매우 작다는 Anderson et al.(2007, eBay 1,177건)의 결론도 기대 효과를 과장하지 말아야 할 근거다 ([MPRA](https://ideas.repec.org/p/pra/mprapa/4324.html)).

### 4.3 변수와 전처리: 공개 데이터는 사전값을, LAYER7 로그는 실제 값을 채운다

예측 시점 t0는 판매자가 종료 시각을 고르는 등록 시점이다. 모든 변수는 t0 시점에 알 수 있는 정보만으로 계산해야 한다.

| 변수 | 정의 | 콜드스타트 사전값 출처 | 운영 중 갱신 |
|---|---|---|---|
| `A_c(t)` 활성 구매자 강도 | 카테고리 c에서, 후보 종료 시각 t 직전 60분 동안 기대되는 활동량(조회·입찰·접속) | 공개 데이터에서 시간대에 관계없이 일관되게 확인된 것은 **0–5시 저조**뿐이다(Palm 158 입찰은 0–3시 36–56건/시 대 10–20시 약 200건/시, NBER 제안도 0–3시 저조, Einav의 00–05시 불리). 시간대가 확실한 MaxSold `bid_time`의 시간대별 분포는 **아직 집계하지 않았다** | LAYER7 이벤트 로그의 롤링 hour-of-week 추정 |
| 집계 창 60분 | 종료 직전 창의 길이 | Jank & Shmueli: 마지막 입찰의 72.5%가 1시간 안, 31.7%가 1분 안 | 자체 막판 입찰 분포로 재보정 |
| `C_i(t)` 공급 충돌 | t 근처에 끝나는 유사 경매 수(유사도·시간 거리 가중) | 계수 β는 공개 데이터로 식별하기 어렵다. Palm 158은 변동이 없고 MaxSold는 내생적이다. ShopGoodwill은 특정 키워드와 1–3일 수집 창에 몰려 있어 관계의 방향을 탐색하는 데만 쓰고 β 값으로는 쓰지 않는다 | 판매자 내 변동을 이용한 NB 회귀 |
| `night(t)` | 현지(KST) 00–05시 마감 패널티 | Einav et al.(2015) | 유지 |
| `dur` | 종료 시각 − 등록 시각(24–72h) | 효과가 작고 플랫폼마다 부호가 다름 | 공변량으로 두고 추정 |
| `sim(i,j)` | 수집품 유사도(카테고리 트리, 시리즈/세트, 등급(PSA 등), 가격대) | Pokémon 시세 참조(CC BY 4.0)로 가격대 구간을 잡음 | 클릭·동시 관심 기반으로 보정 |

전처리 규칙은 데이터마다 다르다. 공통 원칙은 모든 시각을 UTC로 저장하고, 특징은 각 시장의 현지 시각으로 바꾸는 것이다. MaxSold는 offset을 반영해 동부시간으로 바꾸고, 1969-12-31 자리표시 17건을 결측 처리한다. Swoopo는 "PDT" 라벨이 연중 고정돼 있어 서머타임 보정 여부를 판단할 수 없다. 따라서 시간대 결론을 내지 말고 모양 비교에만 쓴다. 형식 불량 102행은 제외한다. Palm 158은 시간대 미표기를 명시하고, `*` 입찰자 행 324개(판매자 시작가 기록으로 추정)를 실입찰에서 뺀다. Jank & Shmueli 표준 파일의 bidder "NA"와 빈칸, "Private"은 입찰자 분석에서 제외한다. eBayAuctions는 완전 중복 346행을 먼저 제거하고 결과를 다시 계산해야 한다. 노트의 요일별 비율은 중복을 제거하기 전 수치다. 168개 요일×시간 셀은 소규모 데이터에서 희소하므로 일 주기 푸리에 항(K=3–4)과 요일 효과로 평활한다. 카테고리별 추정치는 경험적 베이즈로 수축한다. `â_ch = (n_ch + m·p_h) / (N_c + m)`이고, p_h는 전체 시간대 분포, m은 사전 강도다. **활동량의 관측 단위**도 정해야 한다. 동일 사용자의 반복 조회·입찰 50건을 서로 독립된 구매자 50명으로 세지 않도록 고유 활동 사용자 수와 사용자-일(user-day)을 우선 집계하고, 조회·입찰 건수는 보조 신호로 취급한다. 특정 시간에 활성 경매가 많아져 총 이벤트가 늘어난 효과를 점검하기 위해 활성 경매 수당 활동량도 민감도 분석에서 확인한다. 다만 이 정규화와 `C_i(t)` 경쟁 패널티를 동시에 쓰면 공급 효과를 이중 반영할 수 있으므로 운영 점수에 넣기 전에 별도로 검증한다.

### 4.4 점수식: 구매자당 경쟁 경매 비율을 로그로 쓴다

```
score_i(t) = log Â_c(t)                      # 종료 직전 60분 기대 활동량 (수축·평활 추정)
           − β · log(1 + Ĉ_i(t))             # 유사 경매 공급 충돌
           − π · 1[t ∈ 00:00–05:00 KST]       # 심야 패널티 (문헌상 가장 일관된 규칙)
           (+ γ · log(1 + Ĉ_broad(t)) : 선택, 기본 γ = 0)

t ∈ {now+24h, …, now+72h}, 30분 또는 1시간 격자 (최대 97개 또는 49개 후보)
```

β = 1이면 점수는 "경쟁 경매 한 건당 활성 구매자 수"의 로그와 같다. Simonsohn식 직관(구매자가 몰리는 시간대에는 판매자도 몰린다)을 가장 단순하게 표현한 형태다. γ 항은 Bimpikis의 역U자 가설, 즉 넓은 카테고리 수준의 두께가 다중 수요 구매자를 끌어들인다는 가설을 반영할 자리다. 이 결과는 B2B 플랫폼 수준의 시뮬레이션에서 나왔으므로 **기본값은 0으로 둔다**. 데이터로 확인되기 전에는 켜지 않는다. 이 점수식은 문헌 개념을 조합한 휴리스틱이며 **어떤 문헌도 이 식의 최적성을 증명하지 않았다**. β와 π의 초기값은 4.3절의 사전값과 6.3절 시뮬레이션의 민감도 분석으로 범위를 정한다. ShopGoodwill 같은 공개 데이터의 밀집 수치를 β 값으로 그대로 옮기지 않는다. 데이터가 부족한 동안에는 4.7절의 보수적 기본 정책을 쓴다. 이후 LAYER7 데이터에서 판매자 고정효과를 넣은 NB 회귀로 다시 추정한다.

### 4.5 공급 충돌 계산: 시점 고정(point-in-time)이 핵심이다

```
Ĉ_i(t) = Σ_{j ∈ Active(t0), j ≠ i}  sim(i, j) · K(|end_j − t|)
         + λ̂_future(t) · E[sim]                # 선택: t0 이후 등록될 경쟁 경매의 기대 유입

K(d) = max(0, 1 − d / h),  h = 60분 (삼각 커널)
Active(t0) = t0 시점에 이미 등록됐고 종료 시각이 [now+24h−h, now+72h+h] 안에 있는 경매
```

구현할 때는 `auctions(end_at, category_id, status)` 복합 인덱스로 후보 창 안의 경매를 한 번에 가져온다. 그다음 후보 시각마다 커널 가중합을 메모리에서 계산한다. 슬롯이 수십 개이고 경쟁 경매가 수백 건 수준이면 요청 한 번의 연산량은 미미하다. 운영에서는 판매자가 종료 시각을 확정할 때마다 해당 경매를 Active 집합에 즉시 넣어, 다음 판매자의 추천이 순차적으로 갱신되게 한다. 쏠림 방지 장치다. 학습과 평가 데이터에서 이 피처를 만들 때는 반드시 **t0 시점에 이미 등록돼 있던 경매만** 써야 한다. t0 이후 등록된 경쟁 경매나 경쟁 경매의 최종가·입찰 수를 쓰면 미래 정보 누수다. 공개 데이터에는 경매 "등록 시각"이 있는 경우가 드물다. MaxSold는 `auction_starts`, Palm 158은 `Auction Start`가 있다. 그래서 시점 고정 재현은 이 두 데이터에서만 가능하다.

**동시 등록 처리: 잠그지 않고 등록할 때 다시 계산한다.** 순차 갱신은 판매자가 한 명씩 등록할 때만 완전하게 작동한다. 판매자 A와 B가 둘 다 20:00에 추천을 요청하면, 서로의 등록을 모른 채 똑같이 일요일 22:00을 추천받을 수 있다. 추천 시점의 Active 집합과 등록 시점의 Active 집합이 달라지는 것이다. 그렇다고 **종료 시각 중복을 금지하지는 않는다.** 경매가 겹친다고 반드시 성과가 나빠지는 것은 아니다. 잠식 강도는 유사도와 품목에 따라 다르다(4.2절). 중복을 막으면 판매자의 선택권도 침해한다. MVP에서는 분산 락이나 슬롯 예약 없이 **추천 시각 선택(`RECOMMENDED`)과 직접 입력(`MANUAL`)을 구분**해 다음과 같이 처리한다.

| 단계 | `RECOMMENDED`: 추천 후보 선택 | `MANUAL`: 종료 시각 직접 입력 | 기록 |
|---|---|---|---|
| 1. 추천 생성 | 후보별 `Ĉ_i(t)`와 경쟁 경매 ID 집합을 스냅숏으로 저장 | 추천 화면을 열었으면 노출 이력만 연결해도 됨 | `generated_at`, 후보별 `Ĉ`, 경쟁 경매 ID, `policy_version` |
| 2. 등록 요청 | `recommendation_id` 필수. 선택한 시각이 해당 추천 후보에 포함되는지 확인하고 최신 Active 집합으로 `Ĉ_now(t*)` 재계산 | `recommendation_id` 선택 사항. 기간(24–72h), 시간 정합성 등 등록 유효성 검사를 수행하고 선택 시각의 현재 충돌 정보만 조회 | `selection_source`, `Ĉ_now(t*)`, 재계산 시각 |
| 3. 변화 판정 | ① 충돌 가중합의 증가 `Ĉ_now(t*) − Ĉ_snapshot(t*) ≥ δ_weighted`, 또는 ② 최신 추천에서 선택 시각이 TOP 3 밖으로 밀리면 확인 필요. 스냅숏 만료(예: 30분)는 재계산을 **강제하는 조건**이지 단독 경고 사유는 아님 | 추천 스냅숏과 비교하지 않으며 TOP 3 이탈에 따른 재확인도 강제하지 않음. 충돌 현황은 참고 정보로 제공 가능 | `delta_conflict_weighted`, 판정 결과, 안내 여부 |
| 4. 판매자 결정 | 변화가 크면 새로운 TOP 3를 안내하고 원래 시각 유지(`keep_original=true`) 또는 새 시각 선택을 모두 허용 | 판매자가 설정한 시각으로 등록. 충돌을 이유로 등록 차단하지 않음 | 유지/변경, 최종 종료 시각 |

**`δ_weighted`는 실제 경매 건수가 아니라 유사도 × 시간거리 커널로 계산한 충돌 가중합(`Ĉ`) 단위의 임계값**이다. 예를 들어 `δ_weighted=2.0`은 완전 유사한 경매 2건이 정확히 같은 시간에 추가된 경우와 대응하지만, 항상 경매 2건을 뜻하지는 않는다. 안내 문구에 "비슷한 경매 2건 추가"라고 쓰려면 별도 쿼리 또는 스냅숏 차집합으로 **실제 추가 건수**를 확인해야 한다. 이 임계값과 스냅숏 만료 시간은 초기 운영 규칙의 예시이며 실증적으로 검증된 기준이 아니다.

```text
POST /recommendations
  → recommendation_id, TOP 3, evidence_label, factors_used (4.7절)

POST /auctions { end_at, selection_source: "RECOMMENDED", recommendation_id, keep_original? }
  ├─ 변동 작음            → 201 등록 완료
  ├─ 변동 큼 & 미확인      → 확인 필요 응답 { revalidation: { status: "changed", delta_conflict_weighted, new_top3, reason } }
  └─ keep_original = true → 201 등록 완료 (재안내 및 유지 선택 로그 기록)

POST /auctions { end_at, selection_source: "MANUAL", recommendation_id? }
  └─ 기간·입력 검증 후    → 201 등록 완료 (충돌 현황은 선택적 참고 정보, 재추천 강제 없음)
```

두 등록 요청이 거의 동시에 들어오면 서로를 보지 못한 채 등록될 수 있다. 중복이 금지 대상이 아니므로 이를 허용하며, 커밋된 경매는 이후 추천에 반영한다. `RECOMMENDED`와 `MANUAL` 모두 24–72시간 범위는 **추천 요청 시각이 아니라 실제 등록 확정 시각**을 기준으로 서버에서 검증한다. 추천이 오래되거나 등록 도중 기간 경계를 넘었다면 해당 시각은 사용할 수 없으므로 새로운 종료 시각을 선택해야 한다. 로그의 스냅숏과 재검증 기록으로 실제 겹침 빈도를 측정한 뒤, 필요할 때에만 슬롯 예약 같은 장치를 검토한다.

### 4.6 TOP 3 선택: 초기에는 결정론적으로 고르고 추천·선택을 기록한다

상위 3개를 그대로 뽑으면 인접한 30분 슬롯 세 개가 나오기 쉽다. **TOP 3 선택 전략은 `policy_version`별로 구분한다.** 두 정책 모두 같은 입력에는 같은 결과를 반환한다.

| 정책 | 후보 선택 순서 | 거리·동률 규칙 |
|---|---|---|
| `conservative-v0` | 기간을 `[24h,40h)`, `[40h,56h)`, `[56h,72h]` 세 구간으로 나누고 각 구간에서 **점수가 가장 높은 후보를 하나씩 우선 선택**한다. 근거 없는 특정 시각 선호와 지나친 쏠림을 방지하기 위한 정책 | 전체 후보 간 **최소 3시간 간격**을 유지하도록, 구간별 다음 순위 후보를 탐색한다. 같은 점수면 가장 가까운 유사 경매 종료까지의 거리가 먼 쪽 → 이른 시각 |
| `activity-v1` | 전체 후보를 **점수 내림차순**으로 정렬한 뒤, 이미 선택한 후보와 최소 3시간 이상 떨어진 후보를 차례로 뽑는 탐욕적 선택 | 같은 동률 규칙 적용. 점수 차가 허용폭(ε) 이내면 동률 표시 |

구간별 1개와 최소 3시간 간격은 인접 구간 경계에서 충돌할 수 있다(예: 39h와 40h). 이때는 다음 후보를 검사해 간격을 만족시키며, 임의의 규칙을 숨겨서 우선순위를 뒤집지 않는다. 유효한 후보가 부족하면 개수를 줄이고 이유를 알려 주지, 범위를 벗어난 시각이나 거리 규칙 위반 시각을 억지로 채우지 않는다. `conservative-v0`는 통계적 최적 시각이 아니라 **세 개의 서로 다른 선택지를 일관되게 제공하는 정책**이다.

출시 초기에는 softmax 같은 무작위 추천을 넣지 않는다. 대신 다음을 **추천할 때마다 로그로 남긴다**.

| 로그 항목 | 내용 |
|---|---|
| 추천 맥락 | recommendation_id, 경매(초안) ID, 판매자 ID, 카테고리, 추천 생성 시각(`generated_at`, t0), policy_version |
| 추천 결과 | TOP 3 후보 시각, 각 후보의 점수와 구성 요소(`Â`, `Ĉ`, 심야 여부), 동률 여부, `factors_used`, 화면 라벨과 그 근거(`data_sufficiency`, `rank_stability` 지표), 당시 `effect_validation` 상태(4.7절) |
| 경쟁 스냅숏 | 후보별 `Ĉ` 계산에 들어간 경쟁 경매 ID 목록(4.5절 동시 등록 처리) |
| 등록 시 재검증 | `selection_source`, 재계산 시각, `Ĉ_now(t*)`, `delta_conflict_weighted`(추천 선택만), 재추천 안내 여부, 판매자의 유지·변경 결정 |
| 판매자 선택 | 최종 선택한 종료 시각, `selection_source`(`RECOMMENDED`/`MANUAL`), TOP 3 내 순위(추천 선택인 경우), 직접 입력 여부 |
| 결과 | 종료 후 입찰 수, 고유 입찰자 수, 낙찰 여부, 낙찰가 (경매 종료 시 채움) |

쏠림은 4.5절의 순차 갱신이 1차로 막는다. 판매자가 종료 시각을 확정하면 그 경매가 곧바로 Active 집합에 들어가므로, 다음 판매자의 같은 슬롯 점수가 내려간다. 여러 판매자가 동시에 추천받는 경우는 4.5절의 등록 시 재검증으로 보완한다. 결정론적 로그에는 한계가 있다. 모든 후보의 노출 확률이 0 또는 1이므로 IPS·DR 같은 off-policy 평가를 할 수 없다. 추천을 따른 판매자와 따르지 않은 판매자를 비교하는 것도 자기 선택 편향이 있는 관측 비교에 그친다. 그래서 무작위화는 평가 설계를 확정할 때 함께 도입한다. 6.4절에서 설명하는 TOP 3 구성·순서 무작위화나 스위치백이 그 단계다. 로그 스키마에 노출 확률 컬럼을 미리 두고, 초기에는 1.0으로 채워 두면 나중에 테이블을 바꾸지 않아도 된다.

### 4.7 최초 추천 정책과 추천 근거 표시: 데이터가 부족하면 두 가지 회피 규칙만 쓰고 "추천 근거 부족"으로 표시한다

출시 직후에는 LAYER7 자체 활동 로그가 거의 없다. 외국·과거 데이터로 만든 `Â_c(t)` 곡선은 시간대와 시장이 달라 믿기 어렵다(4.3절). 이 상태에서 4.4절 점수식을 그대로 쓰면, 근거 없는 활동 곡선이 추천 순위를 정하게 된다. 그래서 **보수적 기본 정책(policy_version = `conservative-v0`)**을 둔다.

**발동 조건.** 카테고리 c의 LAYER7 자체 활동 데이터가 부족하거나, 데이터가 있어도 추천 순위가 심하게 불안정하면 기본 정책을 쓴다. 최근 4주 종료 경매 수 `N_min`(예: 30건)은 **카테고리 전체의 최소 관측량을 점검하는 보조 조건**이지, 시간대별 추정이 충분하다는 뜻이 아니다. 구매자 활동 추정에는 별도로 고유 활동 사용자·관측일 및 **실제 후보 시각의 유효 표본 수**를 확인한다(아래 `data_sufficiency`). `N_min`과 개별 문턱값은 실증적으로 정해진 수치가 아니라 베타 데이터에서 학습 곡선·부트스트랩 폭을 보고 조정할 출발점이다.

**점수.** 문헌에서 가장 일관된 규칙인 심야 회피와, t0 시점에 이미 등록된 유사 경매와의 충돌 회피만 쓴다.

```
score0_i(t) = − π · 1[t ∈ 00:00–05:00 KST]
              − β0 · Ĉ_i(t)          # Active(t0)의 이미 등록된 유사 경매만, 미래 유입 항 없음
γ = 0, Â_c(t) 미사용
```

β0와 π는 크기를 추정한 값이 아니라 **순서를 정하는 규칙**이다. π는 심야 후보가 비심야 후보보다 항상 뒤로 밀릴 만큼 크게 둔다. 24–72시간 창에는 비심야 후보가 늘 충분히 있다. β0는 "충돌이 적을수록 앞"이라는 순서만 만들면 된다. Goodwill 등 공개 데이터의 밀집 수치에서 β0를 가져오지 않는다(3장 2위 참고). **TOP 3는 4.6절에 명시한 `conservative-v0` 전용 방식**으로 고른다. 즉, `[24,40)h`, `[40,56)h`, `[56,72]h` 구간에서 하나씩 우선 선택하고 전체 최소 3시간 간격을 확인한다.

**전환.** 카테고리의 데이터 충분성 조건이 충족되고 추천 순위 안정성이 아래의 **최소 허용 기준**을 통과하면, 해당 카테고리에서 4.4절 전체 점수식(`Â_c(t)` 포함, `policy_version=activity-v1`)을 사용한다. 충분한 데이터가 있어도 추천 순위가 최소 허용 기준 미만이거나 안정성 평가가 불가능하면 `conservative-v0`를 유지한다. 전환 여부를 판단하는 동안에도 `conservative-v0`로 서비스하는 카테고리에 대해 `activity-v1` 후보 점수와 부트스트랩을 **내부에서만 시험 계산(shadow evaluation)** 할 수 있다. 이 시험 점수는 판매자에게 노출하거나 추천 순위를 바꾸는 데 사용하지 않는다. 전환 시점, 기준 버전과 정책 버전은 로그에 남겨 정책별 성과를 비교한다.

**추천 근거 라벨: 세 가지 상태를 섞지 않는다.** 표본 수와 부트스트랩 결과로 라벨을 올리는 정책은 유지한다. 다만 데이터가 충분하고 추천 순위가 안정적이라는 것과, 추천을 따르면 성과가 좋아진다는 것은 서로 다른 주장이다. 따라서 다음 상태를 구분한다.

| 상태 (내부 필드) | 질문 | 판단 기준 (초기값은 예시이며 사후 조정 필요) | 화면 표시 |
|---|---|---|---|
| 데이터 충분성 (`data_sufficiency`) | 분석할 데이터와 후보별 활동 근거가 충분한가? | **카테고리 전체 기준**: 최근 4주 종료 경매 ≥ `N_min`(예: 30), 서로 다른 판매자 ≥ `m`(예: 10), 최대 판매자 점유율 ≤ 50%. **활동·후보별 기준**: 고유 활동 사용자·관측일을 확인하고, 평활된 3시간 블록에서 후보 시각별 유효 표본 수(`n_eff`, 예: 고유 사용자-일 ≥ 5)를 확인한다. 최소 3개 후보가 3시간 이상 이격되어 안정적으로 추정 가능해야 한다. 전체 56개 요일×3시간 셀의 80%에 관측 5건을 요구하는 규칙은 **삭제**한다. 그 규칙은 최소 225건을 요구해 `N_min=30`과 정합성이 없고 일부 비인기 시간대 때문에 모든 후보를 차단할 수 있기 때문이다. | 라벨에 반영 |
| 추천 순위 안정성 (`rank_stability`) | 표본을 다시 뽑아도 같은 후보가 추천되는가? | 반복 재표본추출 B회(예: 200)에서 **1위 재현율**과 TOP 3 평균 겹침(Jaccard)을 계산하고, 필요하면 1·2위 점수 차/표준편차를 진단값으로 기록. 활동 로그 기반 `Â`는 사용자·일자 단위의 독립성/의존성을 반영해 블록 재표본추출하고, 판매자·경매 수준 효과를 추정할 때는 판매자 단위 클러스터 부트스트랩을 적용한다. **서로 다른 관측 단위를 동일한 독립 표본처럼 세지 않는다.** | 라벨에 반영 |
| 추천 효과 검증 (`effect_validation`) | 실제로 추천을 따르면 경매 성과가 개선되는가? | 6.4절의 무작위화·스위치백 실험 또는 식별 조건이 충족된 정책 평가 | **라벨에 혼합하지 않는다.** 내부 기록: `unverified` / `in_experiment` / `verified_positive` / `verified_null` |

**표시 라벨의 판정 순서는 상호 배타적이며 모든 입력을 포괄한다.** `rank_stability`를 계산할 수 없으면 최소 허용 기준 미달로 취급한다. 임계값 자체는 검증된 통계적 기준이 아닌 초기 운영값이다.

| 화면 라벨 (`evidence_label`) | 조건 | 적용 정책 |
|---|---|---|
| 추천 근거 부족 (`insufficient`) | 데이터 충분성 미달 **또는** 1위 재현율 < 0.6 **또는** TOP 3 Jaccard < 0.5 **또는** 안정성 계산 불가 | `conservative-v0` (이 정책에서는 항상 '부족') |
| 추천 근거 보통 (`moderate`) | 데이터 충분성 충족, 1위 재현율 ≥ 0.6, Jaccard ≥ 0.5이면서, **1위 재현율 < 0.8 또는 Jaccard < 0.7** | `activity-v1` |
| 추천 근거 충분 (`sufficient`) | 데이터 충분성 충족, 1위 재현율 ≥ 0.8 **그리고** Jaccard ≥ 0.7 | `activity-v1` |

예를 들어 1위 재현율이 0.7이고 TOP 3 Jaccard가 0.6이면 **'보통'**이다. 반대로 데이터가 아무리 많아도 1위 재현율이 0.4이면 **'부족'**이다. 두 지표 중 하나라도 최소 기준에 미달하면 전체 점수식 대신 보수적 추천으로 돌아간다. `conservative-v0`의 점수는 현재 Active 집합에서 결정론적으로 계산되므로 같은 방식의 활동량 부트스트랩으로 '높음'을 주장하지 않는다. 기준값과 변경 이력은 별도 `evidence_rule_version`으로 관리한다.

예를 들어 한 카테고리에 5,000건이 쌓였고 여러 사용자·기간에 걸쳐 활동 데이터가 고르게 관측되며 부트스트랩에서 일요일 20시가 반복해서 1위였다고 하자. 그러면 '추천 근거 충분'을 표시할 수 있다. 그러나 이것은 **추천 순위가 통계적으로 안정적이라는 뜻**이지, 그 시각에 끝내면 낙찰가가 높아진다는 뜻이 아니다. 그 성과 주장은 `effect_validation=verified_positive`가 된 뒤 검증된 집단과 조건에서만 할 수 있다.

**설명 문구: 실제로 계산한 요소만 설명한다.** 초기 정책에서 "구매자 활동이 활발한 시간입니다"라고 보여 주면, 계산하지 않은 요소를 추천 근거로 내세우게 된다. 그래서 추천 API가 설명의 재료를 구조화해서 함께 반환한다. 프론트엔드는 그 재료만 문구 템플릿에 넣고, 근거를 따로 만들어 내지 않는다.

```jsonc
{
  "recommendation_id": "rec_…",
  "policy_version": "conservative-v0",
  "evidence_label": "insufficient",            // insufficient | moderate | sufficient
  "factors_used": ["night_penalty", "conflict"],
  "candidates": [
    {
      "end_at": "2026-11-08T11:00:00Z",          // KST 일요일 20:00
      "score": -1.0,                             // 예시: β0=1, Ĉ=1, 심야 아님
      "conflict_weighted": 1.0,                 // 유사도×시간거리 가중합(실제 건수와 구분)
      "reasons": [
        {"code": "NOT_NIGHT"},
        {"code": "LOW_CONFLICT", "similar_count": 1, "window_minutes": 60} // 가중합과 별도로 센 실제 경매 건수
      ]
    }
  ]
}
```

규칙은 세 가지다. 첫째, `reasons`에는 `factors_used`에 있는 요소의 코드만 들어간다. 활동 요소(`activity`)는 `activity-v1`에서만 `factors_used`에 들어가므로, `HIGH_ACTIVITY` 같은 코드는 초기 정책에서 나올 수 없다. 둘째, 정책마다 고정 안내 문구를 붙인다. `conservative-v0`에는 "구매자 활동 데이터는 아직 충분하지 않습니다."를, `activity-v1`에는 `effect_validation`이 `verified_positive`가 아닌 동안 "실제 낙찰 성과 개선 여부는 별도로 검증됩니다."를 붙인다. 셋째, 수치가 있는 근거는 수치를 그대로 보여 준다(예: "±1시간 안에 비슷한 경매 1건 종료"). 추천은 강제하지 않는다는 원칙에 맞게, 판매자가 직접 고르는 입력을 항상 함께 둔다.

아래는 실제 추천 결과가 아니라 **문구 설계 예시**다.

| 정책 | 화면 예시 |
|---|---|
| `conservative-v0` | **추천 근거 부족** · 추천 종료: 일요일 오후 8시 · 심야 시간대가 아니며, 비슷한 상품의 경매 종료가 상대적으로 적은 시간입니다. 구매자 활동 데이터는 아직 충분하지 않습니다. |
| `activity-v1` | **추천 근거 충분** · 추천 종료: 일요일 오후 8시 · 최근 해당 카테고리의 구매자 활동 수준이 높고, 유사 상품 경매와의 종료 충돌이 상대적으로 적습니다. 실제 낙찰 성과 개선 여부는 별도로 검증됩니다. |

### 4.8 바로 쓸 수 있는 오픈소스와 리플리케이션 자원

공개 리플리케이션 패키지는 Coey, Larsen, Platt(AER 2020)의 openICPSR 119387만 확인했다. 그마저 eBay 원자료 일부는 독점이라 README 절차로만 접근할 수 있다 ([openICPSR](https://www.openicpsr.org/openicpsr/project/119387/version/V2/view)). Bimpikis et al.과 Einav et al.은 독점 데이터이고 코드 공개도 확인되지 않았다. 구현에 참고할 코드로는 Open Bandit Pipeline(obp)이 있다. IPS·SNIPS·DR 추정량과 합성 밴딧 데이터 생성기를 제공한다 ([arXiv 2008.07146](https://arxiv.org/abs/2008.07146)). AuctionGym은 광고 입찰자 쪽 시뮬레이터이지만 설정 파일과 CSV 출력 구조를 참고할 만하다(Apache-2.0, [Amazon Science](https://www.amazon.science/publications/learning-to-bid-with-auctiongym)). scikit-learn의 Poisson 회귀 예제는 계수 타깃의 평가 지표 선택을 보여준다 ([예제](https://scikit-learn.org/stable/auto_examples/linear_model/plot_poisson_regression_non_normal_loss.html)). hard/soft close 입찰자 에이전트 모형은 Duffy & Ünver(2008)를 참고할 수 있다 ([PDF](https://sites.socsci.uci.edu/~duffy/papers/jebo1007_rev13.pdf)). **판매자 종료 시각 스케줄링 전용 오픈소스 시뮬레이터는 찾지 못했다.** ShopGoodwill 스크래퍼처럼 GitHub에 있는 수집 도구는 대상 사이트의 약관 문제 때문에 데이터 출처로 권하지 않는다.

## 5. 머신러닝 도입 가능성

### 5.1 무엇을 학습하고 무엇을 예측하나: 연관을 학습한다

접근법 B의 표준 형태는 다음과 같다. 타깃은 경매(또는 물품)의 입찰 수(Poisson/Tweedie 목적함수), 낙찰 여부(로지스틱), 또는 기준가 대비 로그 낙찰가다. 피처는 t0에 알 수 있는 정보로 한정한다. 종료 hour-of-week(주기 인코딩), 기간, 카테고리, 시작가, t0 이전의 판매자 이력, 시점 고정 `C_i(t)`, 롤링 `A_c(t)`가 여기에 해당한다. 추론할 때는 후보 시각 t마다 시간 관련 피처만 바꿔 넣고 예측값으로 순위를 매긴다. 이 모델이 배우는 것은 **"이 시각에 끝난 경매는 보통 입찰이 몇 개였나"라는 조건부 기대값(연관)**이다. **"이 경매를 이 시각으로 옮기면 몇 개가 될까"(개입)가 아니다.** 판매자 숙련도, 상품 품질, 플랫폼 기본값이 종료 시각과 결과에 동시에 영향을 준다. Simonsohn(2010)은 숙련 판매자가 오히려 피크로 몰린다는 것을 보였다. 이런 이유로 관측 상관은 어느 방향으로든 편향될 수 있다. 상관이 강하다고 해서 종료 시각을 바꾸는 효과가 증명되지는 않는다. 이 점을 보고서와 발표에 명시해야 한다.

### 5.2 데이터셋별 ML 학습 가치: MaxSold만 "학습할 만하다"

| 데이터셋 | ML 학습 가치 | 이유 |
|---|---|---|
| MaxSold | **중** (공개 데이터 중 유일하게 학습할 만함) | 물품 300만 개, 경매 2.4만 건, 시점 고정 피처를 재현할 수 있음. 단, 종료 시각 분산이 작아 시간 효과는 거의 학습되지 않고, 라이선스가 불확실함 |
| ShopGoodwill (`ebay-sold-comps`) | 하~중 (GLM 수준) | 약 2,600건, 판매자 ID 있음. 판매자 랜덤효과 NB로 종료 시간대와 공급 밀집의 연관을 보는 데 적당. 낙찰분만 있고 수집 창이 짧아 배포용 학습에는 부적합 |
| Swoopo | 하~중 | 규모는 크지만 종료가 내생적이라 학습 결과를 이전할 수 없음. 활동 곡선 모델에만 씀 |
| Jank & Shmueli | 하 (GLM 수준) | 628건(절대 시각 158건). 부스팅의 이득을 기대하기 어려움 |
| eBayAuctions (DMBA) | 하 (수업용) | 고유 1,626행, 요일만 있음. 중복 제거 필수 |
| UCI Shill, GSA, NBER, Copart, MerRec | 종료 시각 학습용으로는 없음 | 시간 정보 부재, 날짜 단위, 경매 아님, 가격 마스킹 |

규모와 컬럼을 함께 보면 결론은 분명하다. LAYER7에 배포할 모델을 **공개 데이터만으로 학습하는 것은 의미가 없다.** 한국 수집품, 24–72시간, 판매자 선택 구조를 가진 공개 데이터가 없기 때문이다. 공개 데이터로 학습한 모델은 그 플랫폼(캐나다 유품 경매, 2003년 eBay)을 예측할 뿐이다. 공개 데이터에서 ML은 "파이프라인과 평가 방법론을 시연하는 오프라인 실험"으로 자리매김해야 한다. 그 실험에서도 B가 A를 이긴다는 보장은 없다.

### 5.3 eBay 라이선스가 학습·합성 경로를 막는다

eBay API License Agreement는 eBay Content로 "알고리즘을 학습시키거나 ML을 수행하거나 합성 데이터셋을 만드는 것"을 금지한다. Restricted API 데이터의 bulk 다운로드와 제3자 제공도 금지하고, 화면에 표시하는 리스팅 정보는 6시간보다 오래되면 안 된다. 성사율·성공률 같은 파생 데이터와 reserve 경매 정보는 사전 서면 허가가 필요하다 ([eBay API License Agreement](https://developer.ebay.com/join/api-license-agreement)). Browse API에는 `itemEndDate`, `bidCount`, `uniqueBidderCount` 필드가 있다 ([Browse OpenAPI](https://developer.ebay.com/api-docs/master/buy/browse/openapi/3/buy_browse_v1_oas3.json)). 그러나 진행 중인 경매를 폴링해 학습용 데이터셋을 만드는 것은 이 조항에 정면으로 걸린다. 할 수 있는 일은 실시간 참고 표시 정도다. 따라서 **eBay API로 학습 데이터를 모으는 길과 eBay 데이터로 합성 데이터를 만드는 길은 모두 닫혀 있다.** 2003–2004년에 수집된 학술 데이터셋(Jank & Shmueli, DMBA)은 이 API 계약을 통해 얻은 것이 아니므로 이 조항이 직접 적용되지는 않는다. 다만 자체 라이선스가 불명확하므로 비영리 연구 목적, 출처 표기, 재배포 금지로 보수적으로 다룬다. 이 판단은 법률 자문이 아니므로 지도교수 검토를 권한다.

### 5.4 소규모 데이터에서 의미 있는 ML이 가능한가: GLM이 먼저다

Grinsztajn et al.(2022)의 "트리 모델이 딥러닝보다 낫다"는 결론은 약 1만 표본 규모의 데이터 기준이다. 수백 건 규모에서 부스팅이 GLM을 이긴다는 근거가 아니다 ([arXiv 2207.08815](https://arxiv.org/abs/2207.08815)). scikit-learn의 계수 예제에서도 평균 Poisson deviance는 PoissonRegressor 0.594, HistGradientBoosting(Poisson) 0.575로 차이가 작았다 ([scikit-learn](https://scikit-learn.org/stable/auto_examples/linear_model/plot_poisson_regression_non_normal_loss.html)). 이 예제는 수십만 건 보험 데이터다. Riley et al.(2020, BMJ)은 "변수당 10 사건" 같은 경험칙 대신 과적합(수축 계수 ≥ 0.9) 기준으로 필요한 표본을 계산하라고 권한다 ([Utrecht](https://dspace.library.uu.nl/handle/1874/457642)). 따라서 LAYER7 초기 규모(수백 건)에서는 다음 순서의 모델 사다리를 따른다. 카테고리×시간대 평균에 경험적 베이즈 수축 → Poisson GLM → NB GLM(과산포 시) → 판매자·카테고리 랜덤효과 NB → 강하게 정규화한 LightGBM Poisson(`num_leaves` 작게, `min_data_in_leaf` 크게, early stopping). 각 단계는 직전 단계를 **그룹·시간 교차검증에서 의미 있게 이길 때만** 채택한다. 학습 곡선(표본 10%→100%)에서 GLM과 GBM의 검증 deviance를 함께 그리면 "데이터가 얼마나 더 쌓이면 GBM이 이길지"를 정량적으로 논의할 수 있다.

### 5.5 합성 데이터 증강: 시험 장비로는 유용하고 학습 데이터로는 왜곡이다

합성 데이터는 실제 데이터에 없는 정보를 만들어 내지 못한다. 특히 **인과 효과에 대한 정보는 0이다.** CTGAN이나 SMOTE로 만든 행을 학습셋에 섞으면 모델은 생성기가 복제한 교란된 상관이나 생성기 자체의 가정을 배운다. 모델이 생성한 데이터를 반복 학습하면 분포의 꼬리가 사라진다는 결과가 있다 ([Shumailov et al. 2024, Nature](https://www.pure.ed.ac.uk/ws/portalfiles/portal/460496122/ShumailovEtalNature2024AIModelsCollapseWhen.pdf)). 이 결과는 재귀적 학습에 관한 것이지만, "희귀 사례(새벽 종료, 희귀 카테고리)가 과소 표현된다"는 메커니즘은 소규모 경매 데이터에도 해당한다. 73개 데이터셋 연구에서 강한 분류기에는 SMOTE의 이득이 없었다 ([Elor & Averbuch-Elor](https://arxiv.org/abs/2201.08528)). **합성 데이터가 도움이 되는 경우**는 셋이다. 참 효과를 아는 가상 시장에서 A·B 알고리즘과 OPE 추정량이 참값을 회복하는지 확인할 때, 대량 동시 종료·72시간 경계·서머타임 같은 엣지 케이스를 테스트할 때, 공개 데이터의 활동 곡선을 "사전 정보"로 주입할 때다. 마지막 경우는 합성이라고 부르지 말고 사전값이라고 명시해야 한다. **왜곡하는 경우**는 셋이다. 합성 행으로 종료 시각 효과를 학습시킬 때, 계수 타깃에 SMOTE를 적용할 때, 합성 데이터에서 잰 성능을 실제 성능처럼 보고할 때다. 합성 데이터를 쓴다면 TSTR(합성으로 학습, 실제로 평가)과 TRTR(실제로 학습, 실제로 평가)을 함께 보고하고, 최종 수치는 실제 홀드아웃으로만 낸다 ([TSTR 설명](https://clearbox-synthetic-kit.readthedocs.io/en/develop/wiki/utility.html)). eBay 콘텐츠를 원천으로 한 합성 데이터 생성은 5.3절의 약관이 금지한다.

### 5.6 데이터셋을 결합할 수 있는가: 모양은 합치고 수준은 합치지 않는다

결합하면 공변량 이동과 개념 이동이 동시에 생긴다. 시대는 2003년부터 2026년까지 걸쳐 있다. 시간대는 Palm 158 미표기, Swoopo 연중 "PDT", MaxSold 동부시간 offset으로 제각각이다. 통화도 다르다. DMBA는 USD로 환산돼 있고, MaxSold의 통화 컬럼은 이번 조사에서 확인하지 않았다. 마감 규칙은 eBay hard close, MaxSold soft close, Swoopo 카운트다운으로 다르다. 기간도 3/5/7/10일, 6–7일, 카운트다운으로 다르고, 카테고리 체계도 맞지 않는다. 결합할 수 있는 것은 **구조**다. 정규화한 시간대 활동 곡선의 상대 모양, 계수 분포의 과산포 정도, 피처 설계 아이디어가 여기에 해당한다. 결합하면 안 되는 것은 **수준과 규칙 의존 효과**다. 절대 가격, 절대 입찰 수, 마감 규칙에 따라 달라지는 종료 시각 효과, 외국 사용자의 시간대 패턴을 한국 사용자에게 그대로 적용하는 것이 그렇다. 굳이 함께 모형화한다면 `bids ~ hour_block + category + log(start_price) + log(duration) + (1|dataset) + (hour_block|dataset)` 같은 부분 풀링 혼합효과 NB가 표준이다. 사전에 "이 행이 어느 데이터셋에서 왔는가"를 맞히는 분류기(adversarial validation)를 돌려 분포 차이를 진단한다. 경매 ID 단위로 결합할 수 있는 것은 Jank & Shmueli 파일들 사이뿐이다(Palm 158 ↔ 표준 7일 파일 157건, ↔ Curve Clustering 130건). 서로 다른 출처 사이에는 결합 키가 없다.

### 5.7 과적합·편향 검증: 누수, 카테고리, 판매자, 종료 시각 특성

| 위험 | 구체적 형태 | 검증·대응 |
|---|---|---|
| 사후 정보 누수 | 최종 입찰자 수, 막판 입찰, 최종 조회수·찜 수, 경쟁 경매의 결과 | 피처마다 "언제 알 수 있는가"를 기록하고 t0 이전 값만 사용. 사후 정보 누수 개념은 Kaufman et al.(2012, [DOI](https://doi.org/10.1145/2382577.2382579), 서지 미재확인) 참고 |
| 시간 누수 | 무작위 KFold로 미래 데이터를 학습해 과거를 예측함. 활동 곡선을 전체 기간으로 계산함 | 시간 기반 홀드아웃과 `TimeSeriesSplit`, 롤링 활동 곡선 |
| 중복·재등록 | DMBA 완전 중복 17.5%, 재등록 상품 | 중복 제거, 상품 지문·경매 ID로 `GroupKFold` |
| 판매자 편향 | 숙련 판매자가 특정 시간대를 고름(Simonsohn). 한 판매자가 많은 비중을 차지함(Curve Clustering 최다 판매자 1명이 40/149건) | 판매자 그룹 CV("새 판매자" 일반화), 판매자 랜덤효과, 판매자 내 비교 |
| 카테고리 차이 | 품목마다 막판 입찰 강도가 다름(1분 이내 Xbox 38.9% 대 전체 31.7%) | 카테고리별 성능을 따로 보고하고 수축 추정 |
| 종료 시각 특성 | 양성성 위반: MaxSold는 19–21시가 97.6%라 다른 시간대는 사실상 외삽 | 관측이 거의 없는 시간대 예측은 "추정 불가"로 표기 |
| 선택 편향 | 낙찰된 경매만 남기는 필터 | 유찰·무입찰 경매도 포함 |
| 튜닝 낙관 편향 | 같은 CV로 튜닝과 평가를 함께 함 | nested CV, 반복 CV로 분산 보고 |

## 6. 실험 설계

### 6.1 같은 실데이터 테스트셋에서 A와 B를 비교한다

주 실험장은 **MaxSold**다. 시점 고정 피처를 재현할 수 있는 규모와 절대 시각을 모두 갖춘 유일한 공개 데이터이기 때문이다. 2024년 이전을 학습에, 2025–2026년(직접 집계 기준 2,990건)을 봉인된 테스트에 쓰는 시간 분할을 권한다. 학습 구간 안에서는 경매 ID 그룹 CV로 튜닝한다. 보조 실험장은 **Jank & Shmueli**다. 628건 전체로 상대 시간 기반 막판 입찰 지표를 보고, Palm 158 + Curve Clustering으로 판매자 그룹 CV를 한다. 두 접근을 공정하게 비교하려면 비교 대상을 "시간 성분"으로 좁혀야 한다. A는 시간 이외 공변량만 넣은 기준 GLM에 규칙 점수 `score_i(t)`를 공변량 하나로 추가한 모델이다(학습되는 계수 1개). B는 같은 공변량에 시간 피처를 모두 넣은 LightGBM이다. 이렇게 하면 B가 이기더라도 그 이득이 시간 효과에서 왔는지, 상품 수준 차이를 더 잘 맞힌 데서 왔는지 구분할 수 있다.

### 6.2 예측 정확도 평가와 정책 효과 평가는 분리한다

**예측 정확도**는 Poisson deviance, MAE, 계수 데이터 보정 진단으로 잰다. 계수 데이터 보정 진단은 비무작위 PIT와 로그 점수다 ([Czado, Gneiting, Held 2009](https://ideas.repec.org/a/bla/biomet/v65y2009i4p1254-1261.html)). 여기에 예측 구간별 평균 예측과 관측값을 비교한다. 결과는 fold별 차이의 분포로 보고한다. **순위 능력**도 따로 본다. 추천기의 목적은 같은 경매 안에서 후보 시각들의 상대 순서를 맞히는 것이다. 그런데 관측 데이터에는 경매마다 결과가 하나뿐이다. 그래서 판매자 내 쌍이나 매칭 쌍(같은 판매자, 같은 카테고리, 비슷한 시작가, 다른 종료 시각)으로 근사한다. MaxSold에는 판매자 ID가 없어 이 근사가 어렵고, Curve Clustering(판매자 71명)에서만 소규모로 가능하다. **정책 효과**, 즉 TOP 3를 추천했을 때 판매자의 선택과 경매 성과가 실제로 바뀌는지는 공개 관측 데이터로 평가할 수 없다. 판매자의 선택 확률을 모르고, 추천을 따르는지(추종) 관측되지 않으며, 경매끼리 서로 잠식하기 때문이다. **RMSE가 낮다고 정책 가치가 높다는 뜻은 아니다.** 상품 간 수준 차이를 잘 맞히는 모델은 같은 경매 안에서 시각별 차이를 거의 학습하지 못했어도 예측 지표가 좋게 나온다.

**추천 순위 안정성**은 예측 정확도, 정책 효과와 별개인 세 번째 지표로 따로 보고한다. 4.7절의 정의를 그대로 쓴다. 활동 로그에서는 사용자·일자 블록, 판매자/경매 성과 추정에서는 판매자 클러스터를 고려한 재표본추출로 1위 재현율, TOP 3 평균 겹침, 1·2위 점수 차를 부트스트랩 표준편차로 나눈 값을 잰다. A와 B를 같은 테스트 데이터에서 이 지표로도 비교한다. 예측 정확도가 비슷하다면 순위가 더 안정적인 쪽이 판매자에게 일관된 추천을 준다. 그러나 안정성이 높다는 것은 "데이터가 조금 바뀌어도 같은 답을 낸다"는 뜻일 뿐이다. 그 답이 성과를 높인다는 증거는 아니다. 성과 개선은 6.4절에서 검증하고, 그 결과는 `effect_validation` 상태로만 기록한다.

### 6.3 데이터가 부족할 때는 제한적 시뮬레이션으로 평가한다

정책 효과는 단순한 이산 사건 시뮬레이터로 "가정 하의 정합성"을 검증한다. 시간 단위는 1시간 슬롯 × 2–4주다. 구매자 도착은 비동차 Poisson 과정으로 둔다. 강도 곡선은 공개 데이터의 정규화된 활동 모양(Palm 158, Swoopo traces, NBER threads; 시간대 불확실성은 별도 표기)에서 가져온다. 막판 입찰 비율은 Jank & Shmueli의 분포(1분 이내 31.7%, 1시간 이내 72.5%)로 보정한다. 구매자는 예산 1개를 가지고, 동시에 끝나는 대체재 경매 가운데 하나만 입찰한다고 가정한다. 이렇게 하면 공급 충돌과 잠식이 자연스럽게 생긴다. 비교할 정책은 판매자 자유 선택(기본값), 4.7절 보수적 기본 정책, A의 TOP 3, B의 TOP 3, 무작위 TOP 3다. 지표는 경매당 평균 입찰 수, 낙찰률, 평균 낙찰가, 슬롯별 쏠림 지수(HHI), 판매자 간 형평성이다. 시뮬레이션의 핵심 가치는 **민감도 분석**에 있다. 활동 곡선 진폭, 잠식 강도 β, 추천을 따르는 확률, sniper 비율을 격자로 바꿔 가며 정책 순위가 뒤집히는 조건을 보고한다. 모든 파라미터의 출처(실데이터 추정, 문헌, 임의 가정)를 표로 밝힌다. 그리고 "시뮬레이션에서의 정책 우열은 가정 하에서만 성립한다"고 명시한다. 시뮬레이터는 누수 테스트에도 다시 쓸 수 있다. 누수 피처를 넣었을 때 성능이 비현실적으로 좋아지는지 확인하는 용도다.

### 6.4 LAYER7 베타에서 무작위화된 추천으로 실제 효과를 잰다

인과 효과에 가장 가까운 근거는 LAYER7 자체 베타다. 출시 초기의 결정론적 추천 로그(4.6절)로는 노출 확률이 0 또는 1이라 정책 효과를 추정할 수 없다. 그래서 이 절의 무작위화는 평가 설계를 확정하는 단계에서 도입한다. 플랫폼은 종료 시각을 강제할 수 없고 추천만 할 수 있다. 그러므로 추천의 구성이나 순서를 무작위화하면, 추천을 종료 시각에 대한 도구변수로 쓸 수 있다(격려 설계). 이 경우 추천 추종률(1단계)과 성과(축약형)를 함께 보고한다. 같은 시간대에 끝나는 경매끼리 서로 잠식하므로 판매자 단위 A/B는 SUTVA를 위반한다. 그래서 시간 블록 단위로 정책을 번갈아 적용하는 스위치백 설계가 더 적합하다. Johari et al.(2022, Management Science, DOI 10.1287/mnsc.2021.4247)은 양면 플랫폼 실험에서 무작위화 단위에 따라 편향 방향이 달라진다는 것을 보였다 ([arXiv 2002.05670](https://arxiv.org/pdf/2002.05670v3)). 행동 공간은 1시간 슬롯 대신 3시간 블록 정도로 거칠게 잡아 성향 확률이 너무 작아지지 않게 한다. 노출된 후보, 순서, 확률, 실제 선택, 결과를 모두 로그로 남기면 obp로 IPS·SNIPS·DR 평가를 할 수 있다 ([Open Bandit](https://arxiv.org/abs/2008.07146)). 다만 이 추정량이 참값을 회복하는지는 6.3절 시뮬레이터의 합성 로그로 먼저 검증한다.

## 7. LAYER7 최종 권고안

### 7.1 권장 데이터셋과 용도

백엔드 개발자 한 명에게 권하는 데이터 구성은 여섯 가지다. 각각 용도를 좁게 정한다. **Jank & Shmueli eBay 데이터**(Kaggle `auction.csv`와 Drive의 Palm 158·Curve Clustering)는 막판 입찰 창 길이, 입찰자의 경매 간 이동, 공급 충돌 측정 절차를 설계하는 데 쓴다. 3일 경매 148건은 LAYER7의 72시간 경계를 점검하는 데 쓴다. **MaxSold**는 공급 밀집 피처를 대규모로 계산하는 연습, soft close가 실제 종료를 얼마나 미루는지 확인하는 용도, A 대 B 오프라인 비교 실험장으로 쓴다. 라이선스가 불확실하므로 재배포와 상업 이용은 하지 않는다. **Swoopo traces**는 시간대 활동 곡선의 모양을 비교하는 데만 쓴다. **eBayAuctions(DMBA)**는 중복을 제거한 뒤 요일 기준선의 정상 작동 점검(sanity check)에만 쓴다. Pokémon 시세 참조(CC BY 4.0)는 유사도와 가격대 구간용 보조 자료다. **ShopGoodwill(`ebay-sold-comps`)**은 수집품 품목에서 종료 시간대·공급 밀집과 입찰 수의 연관을 판매자 효과를 통제해 확인하는 탐색 분석에만 쓰고, 그 수치를 추천 가중치로 쓰지 않는다. 시간대(UTC/PT)를 먼저 확정하고, 중복 96행을 제거하고, 결과에 "낙찰분만"이라는 한계를 명시한다. 같은 저장소의 eBay 570행은 날짜만 있고 eBay 약관 문제가 있어 쓰지 않는다.

### 7.2 알고리즘과 ML 도입 판단: 규칙 기반으로 출시하고 ML은 조건부로 교체한다

**출시 알고리즘은 4.4–4.7절의 규칙·점수 기반 A로 한다.** 첫 버전은 4.7절의 보수적 기본 정책과 4.6절의 **구간 분산형** 결정론적 TOP 3다. 카테고리별 데이터 충분성과 최소 순위 안정성이 확보되면 4.4절 전체 점수식과 **점수 우선형** TOP 3(`activity-v1`)로 넘어간다.

**UX는 알고리즘이 실제로 계산한 것만 말해야 한다.** 추천 API는 `policy_version`, `factors_used`, 후보별 `reasons` 코드, 화면 라벨("추천 근거 부족/보통/충분")을 함께 반환한다(4.7절). 프론트엔드는 코드를 정해진 문구 템플릿에 넣기만 한다. 그래서 `conservative-v0`에서는 심야·충돌 설명만 나오고, 구매자 활동 문구는 `activity-v1`에서만 나온다. 화면 라벨은 데이터 충분성과 순위 안정성만 나타낸다. "이 시각에 끝내면 더 비싸게 팔린다" 같은 성과 주장은 하지 않는다. 그런 문구는 6.4절 검증으로 `effect_validation`이 `verified_positive`가 된 뒤에, 검증된 범위 안에서만 검토한다. 등록 단계에서는 `RECOMMENDED`로 선택한 경우에만 4.5절의 재검증 결과에 따라 "추천 이후 비슷한 경매가 늘었다"는 안내와 원래 시각 유지 선택지를 제공한다. `MANUAL` 입력은 기간 검증 후 등록하고, 추천 순위 변화로 확인을 강제하지 않는다. 공개 데이터와 문헌이 정당화할 수 있는 수준이 딱 여기까지다. 구현과 디버깅이 쉽고, 추천 이유("이 시간대는 활동이 많고 비슷한 경매가 2건뿐")를 판매자에게 설명할 수 있다. **ML(B)은 출시하지 않는다.** 대신 MaxSold에서 A와 비교하는 오프라인 실험을 캡스톤 결과물로 제시한다. B로 교체하는 조건은 세 가지다. LAYER7 자체 데이터가 무작위화된 로그와 함께 충분히 쌓여야 하고, 그룹·시간 CV에서 B가 GLM 기반 A를 의미 있게 이겨야 하며, 정책 평가(OPE 또는 스위치백)에서도 우위가 확인돼야 한다. 필요한 경매 수를 지금 확정할 근거는 없다. 학습 곡선이 수렴하는 지점에서 판단한다. 데이터가 적을 때 ML을 앞세우면 "ML이라서" 채택한 꼴이 된다. 소규모 데이터에서 부스팅이 GLM보다 낫다는 근거는 없다.

### 7.3 추가 데이터를 합법적으로 얻는 길: 거의 닫혀 있고 자체 수집만 열려 있다

| 경로 | 현황 | 판정 |
|---|---|---|
| eBay Finding/Shopping API | 2025-02-04 폐기, Browse API로 대체 ([eBay deprecation](https://developer.ebay.com/docs/api-deprecation)) | 불가 |
| eBay Browse API | 진행 중인 리스팅만 제공. 라이선스가 ML 학습·합성 데이터·bulk 다운로드를 금지 ([License](https://developer.ebay.com/join/api-license-agreement)) | 실시간 표시용으로만 가능 |
| eBay Marketplace Insights | 선정된 파트너 전용, 문서 자체가 로그인 뒤에 있음 ([overview](https://developer.ebay.com/api-docs/buy/marketplace-insights/static/overview.html)) | 사실상 불가 |
| eBay robots.txt / User Agreement | 허가 없는 자동 접근 금지, AI 크롤러는 `Disallow: /` ([robots.txt](https://www.ebay.com/robots.txt)). 2026-02 개정에서 LLM 봇 금지 추가(2차 자료, [Value Added Resource](https://www.valueaddedresource.net/ebay-bans-ai-agents-updates-arbitration-user-agreement-feb-2026/)) | 스크래핑 불가 |
| eBay 서면 허가 | Restricted API 조항에 사전 서면 동의 예외가 있음 | 요청은 가능하나 승인 여부 미지수 |
| TCGplayer | 신규 API 발급 중단 ([docs](https://docs.tcgplayer.com/docs/getting-started)) | 불가 |
| PriceCharting | 유료, 현재가만, 내부 이용 한정(검색 요약 기준, 원문 403, [API 문서](https://www.pricecharting.com/api-documentation)) | 학습용으로 부적합 |
| 야후옥션 | Web API 2020-01 종료 ([changelog](https://developer.yahoo.co.jp/changelog/auctions.html)). robots.txt가 낙찰 검색 `/closedsearch`를 Disallow ([robots.txt](https://auctions.yahoo.co.jp/robots.txt)) | 불가 |
| Heritage / Goldin / 130point / BaT | robots.txt는 결과 페이지를 대체로 허용(Heritage `Crawl-delay: 15`). 약관은 미확인. Heritage는 2016년 경쟁사의 스크래핑을 약관 위반으로 소송함 ([NBC DFW](https://www.nbcdfw.com/news/local/auction-houses-face-off-in-website-data-scraping-lawsuit/2033762/)) | robots 허용 ≠ 약관 허가. 권하지 않음 |
| 번개장터 | 일반 크롤러는 대부분 허용, GPTBot·ClaudeBot 등 AI 학습 크롤러는 `Disallow: /` ([robots.txt](https://m.bunjang.co.kr/robots.txt)) | AI 학습 목적 수집을 원하지 않는다는 신호 |
| 온비드 OpenAPI | 무료, 이용허락 제한 없음(문서상). 서비스키 필요, 응답 필드는 미확인 ([data.go.kr](https://www.data.go.kr/data/15157222/openapi.do)) | 합법적이지만 봉인입찰 공매라 적합도 낮음 |
| NBER Best Offer, SIGIR eCom 2019 | 연구 목적 공개·신청형 ([NBER](https://www.nber.org/research/data/best-offer-sequential-bargaining), [SIGIR eCom](https://sigir-ecom.github.io/ecom2019/data-task.html)) | 보조 자료. eCom 데이터를 지금 받을 수 있는지는 미확인 |
| 논문 저자에게 요청 | Swoopo(저자 문의 안내), 경매 사기 연구 저자 등 | 시도해 볼 가치 있음. 거절될 수 있음 |
| **LAYER7 자체 베타** | 동의 기반 수집, 가명처리, 무작위 추천 | **유일하게 깨끗하고 인과적인 경로** |

한국 법 쪽에서는 세 가지 위험이 남는다. 첫째, 형사 책임은 여기어때 대 야놀자 사건(대법원 2022. 5. 12. 선고 2021도1533)에서 정보통신망 침입, DB제작자 권리 침해, 업무방해 모두 무죄로 확정됐다. 그러나 같은 사안의 민사(서울중앙지법 2018가합508729)에서는 부정경쟁방지법상 성과물 무단사용으로 책임이 인정됐다 ([법무법인 세종](https://www.shinkim.com/kor/media/newsletter/1843), [대법원 자료](https://www.scourt.go.kr/sjudge/1652779958317_183238.pdf)). 둘째, 잡코리아 대 사람인 사건에서는 반복·체계적 복제가 DB제작자 권리 침해로 인정됐다. 이는 2차 자료 기준이며 배상액은 자료마다 다르다 ([nepla](https://www.nepla.ai/wiki/지식재산/부정경쟁/데이터-부정사용-rv5n72p1g8zm)). 셋째, 입찰자 ID는 다른 정보와 쉽게 결합되면 개인정보가 된다. 개인정보보호위원회의 2024-07-17 안내서는 공개된 개인정보의 처리 근거로 "정당한 이익"을 제시하면서 목적의 정당성과 이익형량을 요구했다 ([법무법인 세종](https://shinkim.com/kor/media/newsletter/2517)). 시민단체는 이 해석을 비판했다 ([참여연대](https://peoplepower21.org/publiclaw/1978869)). 종료 시각 추천에는 개별 입찰자 ID가 필요 없다. 시간대별 입찰 수와 고유 입찰자 수 같은 집계값이면 충분하다. 그러므로 외부 데이터의 ID는 분석 단계에서만 쓰고 저장하지 않는다. LAYER7 자체 데이터는 가명 처리한다. 실제 수집 전에는 지도교수나 법무 검토를 받는다.

### 7.4 작업 순서

| 단계 | 작업 | 산출물 |
|---|---|---|
| 1 | 이벤트 로그 스키마 설계: 조회, 입찰, 접속, 경매 등록·종료 확정, **추천 노출(후보, 순서, 확률)**. 모든 시각은 UTC로 저장 | 로그 테이블, 인덱스 `(end_at, category_id, status)` |
| 2 | 공개 데이터 분석 노트북: Jank & Shmueli 막판 입찰 분포, Palm 158 시간대·동시 종료, MaxSold 슬롯 밀집과 **`bid_time` 시간대 분포(미집계 항목)**, ShopGoodwill 판매자 고정효과 NB(입찰 수 ~ 종료 시간대 + 같은 키워드 ±30분 종료 수, 탐색용이며 가중치로 쓰지 않음), DMBA 중복 제거 후 요일 기준선 | 사전값 표(파라미터, 출처, 불확실성) |
| 3 | 규칙 기반 A 구현: 후보 격자 생성 → `Â_c(t)`(사전값 + 수축) → 시점 고정 `Ĉ_i(t)` → 점수 → 정책별 TOP 3(`conservative-v0`: 구간별 하나·최소 3시간, `activity-v1`: 점수순·최소 3시간) → 추천·선택 로그. 첫 버전은 4.7절 보수적 기본 정책(심야 회피 + 기존 유사 경매 충돌 회피, "추천 근거 부족" 표시). 응답에 `policy_version`·`factors_used`·`reasons` 포함. 등록 API에 `selection_source`(`RECOMMENDED`/`MANUAL`) 분기와 4.5절 재검증(추천 선택만 스냅숏 비교, 수동 입력은 기간 검증, 원래 시각 유지 허용) | 추천 API, 단위 테스트(72시간 경계, KST/UTC, 서머타임 지역 데이터) |
| 4 | 시뮬레이터: 비동차 Poisson 도착, 막판 입찰, 대체재 단일 입찰. 정책 5종과 민감도 격자 | 정책 비교 그림, 파라미터 출처 표 |
| 5 | MaxSold 오프라인 실험: 기준 GLM + A 점수 대 LightGBM, 시간 분할, 학습 곡선, 보정 진단 | A 대 B 비교 보고 |
| 6 | 베타 운영: 결정론적 추천으로 시작해 추천·선택 로그를 쌓고, 평가 설계를 확정한 뒤 무작위화(TOP 3 구성·순서)나 스위치백을 도입, 추종률 측정 | 실제 로그 |
| 7 | 재추정: 판매자 고정효과 NB로 β 재추정, obp로 OPE. 교체 조건을 충족할 때만 B 도입을 검토 | 최종 평가 |

### 7.5 예상되는 기술적 난관

장밋빛 그림만 있는 것은 아니다. **콜드스타트**가 가장 크다. 출시 시점에는 활동 곡선이 외국·과거 데이터의 모양뿐이고, 그 데이터마저 시간대가 불확실하다. 확실한 사전값은 "심야 회피" 하나다. **유사도 정의**도 어렵다. 포켓몬 카드는 세트, 레어도, 등급(PSA 10 대 무등급)에 따라 대체 가능성이 크게 달라지는데, 이를 정의할 공개 기준 데이터가 거의 없다. **쏠림과 순차 갱신**도 문제다. 동시에 추천받은 판매자들에게 같은 슬롯이 추천되는 경쟁 조건(race condition)이 생긴다. MVP에서는 잠금이나 슬롯 예약 대신 추천 선택 시 등록 재계산과 재추천 안내로 다룬다(4.5절). 직접 입력 시에는 추천 스냅숏 비교를 강제하지 않는다. 거의 동시에 들어온 등록끼리의 겹침은 남는데, 중복은 금지 대상이 아니므로 허용하고 로그로 빈도를 잰다. 추천 후 다른 판매자가 같은 슬롯으로 몰리는 미래 공급은 본질적으로 불확실하다. **소표본 통계**도 걸림돌이다. 베타 규모에서는 β가 0과 구별되지 않을 가능성이 높으므로, 결과를 "효과 없음"이 아니라 "검정력 부족"으로 보고해야 한다. **마감 규칙과의 상호작용**도 있다. soft close를 도입하면 실제 종료가 예정보다 늦어지므로(MaxSold 중앙값 21분), 추천 슬롯의 의미와 충돌 커널 폭을 다시 정의해야 한다. **시간대와 서머타임**은 데이터 결합 단계의 실수가 가장 많이 나는 지점이다. 끝으로 **법·약관 리스크** 때문에 외부 데이터를 늘리는 쉬운 길이 대부분 막혀 있다. 이 사실을 일정 계획에 미리 반영해야 한다.

정리하면 다음과 같다. 공개 데이터는 LAYER7에 "어떤 변수를 어떻게 재야 하는가"를 알려준다. "그 변수가 얼마나 중요한가"는 알려주지 못한다. 공개 데이터의 진짜 가치는 정답을 주는 데 있지 않다. 출시 첫날부터 추천과 선택을 기록하고, 평가 단계에서 무작위화를 더할 수 있는 측정 장치를 설계하게 만드는 데 있다. 그 장치가 쌓은 데이터만이 규칙 기반에서 ML로 넘어갈 시점을 정당화할 수 있다.


---

### 문서 개정 이력 (v4, 2026-10-30)

이번 개정은 **공개 데이터셋의 원자료나 논문 실증 결과를 재검증한 개정이 아니라**, 기존 조사 보고서의 LAYER7 구현 정책과 내부 정합성을 보완한 것이다. 주요 변경은 (1) 56개 시간 셀 일률 충족 조건을 후보별 유효 표본·활동 사용자·관측일 기반 판단으로 변경, (2) 추천 근거 부족/보통/충분의 상호 배타적 판정과 정책 전환 조건 정리, (3) 추천 선택과 수동 입력의 등록 API·재검증 분리 및 가중 충돌 임계값 명시, (4) `conservative-v0`와 `activity-v1`의 TOP 3 선택 우선순위 구분, (5) 7.1절 데이터 구성 여섯 가지·7.4절 시뮬레이션 정책 다섯 가지로 숫자 정합성 수정, (6) 구매자 활동 로그의 관측 단위와 정규화 주의사항 추가다. 수치 임계값은 초기 운영 **예시**이며 실제 데이터로 보정해야 한다.
