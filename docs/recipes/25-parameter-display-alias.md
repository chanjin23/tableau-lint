# 레시피 25 — 매개변수 표시 이름(alias) + 값으로 유형 제어

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 · T3 |
| UI 경로 | 매개변수 만들기 > 허용 가능한 값 '목록' > **표시 형식 열(별칭) 입력** → 계산 필드·필터로 뷰 유형 전환 |
| 근거 | **코퍼스 결과형 표본 2건** (MA_015 `…_JWP_260903.twbx` · MA_002 `…_JWP_260728.twbx`). **전/후 UI diff 아님 — 등급 `추정`**. 아래 ★ 항목이 관찰 승격 대상 |
| Tableau | 2026.1 |

레시피 02는 `<member value>`만 다룬다. **값(`value`)과 사용자에게 보이는 글자(`alias`)가
다른 목록**이 실무에서 쓰이는 형태다 — 값은 계산이 읽고, 별칭은 컨트롤이 보여 준다.

## 형태 ① — 불리언 스위치 (MA_015 `P_LINE/PRD`)

`TRUE`=공정 라인별, `FALSE`=Target 제품별. 값은 `true`/`false`, 컨트롤에는 한글이 뜬다.

```xml
<column alias='공정 라인별' caption='P_LINE/PRD' datatype='boolean' name='[매개 변수 5]'
        param-domain-type='list' role='measure' type='nominal' value='true'>
  <calculation class='tableau' formula='true' />
  <aliases>
    <alias key='false' value='Target 제품별' />
    <alias key='true' value='공정 라인별' />
  </aliases>
  <members>
    <member alias='공정 라인별' value='true' />
    <member alias='Target 제품별' value='false' />
  </members>
</column>
```

## 형태 ② — 정수 목록 (MA_002 `P_MONTH`)

값은 정수(계산이 산술에 쓴다), 표시는 `1월`…`12월`. 정수에 `datatype-customized='true'`가 붙는다.

```xml
<column alias='2월' caption='P_MONTH' datatype='integer' datatype-customized='true'
        name='[매개 변수 3]' param-domain-type='list' role='measure' type='quantitative' value='2'>
  <calculation class='tableau' formula='2' />
  <aliases><alias key='1' value='1월' /> … <alias key='12' value='12월' /></aliases>
  <members><member alias='1월' value='1' /> … <member alias='12월' value='12' /></members>
</column>
```

## 규칙 — 레시피 02에 더해지는 것

| 자리 | 규칙 |
|---|---|
| `<member @alias>` | 표시 글자. `@value`는 **리터럴 표기** (불리언 `true`, 정수 `2`, 문자열은 `&quot;…&quot;` ★) |
| `<aliases>/<alias @key @value>` | `member`의 `(value→alias)`를 **한 번 더** 적는다. 둘이 짝이 맞아야 한다 — `key`=member `@value`, `value`=member `@alias` |
| 자식 순서 | `<calculation>` → `<aliases>` → `<members>` |
| `column@alias` | **현재 선택값의 표시 이름.** `@value`와 같은 노이즈 — 저장마다 바뀐다. 생성 시 기본값의 alias와 맞춘다 |
| `formula` | 기본값의 **값**(별칭 아님). 불리언 `true` |
| 워크시트 의존성 복사본 | `<members>`는 빠지고 **`<aliases>`는 남는다** (MA_015 실측: `calculation`+`aliases`) |

## 값으로 유형을 제어하는 계산 (MA_015)

불리언이면 매개변수를 **직접** 조건으로 쓴다 (`= TRUE` 불필요). 이름은 `[Parameters].[…]` 한정.

```text
// 유형 스위치 — 행의 구분값이 선택한 유형과 같으면 TRUE. 시트 필터에 올려 그 유형 행만 남긴다
IF [Parameters].[매개 변수 5] THEN [rpt_gbn] = "공정 라인별"
ELSE [rpt_gbn] = "Target 제품별" END

// 반전 — 시트 필터는 쓰지 않는다. 대시보드 **존 가시성**이 쓴다 (datagraph → 레시피 26):
// 반대편 컨테이너를 "스위치가 FALSE일 때 보이게" 하는 입력이다
NOT [Parameters].[매개 변수 5]

// 유형에 따라 다른 매개변수를 고르는 라벨
IF [Parameters].[매개 변수 5] THEN [Parameters].[매개 변수 1]
ELSE [Parameters].[P_ACCS_NM(복사본)_…] END
```

전환 계산(`datatype=boolean` · `role=dimension`)을 **시트 필터**에 건다 (MA_015 `260903` 실측:
이 계산을 거는 시트 **42개 전부** `member='true'` 하나뿐 — `false` 쪽은 0):

```xml
<filter class='categorical' column='[federated.…].[none:Calculation_…:nk]' filter-group='5'>
  <groupfilter function='member' level='[none:Calculation_…:nk]' member='true'
               user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />
</filter>
```

- **시트는 하나이고 필터가 보이는 행을 바꾼다** — 마크 유형·차트 모양을 바꾸는 것이 아니다.
  이 절의 "유형 제어"는 **데이터 구분값** 제어다. **컨테이너를 통째로 보이고 숨기는**
  유형 제어(동적 존 표시)는 별개 표면이다 → **레시피 26**. 마크 유형을 바꾸는 방식은 코퍼스에 없다 (★ O5).
- 대시보드에는 컨트롤을 `zone[@type-v2='paramctrl']`로 놓는다 (레시피 02 · 16). 컨트롤이
  한글 별칭을 보여 준다.

## 불변 조건

1. 위 계산을 쓰는 시트 **의존성에 매개변수 복사본**(`aliases` 포함·`members` 제외) +
   `column-instance`/`column`이 들어간다 — 레시피 01 불변 1·1-b와 같다
2. **`aliases`와 `members`의 짝이 어긋나면** 컨트롤이 별칭을 못 보이거나 값이 비는 것으로
   추정 ★ (`key`≠member `@value` 인 표본은 코퍼스에 없다 — 깨뜨려 보지 못했다)
3. 삭제 시 paramctrl 존 동반 삭제 — 레시피 06 그대로
4. **대시보드 의존성 사본은 `members`를 포함한다** — 워크시트 사본(제외)과 다르다. 제외하고 썼더니
   Tableau가 재저장 때 `<members>`를 채웠다 (레시피 26 재저장 diff, 2026-10-15)
5. **계산 필드가 매개변수를 참조하면** 그 계산이 있는 `<datasource>` 안에 `<datasource-dependencies
   datasource='Parameters'>`(사본, `members` 제외)가 `<semantic-values>` 뒤·`<object-graph>` 앞에
   생긴다. 손저작 시 **없어도 열린다** — Tableau가 재저장 때 채운다(정규화)

## ★ 미관찰 — 소유자 관찰 시나리오

한 저장 = 한 조작. 아래를 하나씩 저장해 diff를 뜬다 (E2E-3 방식).

| # | 조작 | 알고 싶은 것 |
|---|---|---|
| O1 | 문자열 목록 매개변수 `P_유형`(값 `"월별"`·`"분기별"`) 만들기, **표시 형식 열은 비움** | 별칭 없는 문자열 목록의 `member` — 레시피 02와 같은가 |
| O2 | 같은 매개변수의 **표시 형식 열에 `월간 보기`·`분기 보기` 입력** | 문자열 `alias` 키 표기(`key='&quot;월별&quot;'`?), `column@alias` 등장 여부 |
| O3 | 한쪽 별칭만 고치기 | `aliases`·`members`가 **같이** 바뀌는가 (짝 불변 조건 확인) |
| O4 | 별칭 매개변수를 대시보드 컨트롤로 놓고 값 전환 후 저장 | 노이즈(`value`·`column@alias`)만 바뀌는가 |
| O5 | 매개변수로 **마크 유형**(막대↔선)이 바뀌는 구성 (계산 필드 2개 + 시트 2벌 + 각 필터) | 단일 시트의 `mark@class`를 매개변수로 바꾸는 방식은 없다고 알려져 있다 — 시트 2벌 구성의 XML 형태를 확정 |

## 저작 검증 (2026-10-15) — **린트 수준까지만**

(⚠️ 이 샘플은 **필터 방식**이다 — 컨테이너 가시성은 레시피 26의 샘플이 다룬다.)
레시피 20·21·22·12·03·25만으로 손저작한 샘플(CSV 1개 · 매개변수 2종[불리언 `P_VIEW`·정수 `P_MONTH`]
· 불리언 스위치 계산 2개 · 필터 2개 · 시트 1 · 대시보드 1[paramctrl 2 + 시트 존])을
`twb_validate` → **passed · findings 0** (1회차).

| 음성 대조 | 결과 |
|---|---|
| 계산에서 `[Parameters].` 한정자 제거 | `ref.notation` WARNING ✅ 잡힘 |
| `aliases`의 `value`만 `members`와 다르게 | **findings 0 — 못 잡는다** (불변 조건 2 규칙 부재 확인) |

⚠️ **Tableau에서 열어 보지 않았다.** 대시보드 최소 골격(레시피 없음 — MA_015 실파일 형태를 따랐다,
`devicelayouts` 생략)과 `aliases` 짝은 소유자 관찰(O1~O5)과 열기 확인이 필요하다.
E2E-2의 교훈대로 **린트 통과 ≠ 열린다.**

## 재저장 검증

`@value`·`column@alias`는 노이즈. 그 외 diff가 나면 신호다.

## twb-lint 연계

`ref.notation`(⑦-c) — `[Parameters]` 한정. `calc.field_refs`(②) — 실존. `palette`·`named.refs`는 무관.
현재 `aliases`↔`members` 짝을 검사하는 규칙은 **없다** (관찰 전이라 규칙화하지 않는다 — 07 ERROR는 확신할 때만).
