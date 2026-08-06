# 레시피 16 — 대시보드 컨테이너·존 구조·devicelayout

| 항목 | 값 |
|---|---|
| 판정 표면 | T1(배선)·T4 |
| UI 경로 | 대시보드 > 컨테이너 드래그 / 개체 배치 |
| 근거 | MA_008 `c0ca652`(UI·확인) `c681161`(AI 수용) `35b2505` `b13bc5a` |
| Tableau | 2026.1 |

## 존 종류 (`type-v2` 관찰값)

`text` · `empty` · `layout-flow`(컨테이너, `@param='horz'|'vert'`) · `layout-basic`(루트) ·
`paramctrl` · `color`(색상 범례) · (이름 있는 시트 존은 type-v2 없음)

## 컨테이너 구조 변경

- **래퍼 추가** (`c0ca652`): 기존 컨테이너를 새 존으로 한 겹 감싸면
  `@fixed-size`/`@is-fixed`가 **래퍼로 이동**한다
- **방향 전환** (`c681161`): `zone@param 'vert'→'horz'` + 자식 존 교체.
  컨테이너 자신의 zone-style(테두리·둥글기·배경)은 보존
- 콘텐츠 균등 분할: `zone[@layout-strategy-id='distribute-evenly']` (UI-XML매핑.md 확인)

## zone id 규칙

- 파일 안 유일 정수. UI는 신규 발급, AI가 기존 id 재사용(교체 시)해도 수용 (`8fc93fe`)
- 데스크톱과 Phone devicelayout은 **같은 존이면 id 공유** (`b63e1b1`)
- 루트 `layout-basic`/`layout-flow`의 id는 저장마다 재발급될 수 있다 — 노이즈 (`dbe9a1b`, E2E-1)

## devicelayout (Phone)

- `auto-generated='true'` — Tableau가 데스크톱에서 재생성한다. **AI는 안 만드는 게 아니라
  못 따라간다**: `fixed-size`가 존 높이 파생값이라 손으로 정확히 못 쓴다 (`227b603` 정규화 3)
- Phone에는 컨테이너가 없고 워크시트 존이 평면 배치 (`c681161`)
- 사용자가 Phone을 직접 만졌으면 신호, 데스크톱 변경에 따라온 것이면 노이즈 (신호노이즈.md)

## paramctrl 존 (`b13bc5a` · E2E-1 확인)

기존 컨트롤 존 복제 + `id`(유일)·`param='[Parameters].[…]'`·제목 run만 교체 → 수용.
`w`/`x`는 레이아웃 플로우가 재계산(노이즈). 데스크톱·devicelayout 양쪽에, id 공유.

## 재저장 검증

존 개수로 판정한다 — **개수 불변이면 좌표·크기 diff는 전부 노이즈** (신호노이즈.md 요령).
twb-lint: `named.refs`.
