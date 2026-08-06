# 레시피 03 — 대시보드에 워크시트 배치

| 항목 | 값 |
|---|---|
| 판정 표면 | T1(배선)·T4 |
| UI 경로 | 대시보드 > 시트 목록에서 드래그 (기존 개체 위에 놓으면 교체) |
| 근거 | MA_008 `b63e1b1`(UI·확인) · `b13bc5a`(UI) · `8fc93fe`·`c681161`(AI 저작 수용) |
| Tableau | 2026.1 |

## XML 변경 — 3곳 동시

**① 대시보드 `<zones>`에 존 추가.** 기존 텍스트 개체를 교체하면 그 자리에서
`@type-v2='text'`·`@forceUpdate`·`<formatted-text>`가 빠지고 시트 존이 된다.
`<zone-style>`은 유지.

```xml
<!-- before: 텍스트 개체 -->
<zone forceUpdate='true' h='733' id='1306' type-v2='text' w='9437' x='38188' y='9489'>
  <formatted-text>
    <run bold='true' ...>46.2억</run>
  </formatted-text>
</zone>
<!-- after: 워크시트 존 -->
<zone h='733' id='1449' name='SEC01_제품_당월실적' show-title='false' w='9437' x='38188' y='9489'>
  <layout-cache cell-count-h='1' cell-count-w='1' type-h='cell' type-w='cell' />
</zone>
```

**② `devicelayouts`의 Phone 레이아웃에도 같은 존.** zone `id`는 데스크톱과 **공유**하고,
Phone 쪽에만 `@fixed-size` `@is-fixed='true'`가 더 붙는다 (`b63e1b1`).
Phone에 컨테이너는 없다 — 워크시트 존이 평면 배치된다 (`c681161`).

**③ `<window class='dashboard'>/<viewpoints>`에 viewpoint 추가.**

```xml
<viewpoint name='SEC01_제품_당월실적'>
  <zoom type='entire-view' />
</viewpoint>
```

## 불변 조건

1. **시트가 먼저 존재해야 한다** — `<worksheet>`·`<window class='worksheet'>`·`<thumbnail>`
   3곳 (워크시트 생성 레시피, `b63e1b1`). 대시보드에만 쓰이는 시트의 window는
   `@hidden='true'` (`8fc93fe`)
2. `zone@name` = `viewpoint@name` = `worksheet@name` **3자 일치** (lint `named.refs`).
   시트 개명 시 전부 동반 변경 (`b67ed82`: worksheet·zone 데스크톱/Phone·viewpoint·window 동시)
3. zone `id`: UI는 신규 발급(`1306`→`1449`), AI가 기존 텍스트 존 id를 물려받아도 수용됨
   (`8fc93fe` — "신규 id 발급 없음"). **파일 안 유일성**만 지키면 된다(추정)
4. `@fixed-size`는 존 높이에서 파생 — **손으로 정확히 못 쓴다.** 대략 쓰면 Tableau가
   재계산한다 (`227b603` 정규화 3 — 무해하나 diff에 남는다)
5. 컨테이너 존(`@param='horz'|'vert'`) 안에 넣을 때 컨테이너의 `zone-style`은 건드리지 않는다
   (`c681161` — 자식 교체 시 컨테이너 스타일 보존 관찰)

## 재저장 검증

존 좌표(x·y·w·h)는 레이아웃 플로우가 재계산한다 — 구조(존 개수)가 안 바뀌었는데
좌표만 움직였으면 노이즈 (신호노이즈.md 판정 요령). `<layout-cache>`·thumbnail도 노이즈.
Phone `fixed-size` 재계산은 정규화 — 신호로 읽지 말 것.

## twb-lint 연계

`named.refs` — 3자 일치. `manifest.gates`(⑥-a) — 배선 게이트.
