# 레시피 12 — 필터 (categorical · quantitative · groupfilter 속성)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 필드를 필터 선반에 드래그 > 편집 |
| 근거 | MA_008 `7353886` `529e436` `146f488` `e6a02cc` `358c382` `b63e1b1` `57e556a` · 2026-08-10 통제 관찰 `관찰_01`~`05` |
| Tableau | 2026.1 · 2026.1.1 |

## categorical (`7353886`)

```xml
<filter class='categorical' column='[none:Calculation_4888733706485760:nk]'>
  <groupfilter function='member' level='[none:…:nk]' member='true' … />
</filter>
```

- `column`은 인스턴스 표기
- ⚠️ **`member`의 따옴표는 필드의 `datatype`이 정한다** — boolean은 **맨값**(`member='true'`),
  string은 **따옴표**(`member='&quot;노트북&quot;'`). 실측 138개 파일:
  boolean 맨값 5,923 : 따옴표 0 · string 따옴표 5,569 : 맨값 0.
  boolean을 감싸면 파일은 열리지만 Tableau가 *"필터를 구문 분석하는 동안 오류가
  발생했습니다. 필터를 무시합니다"*로 **그 필터를 버린다** — 걸러져야 할 행이 남아
  틀린 숫자가 나온다. 규칙 ⑦-f가 잡는다 (05 F5-k)
- 멤버 여러 개면 `groupfilter function='union'` 아래 member들.
  **단일 멤버로 좁히면 union 껍데기가 사라지고 member 하나만 남는다** (`e6a02cc`)

## quantitative (`7353886` `529e436`)

```xml
<filter class='quantitative' column='[usr:Calculation_4888733707464705:qk]' included-values='in-range'>
  <min>1</min>
  <max>1</max>
</filter>
```

시트 복제 시 필터 값이 그대로 상속된다 — min/max 갱신을 잊으면 전 시트가 같은 값
(`529e436`이 그 수정).

## groupfilter의 `user:` 속성 — UI 경로 지문

**같은 결과라도 UI 경로에 따라 속성 조합이 다르다** (`358c382`):

| UI 경로 | 속성 |
|---|---|
| 목록에서 선택(수동) | `user:ui-manual-selection='true'` `user:ui-manual-selection-all-when-empty='true'` (`e6a02cc` — 단일 멤버로 좁힐 때 새로 붙음) |
| 필터 편집 대화상자 다른 경로 | `user:ui-domain='relevant'` `user:ui-enumeration='inclusive'` `user:ui-marker='enumerate'` |

복제 판별에도 쓰인다 — `7e15b84`는 이 속성의 유무로 어느 시트에서 복제됐는지 역추론했다.
AI 저작 시: 관찰된 조합 중 하나를 그대로 쓴다. 섞지 말 것(`추정` — 섞은 관찰 없음).

## `<slices>`가 짝으로 따라온다 (통제 관찰 2026-08-10)

**워크시트 필터는 `<filter>` 하나로 끝나지 않는다.** 바로 뒤에 `<slices>`가 붙는다:

```xml
<filter class='categorical' column='[federated.…].[none:품목:nk]'>
  <groupfilter function='union' user:ui-domain='database'
               user:ui-enumeration='inclusive' user:ui-marker='enumerate'>
    <groupfilter function='member' level='[none:품목:nk]' member='&quot;노트북&quot;' />
    <groupfilter function='member' level='[none:품목:nk]' member='&quot;모니터&quot;' />
  </groupfilter>
</filter>
<slices>
  <column>[federated.…].[none:품목:nk]</column>
</slices>
```

- 위치는 `<view>` 안, `<datasource-dependencies>` **다음** · `<aggregation>` **앞**
- `<filter @column>`과 `<slices><column>`은 **같은 2단 표기**로 일치해야 한다
- `<filter>`가 여러 개면 `<slices>`에도 그만큼 `<column>`이 쌓인다
- `groupfilter@level`은 **1단 인스턴스 표기**(`[none:품목:nk]`)다 — `filter@column`의
  2단 표기와 다르다 (07 G8 · 규칙 ⑦-d)

## NULL 제외 — `except` + `level-members` (MA_011 260812)

계산 필드가 `NULL`을 돌려주는 행을 빼는 필터. 실무에서 매우 흔한데 위 `union`/`member`
계열과 형태가 다르다.

```xml
<filter class='categorical' column='[federated.…].[none:Calculation_1238633066082307:nk]'>
  <groupfilter function='except'
               user:ui-domain='relevant' user:ui-enumeration='exclusive' user:ui-marker='enumerate'>
    <groupfilter function='level-members' level='[none:Calculation_1238633066082307:nk]' />
    <groupfilter function='member'        level='[none:Calculation_1238633066082307:nk]' member='%null%' />
  </groupfilter>
</filter>
```

읽는 법: `except(전체 멤버, {null})` — **첫 자식이 피감수**, 나머지가 감수.
NULL 멤버는 `member='%null%'`로 쓴다(따옴표 없음).

`user:` 3속성이 포함형과 다르다:

| | `ui-domain` | `ui-enumeration` |
|---|---|---|
| 포함형(`member`/`union`) | `database` | `inclusive` |
| **제외형(`except`)** | **`relevant`** | **`exclusive`** |

## 측정값 범위 · 날짜 범위 (`관찰_02`·`03`)

```xml
<!-- 측정값: 집계 인스턴스를 건다 -->
<filter class='quantitative' column='[federated.…].[sum:매출:qk]' included-values='in-range'>
  <min>500</min><max>1500</max>
</filter>

<!-- 날짜: 값이 # 로 감싸인다 -->
<filter class='quantitative' column='[federated.…].[none:기준월:qk]' included-values='in-range'>
  <min>#2026-01-01#</min><max>#2026-02-28#</max>
</filter>
```

**날짜 필터는 새 인스턴스를 만든다** — 뷰에 `[yr:기준월:ok]`가 있어도 필터는
`derivation='None'` `type='quantitative'`인 **`[none:기준월:qk]`**를 새로 발급받는다.
날짜를 연속 축으로 다루기 때문이다. 그 인스턴스가 `viewpoint/highlight`에도 자동 추가된다.

## 컨텍스트 필터 (`관찰_04`) — 속성 하나다

```diff
- <filter class='categorical' column='[federated.…].[none:품목:nk]'>
+ <filter class='categorical' column='[federated.…].[none:품목:nk]' context='true'>
```

**diff가 이 한 줄뿐이다.** `<slices>`도 `groupfilter`도 안 바뀐다.

## 데이터 원본 필터 (`관찰_05`) — 자리가 다르다

워크시트가 아니라 **`<datasource>` 안**에 들어간다. `<semantic-values>` 다음 ·
`<object-graph>` 앞:

```xml
<column datatype='string' name='[지역]' role='dimension' type='nominal' />
…
<filter class='categorical' column='[지역]' filter-group='2'>
  <groupfilter function='union' user:ui-domain='database'
               user:ui-enumeration='inclusive' user:ui-marker='enumerate'>
    <groupfilter function='member' level='[지역]' member='&quot;부산&quot;' />
    <groupfilter function='member' level='[지역]' member='&quot;서울&quot;' />
  </groupfilter>
</filter>
```

| 워크시트 필터와 다른 점 | |
|---|---|
| `column` 표기 | **1단 원시 이름** `[지역]` — 데이터 원본 한정자도 인스턴스 한정자도 없다 |
| `<slices>` | **없다** |
| `filter-group` | `'2'`가 붙는다 |
| 동반 변경 | 대상 필드의 `<column>` 정의가 데이터 원본에 실체화된다 |
| 워크시트 | **아무것도 안 바뀐다** |

## filter-group (`57e556a`)

`<filter class='categorical' column='…' filter-group='3'>` — 그룹 번호 속성이 붙는 변형 관찰.
**여전히 미상**(`추정`). 2026-08-10 추가 관찰분:

- 데이터 원본 필터에는 `filter-group='2'`가 붙는다 (`관찰_05`)
- 워크시트 필터 5건에는 **하나도 안 붙었다** (`관찰_01`~`04`)
- 실파일에서는 워크시트 필터에도 붙고 값이 3~142로 흩어진다 — 규칙 미해명

관찰대로만 복제한다. 값을 지어내지 않는다.

## 재저장 검증

UI 형태 그대로면 정규화 관찰 없음. twb-lint: `shelf.refs`(⑪) — 필터 column 실존·표기.
