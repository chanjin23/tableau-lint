# 기능 커버리지 대조 — 레시피가 덮는 곳과 비는 곳

> [`../08-authoring-recipes.md`](../08-authoring-recipes.md) §7의 산출물.
> "레시피 전량 변환 후 Tableau 기능 전체 리스트를 만들어 미관찰 항목을 표시한다"의 그 리스트다.

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 1차 (2026-08-10) |
| 근거 | 실파일 **93개** 전수 스캔 — XML 태그 **198종** · `docs/recipes/01~24` 대조 |
| 재현 | `.venv/Scripts/python tools/scan_surfaces.py --root 'C:/dev/JW/2.개발' --root 'C:/dev'` |
| 다음 | C군(표본 0)을 소유자 관찰 모드로 공급 · B군은 관찰 없이 형태만 선기록 |

## 왜 태그 축인가

기능 리스트를 UI 메뉴나 기억으로 만들면 근거 등급이 전부 `추정`이 된다(08 §5).
대신 **실파일에 실제로 나타난 XML 태그**를 세고, 레시피가 그것을 언급하는지 본다.
경로가 아니라 태그로 세는 이유는 대시보드 `zone`이 12겹까지 중첩돼서
경로 축으로는 같은 기능이 표면 수십 개로 불어나기 때문이다.

**한계 — 이 스캔은 "결과형"만 본다.** 태그가 있다는 것은 형태를 알 수 있다는 뜻이지
**동반 변경(무엇을 같이 고쳐야 하는가)을 안다는 뜻이 아니다.** 동반 변경은
조작 전/후 diff에서만 나온다. 그래서 아래 B군도 레시피로 완성되려면 결국 관찰이 필요하고,
관찰 없이 쓸 수 있는 것은 **형태 절반**뿐이다.

---

## A. 커버됨 — 레시피 01~24

| 표면 | 파일 | 레시피 |
|---|---|---|
| `workbook`·`preferences`·`document-format-change-manifest` | 93 | 20 |
| `datasource/connection`·`relation`·`object-graph`·`metadata-record` | 92 | 21 · 17 |
| `column`·`calculation`·`column-instance`·`table-calc` | 93 | 01 · 04 · 05 |
| `column/members`·매개변수 | 80 | 02 · 06 |
| `worksheet`·`window`·`thumbnail` 3곳 | 92 | 09 · 22 |
| `table/cols`·`rows`·`panes/pane`·`view/breakdown` | 92 | 11 · 22 |
| `filter`·`groupfilter`·`slices` | 86 | 12 |
| `encodings/color`·`text` · `mark@class` · `mark-sizing` · `customized-label`·`customized-tooltip`·`tooltip-style` | 92 | 13 |
| `manual-sort`·`computed-sort` | 76 | 14 |
| `dashboard/zones/zone`·`zone-style`·`devicelayout` | 81 | 03 · 15 · 16 · 19 |
| `style-rule`·`format`·`run`·`formatted-text` | 81 | 19 · 13 |
| `folders-common`·`datasource/style-rule/encoding/map` | 77 | 18 |
| `extract`·`refresh` | 70 | 17 |
| `actions/edit-parameter-action` | 78 | 07 |
| `actions/action[command='tsc:brush']` | 60 | 08 |
| `group[user:ui-builder]` (사용자 집합) | 58 | 23 |
| `group[user:ui-vit-column]` (도구 설명 뷰) | 2 | 24 |
| `window/cards/edge/strip/card` (범례 카드) | 92 | 10 |
| `viewpoint/highlight/color-one-way` | 90 | 22 |

---

## B. 표본은 있는데 레시피가 없다 — **관찰 없이 형태 절반은 지금 쓸 수 있다**

| 표면 | 파일 | 무엇 | 우선 |
|---|---|---|---|
| `edit-group-action` + `add-or-remove-marks` + 매니페스트 `GroupAction`·`GroupActionAddRemove` | **55** | **집합 동작** — T3 직결 | **1** |
| `encodings/lod` (`@column`) | **77** | 마크 **세부 수준** 인코딩. 레시피 13에 아예 없다 | **2** |
| `field-sort-info`/`field-sort-custom-order` | 30 | 데이터 원본 필드 사용자 지정 정렬 순서 | 3 |
| ~~`viewpoint/selection-collection`~~ | 49 | **판별 끝 — 신호다.** 저장 시점의 마크 선택 상태가 박제된 것이고, 남아 있으면 최초 로드 시 디밍으로 보인다. 배포본에서는 제거한다 → 레시피 09 (MA_011 260812, 5건 제거로 디밍 소멸·다른 동작 무변화) | ✅ |
| `repository-location` | 26 | 서버 게시 흔적. 저작 시 써야 하는지 미판정 | 5 |
| `default-map-tool-selection` 19 · `map-pri` 8 | 19 | 지도 도구·색상 우선순위 | 6 |
| 매니페스트 `PatternedLineMarks` | 14 | 선 마크 패턴 | 7 |
| `worksheet/layout-options/title` | 11 | 워크시트 제목 사용자 지정 | 8 |
| `encodings/tooltip` (`@column`) | 8 | 도구 설명 **인코딩** — `tooltip-style`과 다른 것 | 9 |
| `shelf-sorts/shelf-sort-v2/sort-filter-info` + 매니페스트 `IntuitiveSorting`·`IntuitiveSorting_SP2` | 3 | 신형 정렬(선반 정렬) | 10 |
| 워크시트 수준 `style-rule/encoding/color-palette` | 3 | 시트 팔레트 (레시피 18은 데이터 원본 수준) | 11 |
| `action[command='tsc:tsl-filter']` + `link` | **2** | **필터 동작** — 규칙 ⑬이 어휘만 알고 레시피는 없다 | 12 |
| `object-graph/relationships/relationship` + `expression`·`first/second-end-point` | **2** | **관계(조인)** | 13 |
| `calculation[@class='categorical-bin']` + `column/calculation/bin` | 2 | 구간(bin) 필드 | 14 |
| `column/range` (`@granularity`·`@min`·`@max`) | 1 | 범위형 매개변수 허용값 | 15 |
| `table/mark-labels/mark-label/label-position` | 1 | 개별 마크 레이블 — `?` 신호 `35b2505`의 실체 | 16 |

---

## C. 표본 0 — **소유자 관찰 없이는 아무것도 못 쓴다**

실파일 93개 · MA_008 커밋 46개 **양쪽 모두 0건**. 태그 이름조차 나타나지 않는다.

| 기능 | 확인한 태그 | 비고 |
|---|---|---|
| **페이지 선반** | `pages`·`page` | 01 v2.0 T4가 명시적으로 포함하는 표면인데 표본이 없다 |
| **참조선·추세선·분포 밴드** | `reference-line`·`trend-lines` | 규칙 ⑪이 표면으로 선언만 해 뒀다 |
| ~~**총계/소계**~~ | ~~`totals`·`total`~~ | **C군에서 내린다** — 태그가 아니라 `<rows>`의 속성이었다(`total='true'`·`onTop='true'`). 00-inventory `c3ad388`의 "속성 수준 관찰"이 맞았다. 형태는 레시피 11에 있다 (MA_011 260812). **총계 계산 방식·행 총합계·소계는 여전히 미관찰** |
| **스토리** | `story`·`stories` | |
| **주석** | `annotation` | |
| **계층(드릴)** | `hierarchy`·`drill-path` | |
| **그룹 필드** | — | `group` 5모양 전부 집합·동작·도구설명이다. 그룹 필드형 없음 |
| **URL 동작 · 시트 이동 동작** | `command=` | 명령은 `tsc:brush`·`tsc:tsl-filter` 2종뿐 |
| **마크 인코딩 size·shape·detail·path** | `encodings/*` | 실재 자식은 `color`·`text`·`lod`·`tooltip` 4종뿐 |
| **예측·클러스터** | `forecast`·`cluster` | |
| 여백 4면 개별 지정 | — | UI-XML매핑.md 미관찰란과 동일 |

---

## 00-inventory 정정 3건

이 스캔이 인벤토리의 "표본 0" 판정 셋을 뒤집었다. **코퍼스(MA_008 커밋)에 없다는 것과
실파일에 없다는 것은 다르다** — 인벤토리는 앞의 것만 셌다.

| 인벤토리 서술 | 실측 | 결과 |
|---|---|---|
| 집합 동작 — "여전히 표본 0" | `edit-group-action` **55개 파일 108건** | 형태는 지금 쓸 수 있다. 동반 변경만 미지 |
| 필터 동작 — "미관찰" | `tsc:tsl-filter` **2개 파일 14건** | 규칙 ⑬이 이미 어휘를 갖고 있다 |
| 조인/데이터 혼합 — "실파일 106개에도 표본 0" | `relationship` **2개 파일 6건** | 스캔 대상이 93개로 정정됨(중복 제거) |

---

## 소유자에게 넘길 관찰 목록 (C군 우선순위)

한 저장 = 한 조작(E2E-3에서 확인된 유일하게 통하는 방식):

1. **페이지 선반** — 차원 하나를 페이지에 올리고 저장. T4 표면인데 표본이 0이다
2. **참조선** — 연속형 축에 평균선 하나. 규칙 ⑪이 선언만 해 둔 표면
3. **마크 인코딩 size·shape** — 필드를 크기·모양에 하나씩
4. **그룹 필드** — 차원 멤버 2개를 묶어 그룹 생성
5. **총계/소계** — 분석 창에서 총계 켜기
6. **URL 동작 · 시트 이동 동작** — 명령 2종 외 나머지
7. 계층 · 주석 · 스토리 — T1~T4 밖이라 후순위
