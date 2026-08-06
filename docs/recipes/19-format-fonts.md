# 레시피 19 — 글꼴·서식 규칙 (style-rule)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4(서식) |
| UI 경로 | 서식 메뉴 / 워크시트 기본 서식 |
| 근거 | MA_008 `75da540`·`8950148`·`d13373e`(AI 수용) `c6bdf15` `a248ae3` `146f488` `9cac21f`(UI) |
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

- 머리글 표시 해제: `style-rule[@element='label']/format[@attr='display'][@field='…']='false'` (`9cac21f`)
- 소계 테두리: `style-rule[@element='header']/format[@attr='border-color'][@data-class='subtotal']` (`9cac21f`)
- 셀 숫자 형식: `style-rule[@element='cell']/format[@attr='text-format']` (억/% 관찰, `146f488`)

## 불변 조건 (일괄 변경 시 제외 규칙 — `8950148`·`d13373e` 판단)

1. devicelayouts(Phone) 안 값 — auto-generated, 손대면 되돌아온다
2. 면별 비대칭 여백과 짝지어진 값 — 의도 보존
3. 요청 범위 밖 크기(11/12/14/18/24pt 등) — 개별 명시는 우선권이 있다

## 재저장 검증

⚠ 미해결 — `b6256cf`에서 글꼴 명시 33곳이 소실됐는데 사용자 해제인지 Tableau 제거인지
판별 불가(`?`). 글꼴 일괄 작업 후 재저장 diff를 반드시 확인할 것.
