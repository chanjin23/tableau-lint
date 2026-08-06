# 레시피 06 — 매개변수 변경·삭제 (수명주기)

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 |
| UI 경로 | 데이터 패널 > 매개변수 우클릭 > 편집/삭제 |
| 근거 | MA_008 `8b136bb` `57e556a` `ae0f567` `b6256cf` |
| Tableau | 2026.1 |

## 타입 전환 — 문자열 목록 → datetime (`8b136bb`)

한 속성이 아니라 **묶음 전환**이다:

| 항목 | 변화 |
|---|---|
| `@datatype` | `string` → `datetime` |
| `@param-domain-type` | `'list'` **제거** (datetime은 자유 입력) |
| `<members>` | **통째 삭제** |
| `formula` | `'"26-01"'` → `'#2026-01-01 00:00:00#'` (datetime 리터럴) |
| 추가 | `+@datatype-customized` `+@default-format='*YY-MM'` `+@default-value-field` |

이 매개변수를 참조하던 계산도 새 타입에 맞게 고쳐야 한다 —
`8b136bb`에서 F_YM_RANGE가 문자열 비교→날짜 직접 비교로 함께 교체됐다.

## 값 목록의 필드 연결 해제 (`ae0f567`)

목록을 "필드에서 가져오기"→수동 목록으로 바꾸면 `@source-field` 속성이 **소멸**한다.
`<members>`는 남는다.

## 삭제 (`57e556a` `8b136bb` `b6256cf`)

`Parameters`의 `<column>` 제거 + **동반 정리 2종**:

1. 대시보드의 `zone[@type-v2='paramctrl'][@param='[Parameters].[…]']` 동시 삭제
   (`57e556a` — 안 지우면 죽은 컨트롤)
2. 참조하던 계산·필터 확인 — dangling되면 층 3 (lint ⑦-c·②)

## 재저장 검증

`@value`(현재값)는 노이즈. 전환·삭제 자체는 제자리 변경 — 정규화 관찰 없음.
