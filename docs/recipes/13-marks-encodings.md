# 레시피 13 — 마크·인코딩·레이블·도구설명

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 마크 카드 (유형·색상·텍스트·크기·레이블) · 도구 설명 |
| 근거 | MA_008 `5916221` `a248ae3` `6958d25` `b13bc5a` `b6256cf` `8b136bb` `23690bc`(AI) `35911cd` |
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
