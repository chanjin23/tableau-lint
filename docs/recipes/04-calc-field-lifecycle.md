# 레시피 04 — 계산 필드 변경·삭제 (수명주기)

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 |
| UI 경로 | 데이터 패널 > 필드 우클릭 > 편집/이름 바꾸기/삭제 |
| 근거 | MA_008 `35911cd` `e6a02cc` `98fb49c` `6958d25` `b6256cf` `ae0f567` `35db682` `a248ae3` `ad7cb3f` `b63ddda` |
| Tableau | 2026.1 |

## 수식 편집

`column[@caption='…']/calculation@formula`만 교체. `name`·caption 불변 → 참조 전부 유지.

- 주석은 수식 문자열의 일부다 — `// …` 선두 추가 가능 (`b63ddda` `57e556a`)
- 빈 껍데기(`formula=''`)에 수식 채우기 = `@formula`만 채움, `<column>` 불변 (`35db682`)
- 결과 타입이 바뀌면 `@datatype`/`@type` 동반 전환 — 라벨(string·nominal)→집계(real·ordinal) (`1d2aa95`)

## 테이블 계산 ↔ LOD 전환 (`35911cd`·`146f488` 양방향 관찰)

수식만 바꾸면 안 된다. 동반 변경 3종:

1. `column`과 `column-instance` **양쪽**에서 `<table-calc @ordering-type>` 추가/제거
2. `column-instance @derivation` `'User'`↔`'Attribute'` — 인스턴스 name도 `[usr:…:qk]`↔`[attr:…:qk]`
3. 그 인스턴스를 참조하는 `filter`/`slices`도 새 표기로 함께

## 개명

`@caption`만 변경. **`name`은 유지 → 참조가 안 깨진다** (`e6a02cc` C_B_재고→C_B_월별재고추이).
같은 필드를 쓰는 워크시트마다 `datasource-dependencies/column@caption`도 함께 (`b6256cf` — 5필드 = column 13곳).

## 삭제

`<column>` 블록(자식 `<calculation>` 포함) 통째 제거 (`98fb49c` `7f4e665` `b6256cf`).

- 참조 0 확인 후 지운다 — `98fb49c`는 "참조 0곳" 확인하고 지웠다. 참조가 남으면 dangling (lint ②)
- 필드 **교체**(삭제+신규)면 쓰던 시트의 `encodings`·`datasource-dependencies`의
  column·column-instance를 새 name으로 전부 갱신 (`6958d25`)

## 복사본 name 발급 함정 (`a248ae3`)

UI 복제 시 `name`은 **원본 caption 기반**으로 발급된다 — caption을 바꿔가며 연쇄 복제하면
name과 caption이 어긋난다 (`C_L_MTD-1_실적`의 내부 name이 `[C_L_MTD-2_실적(복사본)_…]`).
**무해하다** — 참조는 name으로 하므로. AI는 어긋난 name을 "고치려" 들지 말 것.

## 별칭 (`ad7cb3f`)

`column` 자식으로 `<aliases>/<alias @value>`. 측정값 이름의 별칭은 **정적 문자열** —
매개변수 연동 불가 (`1d2aa95` 한계 관찰).

## 재저장 검증

수식·caption 변경은 제자리 — 정규화 없음. 신규/삭제로 정렬이 깨지면 위치 재배치
(name 오름차순, E2E-1). twb-lint: `calc.field_refs`(②)·`calc.functions`·`calc.aggregation`.
