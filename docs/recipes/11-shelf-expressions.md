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

## 불변 조건

1. 선반의 인스턴스 표기와 `datasource-dependencies`의 `column-instance`가 일치해야 한다 (lint ⑪)
2. 측정값 이름 필터(`[:Measure Names]` categorical)와 선반 구조는 세트로 움직인다 —
   구조 전환 시 필터·`manual-sort`·encodings도 함께 정리 (`33052f5`가 −4종 제거)
3. 측정값 이름 별칭은 정적 — 매개변수 연동 필요하면 계산필드 라벨로 우회 (`23690bc`)

## 재저장 검증

`23690bc` AI 저작 "기존 필드 무수정, 다른 워크시트 45개 바이트 동일" 수용.
twb-lint: `shelf.refs`(⑪).
