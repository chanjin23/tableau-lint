# 레시피 23 — 집합 (만들기 · 뷰에 배치)

| 항목 | 값 |
|---|---|
| 판정 표면 | T3 · T4 |
| UI 경로 | 데이터 창에서 차원 우클릭 > **만들기 > 집합** / 만든 집합을 선반·마크에 드래그 |
| 근거 | 2026-08-10 관찰 `관찰_06`·`07`·`08`·`09` (소유자 조작, UI · 통제 diff) |
| Tableau | 2026.1.1 |

**실파일 106개에 사용자 집합이 46개 있는데 뷰에 배치된 표본이 0건이었다.**
이 레시피가 그 빈칸을 채운다 (`docs/06-rule-candidates.md` R20-b가 폐기됐던 이유).

---

## ① 목록 집합 — 값을 골라 만든다 (`관찰_06`)

데이터 창 `품목` 우클릭 > 만들기 > 집합 > 이름 `품목집합_목록` > `노트북` 체크.

```xml
<!-- <datasource> 안, 테이블 <column> 다음 · <layout> 앞 -->
<column datatype='string' name='[품목]' role='dimension' type='nominal' />
<group caption='품목집합_목록' name='[품목집합_목록]' name-style='unqualified'
       user:ui-builder='filter-group'>
  <groupfilter function='member' level='[품목]' member='&quot;노트북&quot;'
               user:ui-domain='database' user:ui-enumeration='inclusive'
               user:ui-marker='enumerate' />
</group>
```

**동반 변경**: 기반 필드 `[품목]`의 `<column>` 정의가 데이터 원본에 **새로 실체화된다.**
그전까지는 metadata-records에만 있었다. 집합을 만들면 필드 정의가 따라 나온다.

## ② 상위 N 집합 — 조건으로 만든다 (`관찰_07`)

`품목` > 만들기 > 집합 > **상위** 탭 > 상위 2개 by 합계(매출).

```xml
<column datatype='integer' name='[매출]' role='measure' type='quantitative' />
<column datatype='string' name='[품목]' role='dimension' type='nominal' />
<group caption='품목집합_상위' name='[품목집합_상위]' name-style='unqualified'
       user:ui-builder='filter-group'>
  <groupfilter count='2' end='top' function='end' units='records'
               user:ui-marker='end' user:ui-top-by-field='true'>
    <groupfilter direction='DESC' expression='SUM([매출])' function='order'
                 user:ui-marker='order'>
      <groupfilter function='level-members' level='[품목]'
                   user:ui-enumeration='all' user:ui-marker='enumerate' />
    </groupfilter>
  </groupfilter>
</group>
```

**3중 중첩이고 순서가 곧 의미다** — `end`(몇 개) → `order`(무엇으로 정렬) →
`level-members`(어느 필드에서). 정렬 기준 필드(`[매출]`)의 `<column>` 정의도 같이 실체화된다.

| 속성 | 뜻 |
|---|---|
| `count='2'` `end='top'` | 상위 2개 (하위는 `end='bottom'` 추정 — 미관찰) |
| `units='records'` | 개수 기준 |
| `expression='SUM([매출])'` | **집계 수식 문자열.** 필드 참조는 계산식 표기(`[매출]`) |
| `direction='DESC'` | 정렬 방향 |

## ③ 집합을 행/열 선반에 (`관찰_08`) ★

만든 집합을 **행 선반**에 드래그.

```xml
<!-- 워크시트 datasource-dependencies -->
<column-instance column='[품목집합_목록]' derivation='InOut' name='[io:품목집합_목록:nk]'
                 pivot='key' type='nominal' />
```
```xml
<rows>([ds].[io:품목집합_목록:nk] * [ds].[sum:매출:qk])</rows>
```

**핵심은 `io:` 한정자다.** 집합은 `derivation='InOut'`이고 인스턴스 이름이 `[io:<집합명>:nk]`.
"집합 안/밖"의 2값 차원으로 뷰에 들어간다.

기존 선반에 더할 때는 레시피 11의 `*` 축 교차로 묶인다.

**동반 변경**: `windows/window/viewpoint/highlight/color-one-way`에 이 인스턴스가
**자동 추가**된다 (레시피 22 §⑥과 같은 성질).

## ④ 집합을 색상에 (`관찰_09`)

행에서 빼고 **색상**에 올린다.

```xml
<encodings>
  <color column='[ds].[io:품목집합_목록:nk]' />
</encodings>
```
```xml
<!-- windows/window/cards -->
<edge name='right'>
  <strip size='160'>
    <card pane-specification-id='0' param='[ds].[io:품목집합_목록:nk]' type='color' />
  </strip>
</edge>
```

**빼는 쪽도 같이 지운다** — 색상에서 내린 `[지역]`은 `column-instance`·`column` 사본·
`viewpoint/highlight`의 `<field>`에서 **전부 사라진다.** 하나만 남기면 dangling이 된다.

---

## 집합의 세 갈래 — 구별해서 써라

| 갈래 | 표식 | 만드는 주체 |
|---|---|---|
| **사용자 집합** | `user:ui-builder='filter-group'` | 사람 (이 레시피 ①②) |
| 동작 집합 | `hidden='true'` `user:auto-column='sheet_link'` | 하이라이트/집합 동작 |
| 도구 설명 뷰 집합 | `hidden='true'` `user:auto-column='sheet_link'` `user:ui-vit-column='true'` | Tableau (레시피 24) |

**`hidden='true'`는 시스템이 만든 집합의 표식이다.** 사람이 만든 집합에는 붙지 않는다
(실측 80:2, 반례 2건은 로드 거부된 파일 하나 — 06 R20-a).

## 불변 조건

1. `<group>`은 **`<datasources>` 아래에만** 있다. 워크시트 안에는 없다 (실파일 164개 전수)
2. 자식은 항상 `<groupfilter>` **하나**. 여러 조건은 중첩으로 표현한다
3. 기반 필드가 반드시 있어야 한다 — 없으면 이 집합을 쓰는 계산이 전부 깨진다
   (twb-lint 규칙 ⑨ `set.definition`)
4. 집합을 만들면 **기반 필드·정렬 기준 필드의 `<column>` 정의가 실체화**된다
5. 뷰에 올리면 `io:` 인스턴스 · 선반 문자열 · `viewpoint/highlight` **3곳**이 함께 움직인다

## 재저장 검증 · twb-lint

관찰 원본 그대로면 정규화 없음. 4건 전부 `twb_validate` → `passed=true`, findings 0.
twb-lint: `set.definition`(⑨) · `shelf.refs`(⑪).
