# 레시피 09 — 워크시트 생성·복제·개명·삭제

| 항목 | 값 |
|---|---|
| 판정 표면 | T1(배선) |
| UI 경로 | 시트 탭 우클릭 > 새로 만들기/복제/이름 바꾸기/삭제 |
| 근거 | MA_008 `b63e1b1`(UI·확인) · `b13bc5a` `7353886` `35911cd` `ad7cb3f` · `8fc93fe`·`c681161`(AI 수용) · `8df7c57`(uuid 제약) |
| Tableau | 2026.1 |

## 3곳 동시 규칙 — 전 조작 공통

| 조작 | `<worksheet>` | `<windows>/<window class='worksheet'>` | `<thumbnails>/<thumbnail>` |
|---|---|---|---|
| 생성/복제 | +블록 | +블록 | +블록 |
| 개명 | `@name` | `@name` | `@name` |
| 삭제 | −블록 | −블록 | −블록 |

개명 시 대시보드에 배치된 시트면 `zone@name`(데스크톱·Phone)·`viewpoint@name`도 함께 —
총 5곳 (`b67ed82`). lint `named.refs`가 3자 일치를 검사한다.

## 생성·복제 세부

- 빈 시트도 유효 — datasources 비고 pane 1개, rows/cols 빈 문자열 (`1d2aa95` 시트 46)
- **복제해도 계산필드는 새로 안 생긴다** — 원본 것을 그대로 참조 (`7e15b84`)
- 복제 시 필터 값도 그대로 상속 — 복제 후 필터만 고치는 흐름이 정석
  (`8fc93fe` 하위카드 min/max=2..6, `529e436`은 안 고쳐서 난 결함)
- 대시보드에만 쓰이는 시트의 window는 `@hidden='true'` (`8fc93fe`)
- UI 복제 명명: `'<원본> (2)'` 접미사 → 개명으로 정리 (`7e15b84`→`b63e1b1`)

## AI 저작 제약 (XSD 실증)

- `<window>`의 `<simple-id uuid>`는 XSD unique 제약(`DemandWindowSimpleIdUnique`) —
  기존 window를 복사하면 **새 uuid 필수.** 그대로 복사하면
  `Duplicate key-sequence … in unique identity-constraint`로 로드 거부 (`8df7c57`)
- window 복사 시 원본에 붙은 범례 카드(`cards/edge`)가 대상 시트에 안 맞으면 제거 —
  `8fc93fe`는 색상 카드·measures 카드를 빼고 highlight 필드를 교체했다

## 삭제 여파

- 동작의 exclude 목록에서 그 시트 항목 제거 (`c681161` −5) — 레시피 07·08
- 대시보드 존·viewpoint도 배치돼 있었으면 함께 제거

## 재저장 검증

`<window>` 블록 순서는 **시트명 정렬**로 재배치된다 (`227b603` 정규화 2) —
새 window는 정렬 위치에 넣는다. thumbnail은 저장마다 재생성(노이즈) — AI가 생략해도
되는지는 미관찰(`추정`: 재생성될 것). worksheets 블록 자체의 순서 규칙도 미관찰.
