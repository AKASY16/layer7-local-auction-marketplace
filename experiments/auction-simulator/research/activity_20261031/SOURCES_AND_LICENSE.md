# 신규 자료 출처·사용 범위

## Retailrocket

- 제공자: Retailrocket, 공식 데이터 카드 표시 작성자 Roman Zykov.
- 출처: https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset
- 확인일: 2026-10-31. 공식 카드 검색 색인에서 스키마 설명·규모·라이선스를 확인했다. 직접 HTML 및 API는404를 반환했으므로 실시간 API 메타데이터나 제공자 원본 체크섬 확인이라고 표현하지 않는다. 조회 실패는 source_metadata/retrieval.json에 보존한다.
- 공식 카드 표시 라이선스: **CC BY-NC-SA 4.0**. [공식 조건](https://creativecommons.org/licenses/by-nc-sa/4.0/): 저작자·출처·라이선스 및 변경사항 표시, 비상업적 이용, 개작물 공유 시 같은 조건. 이번은 로컬 연구 분석이며 외부 공개·배포는 수행하지 않았다. 파생 활동 자료를 공유할 때도 출처·변경 내역과 해당 조건을 유지해야 한다. 향후 상업 서비스에 자료/파생 프로파일을 포함할 권한은 이번 연구 사용으로 확보되지 않는다. 별도로 작성한 독립 분석 코드 전체에 동일 라이선스가 자동 적용된다고 판단하지 않는다.
- 로컬 원본: data/external/activity_profiles/retailrocket/events.csv, 94,237,913 bytes, SHA256 `3745aa83238b1e6d44d8fda209807899f420084398f94ddf745f3cbcfecbf9e7`.
- 원본은 사용자가 제공한 CSV를 바이트 변경 없이 이동했다. 제공자의 게시 행수/이벤트 수/visitor 수와 일치하지만 제공자 체크섬이 없어 다운로드 원본과의 암호학적 동일성을 확인했다고 주장하지 않는다.
- 공식 설명은 Unix timestamp이며 로컬 숫자는 밀리초 단위의13자리다. UTC로 읽고 KST 표시는 같은 순간의 +9시간 변환으로만 해석한다. 쇼핑몰 국가·사용자 지역·현지 시각은 미확인이다. 국가를 주장하는 다른 사이트의 추정을 공식 확인으로 채택하지 않았다.
- 공급된 파일은 events.csv뿐이다. item_properties 및 category_tree가 없고 숫자 item ID에 의미 라벨도 없으므로 수집품을 식별할 수 없다. 전체 일반 이커머스 자료로만 취급한다.
- 변경 내역: 원본 자체 변경 없음. 주간 경계 표본 분리, 날짜–시간 distinct 집계, 평균1 정규화, 불확실성 및 민감도 파생 결과 생성. 집계 프로파일은 쇼핑 활동의 상대적 형태이며 경매 입찰/한국 수요로 변환한 실측값이 아니다.

## Simonsohn

- Uri Simonsohn(2010), *eBay's Crowded Evenings: Competition Neglect in Market Entry Decisions*, Management Science56(7):1060–1073, https://doi.org/10.1287/mnsc.1100.1180 .
- 새 제공 파일은44쪽 working manuscript, 기존 연구 폴더의 출판본은14쪽이다. 같은 연구의 두 판본이며 독립 증거2개로 세지 않는다. 제공 원고의 이론 부분과 출판본의 관측 표를 구분했다.
- 새 파일 SHA256 `29f80542e45f680b21980b5a165d583dc1c385b6f90371b8f69c750c33249f69`(274,069 bytes).
- 논문 전체를 공개 재배포할 라이선스를 확보한 것으로 간주하지 않는다. 로컬 열람·표 수치의 출처를 밝힌 분석만 수행하고 외부 업로드는 하지 않았다. 원자료는 제공되지 않아 재추정하지 않았다.

## 이동 기록

| 제공 위치(1031 내부) | 현재 위치 | 용도 |
| --- | --- | --- |
| Retailrocket Recommender System Dataset.csv | data/external/activity_profiles/retailrocket/events.csv | 상대 쇼핑 활동 형태·위상·자료 변동 검증 |
| eBay's Crowded Evenings Competition Neglect in Market Entry Decisions.pdf | research/papers/simonsohn_2010_revalidation/ebays_crowded_evenings_2010.pdf | 활동 수요와 공급 혼잡 개념의 원문 검토 |

이동 전후 해시가 일치한다. 기존 baseline·audit·V2 실험 자료는 이동하거나 덮어쓰지 않는다.
