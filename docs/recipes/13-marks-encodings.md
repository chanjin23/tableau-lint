# 레시피 13 — 마크·인코딩·레이블·도구설명

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 마크 카드 (유형·색상·텍스트·크기·레이블) · 도구 설명 |
| 근거 | MA_008 `5916221` `a248ae3` `6958d25` `b13bc5a` `b6256cf` `8b136bb` `23690bc`(AI) `35911cd` · 2026-11-10 MA_011 "총계 포함" 분리 실험 A0~A2 |
| Tableau | 2026.1 |

## 마크 유형 (`5916221`)

`pane/mark@class` — `'Automatic'`·`'Text'`·`'Bar'`·`'Square'`·`'GanttBar'` 관찰.
pane마다 따로다 — 마크 카드 분리 상태(레시피 11)면 pane별로 바꾼다.

## 인코딩 (`5916221` `a248ae3`)

```xml
<pane id='3'>
  <encodings>
    <color column='[usr:Calculation_4614680346259457:nk]' />
    <text column='[usr:Calculation_4614680346120192:qk]' />
  </encodings>
</pane>
```

- 인코딩에 올린 필드는 그 시트 `datasource-dependencies`에 column·column-instance 동반 추가
- 색상 팔레트 자체는 **데이터소스 수준**에 있다 (레시피 18) — 시트에는 참조만

## 연속형 색상 — 총합계 행까지 칠하려면 "총계 포함" ★ (2026-11-10 분리 실험)

**증상**: 그리드에 연속형 색상(음수 빨강/양수 검정 등)을 걸고 행 총합계를 켜면,
**총합계 행 숫자만 회색**으로 나온다. Tableau 기본값은 총계를 색상 범위에서 **뺀다.**

UI: 색상 카드 > 색상 편집 > (고급) **`총계 포함`** 체크.

```xml
<!-- worksheet/table/style/style-rule[@element='mark'] -->
<encoding attr='color' center='-0.0001' field='[federated.<ds-id>].[Multiple Values]'
          include-totals='true' num-steps='2' type='custom-interpolated'>
  <color-palette custom='true' name='' type='ordered-diverging'> … </color-palette>
</encoding>
```

- 바뀌는 것은 **`include-totals='true'` 속성 하나**다. 끄면 속성 자체가 없다 (`'false'` 표본 0)
- 속성은 알파벳 순서 자리(`field` 다음 · `num-steps` 앞)에 쓴다 — Tableau 저장본이 그렇다
- **총합계 행 글자색 서식으로는 안 고쳐진다.** `cell`·`header` style-rule에
  `<format attr='color' data-class='total' value='#000000'/>`를 넣어도 회색 그대로다 —
  색상 인코딩이 글자색 서식보다 우선한다 (아래 실험 A2)

분리 실험 (MA_011 JWP `SEC04_그리드`, 직전 백업에서 한 곳만 바꿈, 소유자가 Tableau에서 확인):

| 실험본 | 바꾼 것 | 총합계 행 숫자 |
|---|---|---|
| A0 | 없음 (대조) | 회색 |
| A1 | `include-totals='true'`만 | **정상** (음수 빨강·양수 검정) |
| A2 | `cell`·`header`에 `color data-class='total'/'subtotal'` `#000000`만 | 회색 |

코퍼스: 색상 encoding 11,254건 중 `include-totals` **2건**(MA_011 JWP·JWLH 최종본, 둘 다 Tableau 저장본).
`interpolated`·`palette` 유형에서도 같은 속성인지는 미관찰.

## 마크 레이블·크기

- 텍스트 마크의 기본 쌍 — 빠뜨리면 Tableau가 채운다. 정본으로 넣어 두는 편이
  정규화 0에 가깝다 (MA_011 재저장 검증 · 같은 파일 카드 시트 42개가 전부 이 형태):

  ```xml
  <style><style-rule element='mark'>
    <format attr='mark-labels-show' value='true' />
    <format attr='mark-labels-cull' value='true' />
  </style-rule></style>
  ```

- `pane/style-rule[@element='mark']/format[@attr='mark-labels-show']` `'true'|'false'`
- 크기 조정 해제: `pane/+<mark-sizing @mark-sizing-setting='marks-scaling-off'>` (`b13bc5a` — 간트에 적용 관찰)
- 크기값: `pane/style/style-rule[@element='mark']/format[@attr='size']` (`b6256cf`, GanttBar size 1.747 `23690bc`)

## 커스텀 레이블·도구설명 (`35911cd` `8b136bb`)

- `pane/+<customized-label>/<formatted-text>/<run @bold @fontsize>`
- 도구설명 교체: `+<customized-tooltip>/<formatted-text>` (필드 삽입 run 포함)
  + 끄기: `<tooltip-style @tooltip-mode='none'>` (worksheet/table 수준 관찰도 있음 — UI-XML매핑.md)

## 축·격자 숨김

- 축 머리글: `style-rule[@element='axis']/format[@attr='display'|'title'] @scope='rows'` 확인,
  `@scope='cols'`는 유추(`5916221` ?)
- 격자선: `style-rule[@element='gridline']` rows `stroke-size=0` `line-visibility=off` (`8b136bb`)

## 재저장 검증

전부 제자리 요소 — 정규화 관찰 없음. `?` 표시 2건(axis cols · 6958d25 run bold 제거)은
승격 전 재관찰 필요. twb-lint: `shelf.refs`(⑪) — encoding column 표기.
