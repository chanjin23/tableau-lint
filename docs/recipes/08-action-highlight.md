# 레시피 08 — 하이라이트 동작 (action/tsc:brush)

| 항목 | 값 |
|---|---|
| 판정 표면 | T3 |
| UI 경로 | 대시보드 > 동작 > 동작 추가 > **하이라이트** |
| 근거 | MA_008 `8b136bb`(UI) · `1892f8d`·`6154648`·`8df7c57`(AI 수용) · `b67ed82`(UI·소스 다중) |
| Tableau | 2026.1 |

## XML — `workbook/<actions>` 직속. `<edit-parameter-action>`과 요소가 다르다

```xml
<action caption='SEC03_범례그래프_하이라이트' name='[Action4_…32자리hex…]'>
  <activation auto-clear='true' type='on-select' />
  <source dashboard='<대시보드명>' type='sheet' worksheet='<원본 시트>' />
  <command command='tsc:brush'>
    <param name='exclude' value='시트A,시트B,…' />
    <param name='field-captions' value='측정값 이름' />
    <param name='target' value='<대시보드명>' />
  </command>
</action>
```

## `<edit-parameter-action>`과 다른 점 3개

1. **exclude가 요소가 아니라 문자열** — `param[@name='exclude']`에 제외 시트들을
   **쉼표로 이어붙인 단일 값**. 원본 시트 자신도 목록에 들어간다 (`1892f8d`).
   ⚠ 시트명에 쉼표가 있으면 깨진다 — `1892f8d`에서 사전 확인하고 넣었다
2. **원본 시트 지정이 2형태** — 1개면 `source@worksheet` 속성. **2개 이상이면
   속성이 사라지고 `<exclude-sheet>` 자식 방식으로 전환** — 원본도 제외로 기록
   (zones 59 − exclude 57 = 원본 2, `b67ed82`)
3. `field-captions` = 하이라이트 기준 필드를 **caption**으로. 다중이면 쉼표 구분
   (`'C_CL_연간목표,C_CL_추이구분'`, `b67ed82`)

## 순서 제약 (XSD 실증, `6154648`)

`<action>`은 `<edit-parameter-action>`보다 **앞**이어야 한다. `</actions>` 앞에 붙이면:

```
Element 'action': This element is not expected. Expected is ( edit-parameter-action )
```

→ 첫 `<edit-parameter-action>` 앞에 삽입한다.

## 하이라이트가 실제로 먹는 조건 (`6154648` 실패 관찰)

원본·대상 시트가 **공유하는 필드**가 하이라이트 기준이어야 한다. 범례가
`[:Measure Names]`인데 그래프 색이 차원 기반이면 동작이 걸려도 막대에 안 먹는다 —
XML은 유효하지만 기능이 죽는다 (층 4 너머, lint가 못 잡는 의미 결함).

## 재저장 검증

AI 저작 3건 전부 수용, 워크시트·대시보드 블록 무변경 확인 (`1892f8d` `8df7c57`).
twb-lint: `action.refs`(⑩) · `action.shape`(⑬).
