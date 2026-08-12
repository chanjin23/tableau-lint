# 레시피 11 — 선반 표현식 (rows/cols) · pane 분리 · 이중축

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 필드를 열/행 선반에 드래그 |
| 근거 | MA_008 `33052f5`(UI·확인) `146f488` `1d2aa95` `35db682` `9cac21f` `23690bc`(AI 수용) |
| Tableau | 2026.1 |

## 문법 — `<rows>`/`<cols>` 요소 텍스트

| 연산자 | 뜻 | 예 |
|---|---|---|
| `*` | 차원 × 측정값 **축 교차** | `([none:accs_nm:nk] * [usr:…:qk])` |
| `+` | 측정값 **축 연결** (우결합 중첩으로 기록) | `(A + (B + C))` |
| `/` | 계층 표(차원/차원, 머리글 행) | `(accs_nm / [:Measure Names])` |

- 참조 표기는 인스턴스형 — `[<집계>:<name>:<qk|nk>]` (07 G8). `[:Measure Names]`는 특수형
- 단일 필드 → 이중축: 값이 괄호+`+` 연결로 바뀐다
  `[attr:idct_val:qk]` → `([attr:idct_val:qk] + [usr:…:qk])` (`35db682`)

## pane 분리 (`33052f5`)

측정값 이름+측정값 구조는 마크 카드가 하나다. 측정값들을 **각각 연속형으로** 열에 올리면:

- `<panes>` 1개 → N+1개. 첫 pane은 `@id` 없음(전체 카드), 나머지 `@id='1'…'N'`
- 각 pane에 `@x-axis-name`(열 축) / `@y-axis-name`(행 축) = 해당 측정값 인스턴스
- 마크가 자동 재판정된다 — 막대로 바뀌며 `mark-labels-show='false'`가 붙는 것 관찰

역방향(측정값 이름 구조로 복귀)은 `9cac21f` — pane 4→1, 이때 남는 pane의 `@id`는 유지됐다.

## 이중축 동기화 (`23690bc` AI 수용)

`style-rule[@element='axis']` + `<encoding attr='space' @fold='true' @synchronized='true'>`.

## `[측정값 이름]` 구조 — 최소 정본 세트 (MA_011 260811 AI 저작 · 재저장 무수정 수용)

네 조각이 **세트로 움직인다.** 하나만 빠져도 표가 비거나 필드가 제거된다.

```xml
<view>
  <!-- 1. 어떤 측정값을 몇 개 띄울지 -->
  <filter class='categorical' column='[<ds>].[:Measure Names]'>
    <groupfilter function='union' user:op='manual'>
      <groupfilter function='member' level='[:Measure Names]'
                   member='&quot;[<ds>].[usr:Calculation_A:qk]&quot;' />
      <groupfilter function='member' level='[:Measure Names]'
                   member='&quot;[<ds>].[usr:Calculation_B:qk]&quot;' />
    </groupfilter>
  </filter>
  <!-- 2. slices 에 [:Measure Names] 를 짝으로 -->
  <slices><column>[<ds>].[:Measure Names]</column></slices>
</view>
<panes><pane><mark class='Automatic' />
  <!-- 3. 텍스트에는 개별 측정값이 아니라 [Multiple Values] -->
  <encodings><text column='[<ds>].[Multiple Values]' /></encodings>
</pane></panes>
<!-- 4. 선반에는 [:Measure Names] 를 차원처럼 -->
<cols>([<ds>].[none:Calculation_L:nk] / [<ds>].[:Measure Names])</cols>
```

- 측정값이 1개면 `groupfilter function='member'` 단독, 2개 이상이면 `union` 래핑(`user:op='manual'`)
- `member` 값은 **인스턴스 문자열을 큰따옴표로 감싼 형태** (`manual-sort`의 `<bucket>`과 같다)
- `[:Measure Names]`는 데이터 원본에 `<column>`으로 존재하지만 `[Multiple Values]`는
  정의가 필요 없다 — 이 비대칭이 헷갈린다
- 집계 계산 필드의 인스턴스 파생은 `derivation='User'` → `[usr:…:qk]`,
  비집계 필드에 집계를 걸면 `derivation='Sum'` → `[sum:…:qk]` (lint ⑧)
- **열 표시 순서는 이 union 순서로 정해지지 않는다** — Tableau가 caption 가나다순으로
  재작성한다. 순서는 `<manual-sort>`로만 정한다 (레시피 14)
- 동반 변경: window `<cards>/<edge name='left'>/<strip>`에 `<card type='measures' />`가
  `marks` 다음에 추가된다 (레시피 09·10)

## 총계 — 태그가 아니라 선반 요소의 속성이다 ★ (MA_011 260812 UI 관찰)

```xml
<rows onTop='true' total='true'>[federated.…].[none:Calculation_1238633066082307:nk]</rows>
```

| 속성 | UI 조작 | 결과 |
|---|---|---|
| `total='true'` on `<rows>` | 분석 > 총계 > **열 총합계 표시** | 표 아래에 총합계 **행** 추가 |
| `onTop='true'` on `<rows>` | 분석 > 총계 > **열 총합계를 맨 위로 이동** | 총합계 행이 맨 위로 |

- 워크시트 3개에서 같은 형태 재현. **다른 태그·속성은 일절 추가되지 않는다**
- **매니페스트 게이트 없음**
- 총계 계산 방식 "자동"은 기본값이라 **아무 XML도 남지 않는다**. 합계/평균 등으로 바꾸면
  무엇이 기록되는지는 **미관찰**. 행 총합계(`<cols>` 쪽)·소계도 미관찰
- 주의 — 비율 측정값의 총계가 옳으려면 그 필드가 `SUM(a)/SUM(b)` 구조여야 한다.
  저장된 비율값을 `SUM()`한 필드면 총합계 행에서 비율이 합산돼 무의미한 값이 된다
  (MA_011에서 12개월치 비율이 더해져 `4,017%`가 표시됐다)

## 불변 조건

1. 선반의 인스턴스 표기와 `datasource-dependencies`의 `column-instance`가 일치해야 한다 (lint ⑪)
2. 측정값 이름 필터(`[:Measure Names]` categorical)와 선반 구조는 세트로 움직인다 —
   구조 전환 시 필터·`manual-sort`·encodings도 함께 정리 (`33052f5`가 −4종 제거)
3. 측정값 이름 별칭은 정적 — 매개변수 연동 필요하면 계산필드 라벨로 우회 (`23690bc`)

## 재저장 검증

`23690bc` AI 저작 "기존 필드 무수정, 다른 워크시트 45개 바이트 동일" 수용.
twb-lint: `shelf.refs`(⑪).
