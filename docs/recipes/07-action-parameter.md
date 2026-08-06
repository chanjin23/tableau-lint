# 레시피 07 — 매개변수 동작 (edit-parameter-action)

| 항목 | 값 |
|---|---|
| 판정 표면 | T3 |
| UI 경로 | 대시보드 > 동작 > 동작 추가 > **매개 변수 변경** |
| 근거 | MA_008 `b13bc5a`(UI·확인) · `8fc93fe`·`c681161`(exclude 갱신, AI 수용) |
| Tableau | 2026.1 |

## XML — `workbook/<actions>` 직속

```xml
<edit-parameter-action caption='SEC01_카드선택' name='[Action1_FA0F3317C873440799C62781162042A8]'>
  <activation type='on-select' />
  <source dashboard='<대시보드명>' type='sheet'>
    <exclude-sheet name='<선택 안 한 시트>' />
    <!-- ... 고르지 않은 시트마다 1개 -->
  </source>
  <agg-type type='attr' />
  <clear-option type='do-nothing' />
  <params>
    <param name='source-field' value='<원본 필드>' />
    <param name='target-parameter' value='[Parameters].[매개 변수 N]' />
  </params>
</edit-parameter-action>
```

| 항목 | 규칙 |
|---|---|
| `@name` | `[ActionN_<32자리 hex>]` — N 증가 + 대문자 hex 32자리 |
| `target-parameter` | `[Parameters].[…]` 완전 한정 (lint ⑬ `action.shape` 어휘) |
| 매니페스트 | `ParameterAction`(+`ParameterActionClearSelection`) 항목 필요 — 이 코퍼스 파일엔 이미 있음 |

## 핵심 함정 — 대상은 포함이 아니라 **제외**로 기록된다 (`b13bc5a`)

UI에서 원본 시트 몇 개를 고르면 XML에는 **고르지 않은 시트**마다
`<exclude-sheet @name>`이 들어간다 (관찰: 28개·34개).

**여파** — 새 워크시트를 만들면 기존 동작의 exclude 목록에 자동으로 안 들어간다
= **새 시트에 그 동작이 걸린다.** XML로 시트를 만들 때 의도가 아니면
기존 `edit-parameter-action`마다 `+<exclude-sheet>`를 같이 넣는다
(`8fc93fe` x5 · `c681161` x10/-5 — 시트 증감마다 갱신했다).

## 재저장 검증

UI 저장 형태 그대로면 정규화 관찰 없음. twb-lint: `action.refs`(⑩) 배선 9표면 ·
`action.shape`(⑬) 종류별 어휘.
