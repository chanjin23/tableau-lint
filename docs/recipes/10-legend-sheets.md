# 레시피 10 — 범례 시트 패턴 · 범례 카드

| 항목 | 값 |
|---|---|
| 판정 표면 | T3·T4 |
| UI 경로 | (범례 시트) 시트 복제 후 구성 · (카드) 워크시트 창에서 범례 카드 드래그 |
| 근거 | MA_008 `358c382` `6154648`(AI) `8df7c57`(AI) `b67ed82` `b6256cf` `8fc93fe`(AI) |
| Tableau | 2026.1 |

## 범례 시트 — 색상 견본 시트를 따로 만드는 패턴

기본 색상 범례 대신 Square 마크 미니 시트를 만들어 대시보드에 놓고
하이라이트 동작(레시피 08)을 건다. 구성 (`358c382`):

- `mark@class='Square'`, cols·color·text 전부 같은 필드
- 항목 한정은 `filter[@class='categorical']`
- **색은 지정하지 않는다** — 데이터소스 수준
  `style/style-rule[@element='mark']/encoding[@attr='color']` 팔레트를 그대로 상속
  (`6154648` `8df7c57` — 시트에 색을 다시 정의하지 않았다)

## 하이라이트가 먹으려면 (`6154648` 실패→수정 관찰)

범례와 그래프가 **같은 차원 필드**를 공유해야 한다. 그래프 색이
`C_CL_추이구분`인데 범례가 `[:Measure Names]`면 색도 어긋나고 하이라이트도 안 먹는다.
측정값 항목(검정 선 등)은 차원을 얹어도 안 되므로 **상수 문자열 차원**
(`formula='"연간목표"'`)을 만들어 그걸로 색·범례를 구성한다 (`b67ed82`).

한 범례 시트로 차원 값 + 측정값 항목을 동시에 하이라이트할 수 없다 —
시트를 가른다 (`8df7c57`).

## 범례 카드 이동/제거 (`b6256cf`)

`window[@class='worksheet']/cards/edge[@name='right'|'left']/strip/card`:

- 오른쪽→왼쪽 = `edge[@name='right']` 제거 + `edge[@name='left']/strip`에 `<card @type='color'>` 추가
- `strip@size`도 함께 조정 (160→199 관찰)
- 색상 범례 카드 제거 = 해당 `<card>` 삭제

## 재저장 검증

AI 저작 범례 시트 3건 수용 (`6154648` `8df7c57`). twb-lint: `named.refs` · `action.refs`(⑩).
