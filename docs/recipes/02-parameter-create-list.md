# 레시피 02 — 매개변수 추가 (허용 값 = 목록)

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 |
| UI 경로 | 데이터 패널 > **매개 변수 만들기** > 데이터 형식 선택, 허용 가능한 값 '목록' |
| 근거 | MA_008 `b13bc5a`(UI·확인) · `8b136bb`(타입 전환) · `ae0f567`(source-field 소멸) |
| Tableau | 2026.1 |

## XML 변경 — 어디에 무엇을

`<datasource name='Parameters'>` 직속으로 `<column>` 1개. 자식 `<calculation>` + `<members>`.

```xml
<column caption='P_ACCS_NM' datatype='string' default-value-field='[federated.1z0aj35028p9cq149bdem1ncjozh].[Calculation_5432716985044993]' name='[매개 변수 9]' param-domain-type='list' role='measure' type='nominal' value='&quot;총합&quot;'>
  <calculation class='tableau' formula='&quot;총합&quot;' />
  <members>
    <member value='&quot;고정비&quot;' />
    <member value='&quot;매출액&quot;' />
    <!-- ... 허용 값마다 1개 -->
  </members>
</column>
```

| 속성 | 값 규칙 |
|---|---|
| `name` | `[매개 변수 <N>]` — UI가 순번 발급. 삭제된 번호는 재사용 안 하는 것으로 보임(추정). `caption`이 사용자 이름 |
| `formula` | **기본값** (문자열이면 `&quot;` 이스케이프) |
| `value` | **현재 선택값 — 노이즈다.** 저장할 때마다 바뀔 수 있다 (신호노이즈.md). 생성 시 기본값과 같게 |
| `param-domain-type` | `'list'`. 목록 아님(전체) = 속성 자체 없음 |
| `default-value-field` | 선택 — "통합 문서가 열릴 때" 기본값 필드. `[<데이터소스 id>].[<필드 name>]` 완전 한정 |
| `source-field` | 선택 — 값 목록을 필드에서 채울 때. **수동 목록으로 바꾸면 이 속성이 소멸** (`ae0f567`) |
| `datatype-customized` + `default-format` | 표시 형식 지정 시 (`*#월`, `*YY-MM` 등) |

datetime 매개변수는 `<members>` 없이 `formula='#2026-01-01 00:00:00#'` 형태,
`@param-domain-type` 제거 (`8b136bb` — 목록→datetime 전환 관찰).

## 불변 조건

1. **쓰는 워크시트마다** `<datasource-dependencies datasource='Parameters'>`에 이 `<column>`
   사본이 들어간다 — **단 `<members>`는 빼고** `<calculation>`만 (`b13bc5a`)
2. 계산 수식에서 참조는 반드시 `[Parameters].[매개 변수 N]` 한정 —
   한정 없으면 계산이 통째로 깨진다 (층 3, lint ⑦-c)
3. **삭제 시** 대시보드의 `zone[@type-v2='paramctrl']`도 함께 지운다 (`57e556a` — 동시 삭제 관찰).
   남기면 죽은 컨트롤 존
4. 대시보드에 컨트롤을 보이려면 `zone[@type-v2='paramctrl']` 추가 (`b13bc5a`)
5. 매니페스트 항목 불필요 — 매개변수 추가로 매니페스트가 바뀐 관찰 없음

## 재저장 검증

`value`(현재값)는 어차피 노이즈로 계속 바뀐다 — diff 판독 시 무시.

**삽입 위치 (E2E 2026-08-06 확인)** — Parameters의 `<column>`도 **`name` 문자열
오름차순** 정렬이다. 괄호 포함 비교라 `[매개 변수 10]` < `[매개 변수 11]` < `[매개 변수 1]`
(`'0'`·`'1'` < `']'`). 끝에 붙이면 Tableau가 정렬 위치로 옮긴다(내용 불변).

**paramctrl 존 (E2E 확인)** — 기존 컨트롤 존을 복제해 `id`(파일 내 유일)·`param`·제목만
바꿔 넣으면 수용된다. `w`/`x`는 레이아웃 플로우가 재계산하므로 대략 값이면 된다(노이즈).

## twb-lint 연계

`ref.notation`(⑦-c) — `[Parameters]` 한정 검사. `calc.field_refs`(②) — 실존 검사.
