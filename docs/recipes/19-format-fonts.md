# 레시피 19 — 글꼴·서식 규칙 (style-rule)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4(서식) |
| UI 경로 | 서식 메뉴 / 워크시트 기본 서식 |
| 근거 | MA_008 `75da540`·`8950148`·`d13373e`(AI 수용) `c6bdf15` `a248ae3` `146f488` `9cac21f`(UI) · 2026-11-10 MA_018 총합계 글꼴(UI) |
| Tableau | 2026.1 |

## 원리 — 기본값은 XML에 안 적힌다 (`75da540`)

Tableau 기본(Tableau Book 9pt)은 파일에 문자열로 존재하지 않는다.
**속성이 없는 자리가 곧 기본값으로 렌더되는 자리다.** 따라서:

- 기본값을 다른 값으로 바꾸기 = 치환이 아니라 **누락 채우기**
- 개별 element(title·label·cell)에 명시된 크기는 시트 기본보다 우선 — 전역으로 덮지 말 것

## 표면 4곳 — 글꼴이 사는 자리 (`8950148` 실측: 4곳 전부 바꿔야 일괄 변경)

| 자리 | 표기 |
|---|---|
| 시트 기본 | `worksheet/table/style/style-rule[@element='worksheet']/format[@attr='font-family'\|'font-size']` |
| 요소별 | `style-rule[@element='label'\|'cell'\|'header'\|…]/format[…]` |
| 리치 텍스트 | `<run @fontname @fontsize @fontcolor @bold @fontalignment>` |
| 대시보드 텍스트 개체 | `zone/formatted-text/run` — **워크시트 스타일을 상속하지 않는다** (`75da540`) |

`style-rule[@element='worksheet']` 자체가 없는 시트는 규칙부터 신설 (`75da540` 3건).

## 필드 한정 서식 (`c6bdf15` `a248ae3`)

```xml
<style-rule element='label'>
  <format attr='font-weight' field='[none:Calculation_…:nk]' value='bold' />
  <format attr='font-size' field='…' value='12' />
</style-rule>
```

`@field`로 특정 머리글만. 머리글 행 높이는 글꼴에서 파생 — 나란한 시트끼리
머리글 서식이 다르면 행이 어긋난다 (`c6bdf15` — 2pt 차이 관찰).

**`label`·`cell`·`header`·`axis`는 맨 `<format>`이 맞다** — 실파일 254개에서
`@field` 붙은 맨 표기가 각각 10,876 · 11,555 · 2,636 · 1,291건, fcp 접두는 0건이다.
아래 컨트롤 하나만 예외다.

### 예외 — 매개변수 컨트롤의 필드별 서식은 fcp 접두 (`_.fcp.IndividualControlFormatting`)

```xml
<style-rule element='parameter-ctrl'>
  <format attr='font-size' value='10' />                       <!-- 카드 전체: 맨 이름 -->
  <_.fcp.IndividualControlFormatting.true...format
      attr='font-size' field='[Parameters].[매개 변수 1]' value='11' />
</style-rule>
```

`@field`가 붙는 순간 접두가 필요하다 — **468건 : 맨 표기 0건**. 매니페스트에
`<_.fcp.IndividualControlFormatting.true...IndividualControlFormatting />`를 넣는다.
규칙 ⑮가 WARNING으로 잡는다(로드 거부는 미실측 — 상관만 확인됐다).

> `legend` 계열은 맨 238건 : fcp 21건으로 **혼재**다. 어느 쪽이 정본인지 모르므로
> 규칙에 넣지 않았다. 건드릴 일이 있으면 그 파일의 기존 표기를 따른다.

- 소계 테두리: `style-rule[@element='header']/format[@attr='border-color'][@data-class='subtotal']` (`9cac21f`)

## 총계·총합계 행 글꼴 — `data-class` (2026-11-10 UI 관찰)

UI: **서식 > 글꼴** → 서식 창 *시트* 탭에 `기본값` · **`총계`** · **`총합계`** 세 영역이 있고,
각각 `패널`(숫자 셀)과 `머리글`(행 이름) 글꼴을 따로 고른다.
본문 서식과 **같은 `style-rule`에 `data-class`만 붙인** 형태로 저장된다.

| UI | XML |
|---|---|
| 총합계 > 패널 | `style-rule[@element='cell']/format[@data-class='total']` |
| 총합계 > 머리글 | `style-rule[@element='header']/format[@data-class='total']` |
| 총계 > 패널 · 머리글 | 같은 자리에 `data-class='subtotal'` (아래 근거 — 이름 대응은 추정) |

```xml
<style-rule element='cell'>
  …본문 서식…
  <format attr='color' data-class='total' value='#c0c0c0' />    <!-- 총합계 숫자 -->
</style-rule>
<style-rule element='header'>
  …본문 서식…
  <format attr='color' data-class='total' value='#b6992d' />    <!-- '총합계' 글자 -->
</style-rule>
```

- **기본값이면 아무것도 안 적힌다** — 총계·총합계 행은 본문 글꼴을 그대로 따른다.
  "총합계 행을 본문과 같게"는 **서식을 넣는 일이 아니라 빼는 일**이다 (`data-class` 서식 삭제)
- 필드 한정 형태도 1건 나왔다: `<format attr='color' data-class='total' field='[<ds>].[:Measure Names]' … />`
  — 같은 관찰 중 **실수 클릭**으로 생긴 것이라 UI 경로는 미확인 (필드 서식 창으로 추정)
- `총계`↔`subtotal` 근거: MA_002 89개 파일의 `cell`·`header`
  `font-weight data-class='subtotal' value='normal'` · 테두리 `subtotal` 30,337건. 직접 조작 관찰은 `총합계`뿐
- 굵기·글꼴·크기도 본문과 같은 속성 이름(`font-weight`·`font-family`·`font-size`)에
  `data-class`를 붙인다 — `font-weight`는 `subtotal`로 관찰, `total`의 글꼴·크기는 미관찰

**⚠ 연속형 색상이 걸린 그리드에서 총합계 숫자가 회색이면 글꼴 문제가 아니다.**
색상 인코딩이 이 글자색 서식을 이긴다 — `include-totals`(레시피 13 "총계 포함")로 고친다.

근거: MA_018 JWP `SEC03_상세 실적표_그리드`(총합계 켜짐, 색상 인코딩 없음)에서 소유자가
`총합계` 패널을 연회색, 머리글을 금색으로 바꿔 저장 → 위 두 줄만 추가됐다 (재저장 정규화 제외).

## 행·열 구분선 수준 — `table-div` `div-level` (2026-11-10 UI 관찰)

UI: **서식 > 테두리** → 서식 창 *시트* 탭 `행 구분선`(또는 `열 구분선`) > **`수준`** 슬라이더.

```xml
<style-rule element='table-div'>
  <format attr='stroke-size' scope='rows' value='1' />
  <format attr='line-visibility' scope='rows' value='on' />
  <format attr='line-pattern-only' scope='rows' value='solid' />
  <format attr='div-level' scope='rows' value='3' />
  <format attr='stroke-color' scope='rows' value='#000000' />
  <!-- 열 구분선은 같은 attr에 scope='cols' -->
</style-rule>
```

**`div-level` = 행 선반 바깥에서부터 몇 번째 필드까지 경계에 선을 긋는가.**
행 선반이 `C_LV1 / C_LV2 / C_그리드_행_라벨`(불연속 3개)인 그리드에서:

| 수준 | 패널 가로선 |
|---|---|
| 3 (= 행 필드 수, 슬라이더 끝) | **모든 행 사이** |
| 1 | `C_LV1` 그룹 경계에만 (매출액 · 변동판매비 · 고정판매비 묶음 사이) |
| 0 (슬라이더 처음) | 없음 |

- **슬라이더 최대값 = 행 선반 불연속 필드 수**다 (위 시트: 눈금 0~3). "모든 행에 선"을 원하면
  `div-level`을 행 필드 수로 쓴다
- **필드 수보다 큰 값도 파일에는 남는다** — 실파일 시트 2,462개 중 472개가 필드 수보다 크고
  Tableau 저장본에도 있다. 저장 시 잘라내지 않으니 로드 오류는 아니다. 렌더는 최대값과 같을
  것으로 추정(미관찰). 행 필드를 빼면 옛 값이 그대로 남는 경우로 보인다
- 수준을 바꿔도 **머리글 쪽 선은 그대로**였다 (이 시트는 머리글 테두리가 따로 켜져 있다)
- 수준 0의 XML 표기는 미관찰 — 코퍼스 `scope='rows'` 값은 1~5뿐이다

근거: MA_012 JWP `SEC04_상세표_그리드_NOV`(행 필드 3, `div-level` rows=3)에서 소유자가 슬라이더를
3 → 1 → 0으로 옮기며 화면을 확인(저장 안 함). MA_012 6개 판본의 상세표 그리드 18시트는 전부
`div-level` = 행 필드 수, 모두 Tableau 저장본.

## 셀 숫자 서식 — `text-format` (`146f488` · MA_011 260811 재저장 무수정 수용)

```xml
<style>
  <style-rule element='cell'>
    <format attr='text-format' field='[<ds>].[usr:Calculation_A:qk]'
            value='n#,##0.0;-#,##0.0' />
  </style-rule>
</style>
```

- `value` 문법: `양수 서식;음수 서식`. 선두 `n`이 붙는다.
  접미 문자열은 따옴표로 — `n#,##0.0&quot;%&quot;;-#,##0.0&quot;%&quot;`
- `@field`로 필드별 지정. `@field` 없이 쓰면 시트 전역
- MA_011에서 7건 전부 재저장 무수정 수용 — 이 문법이 정본이다

## 필드 **레이블** 숨김 vs 필드 **머리글** 숨김 — 다른 표면이다 ★

이름이 비슷해서 혼동된다 (MA_011 260812 UI 관찰로 두 개가 한 시트에서 같이 나왔다).

| 감추는 대상 | XML |
|---|---|
| 필드 **레이블** (표 좌상단 필드명) | `style-rule[@element='worksheet']` + `display-field-labels` + `@scope` |
| 필드 **머리글** (각 행/열의 멤버명) | `style-rule[@element='label']` + `display` + `@field` (`9cac21f`) |

```xml
<style-rule element='worksheet'>
  <format attr='display-field-labels' scope='cols' value='false' />
  <format attr='display-field-labels' scope='rows' value='false' />
</style-rule>
```

`scope`는 `rows`/`cols` **쌍**을 받는다. `rows`는 AI가 근거 없이 쓴 값이었는데
① 재저장에서 무수정 수용되고 ② 사람이 UI로 만든 시트에서도 같은 형태가 나와 **확정됐다.**
(`stroke-size`·`line-visibility`도 같은 쌍을 쓴다.)

## 불변 조건 (일괄 변경 시 제외 규칙 — `8950148`·`d13373e` 판단)

1. devicelayouts(Phone) 안 값 — auto-generated, 손대면 되돌아온다
2. 면별 비대칭 여백과 짝지어진 값 — 의도 보존
3. 요청 범위 밖 크기(11/12/14/18/24pt 등) — 개별 명시는 우선권이 있다

## 재저장 검증

⚠ 미해결 — `b6256cf`에서 글꼴 명시 33곳이 소실됐는데 사용자 해제인지 Tableau 제거인지
판별 불가(`?`). 글꼴 일괄 작업 후 재저장 diff를 반드시 확인할 것.
