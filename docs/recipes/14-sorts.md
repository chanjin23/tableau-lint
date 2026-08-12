# 레시피 14 — 정렬 (computed-sort · manual-sort)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 필드 우클릭 > 정렬 > 필드 기준 / 수동 |
| 근거 | MA_008 `b13bc5a`(UI·확인) `23690bc`(AI 수용) `146f488` `6154648`(AI) · **MA_011 260812**(UI 관찰 + 실패 실측) |
| Tableau | 2026.1 |

## 참조 표기 — 둘 다 **데이터 원본 한정형**이다 ★

`column`·`using`은 `[<데이터소스 이름>].[<인스턴스>]`로 쓴다.
한정자를 빼면 XSD도 twb-lint도 통과하지만 Tableau가 로드하면서 정렬만 버린다:

```
'SEC05_그리드표' 오류:
[none:Calculation_1238633066082307:nk] 필드가 정의되지 않았습니다. 정렬 지정을 무시합니다.
```

**발견이 어렵다.** 경고를 닫으면 워크북은 열리고 나머지 기능은 전부 정상이라
"경고 한 번 뜨고 마는 것"으로 오인하기 쉽다. 무시하면 **틀린 순서의 표가 그대로 배포된다.**

실측(2026-08-12, 실파일 47개): `computed-sort@column` 503 · `@using` 503 ·
`manual-sort@column` 432가 전부 한정형이고 비한정은 0건이다.

대조 — 정렬과 **반대로** 한정자를 쓰지 않는 자리: `groupfilter@level`(레시피 12) ·
`column-instance@name`/`@column`(정의부라 한정자 없음).

## 필드 기준 정렬 (`b13bc5a` · MA_011 260812 재확인)

```xml
<computed-sort column='[federated.<ds-id>].[none:accs_nm:nk]'
               direction='ASC'
               using='[federated.<ds-id>].[min:scrn_seq:qk]' />
```

`column` = 정렬 대상 차원 인스턴스, `using` = 정렬 기준 집계 인스턴스.
`using`이 가리키는 인스턴스는 워크시트 `datasource-dependencies`에 있어야 한다
(`derivation='Min'` → `[min:…:qk]`). 원본 필드에 `<column>` 정의가 없으면 레시피 01 참조 —
`scrn_seq`가 정확히 그 부류다.

## 수동 정렬 (`146f488` `6154648` · **MA_011 260812 실제 XML**)

```xml
<manual-sort column='[federated.<ds-id>].[:Measure Names]' direction='ASC'>
  <dictionary>
    <bucket>&quot;[federated.<ds-id>].[usr:Calculation_2375252988260358:qk]&quot;</bucket>
    <bucket>&quot;[federated.<ds-id>].[usr:C_매출총이익(복사본)_1503340500520966:qk]&quot;</bucket>
  </dictionary>
</manual-sort>
```

- `<bucket>` 텍스트는 **인스턴스 문자열을 큰따옴표로 감싼 형태** —
  `[:Measure Names]` 필터의 `groupfilter@member`와 완전히 같은 표기다 (레시피 12)
- bucket 순서 = 표시 순서(좌→우). 그런데 `direction='ASC'`도 함께 붙는다
- 측정값 선반의 열 순서는 **`<manual-sort>`로만** 정한다 — `[:Measure Names]` 필터의
  union 멤버 순서는 Tableau가 caption 가나다순으로 재작성하고, 내부 `name`을
  원하는 순서로 발급하는 우회도 듣지 않는다 (MA_011 재저장 실측)

주의 — 필터에서 멤버를 빼도 manual-sort dictionary에는 **옛 bucket이 남을 수 있다**
(`9cac21f` 달성률 bucket 잔존, 무해).

## `<view>` 안 위치 (MA_011 260812)

정렬 태그는 **정렬 대상 필드의 `<filter>` 직후**에 온다.

```
datasource-dependencies (Parameters) · datasource-dependencies (main)
filter        [:Measure Names]
manual-sort   [:Measure Names]
filter        [none:C_G_구분코드:nk]
computed-sort [none:C_G_구분코드:nk]
filter        [none:idct_gcode:nk]
slices · aggregation
```

필터가 없는 필드를 정렬하면 어디 놓이는지는 이 표본으로 알 수 없다.
`datasource-dependencies` 다음 · 첫 `<filter>` 앞에 둔 AI 저작본도 경고 없이 열렸고,
재저장 시 위 순서로 정규화됐다 — **순서는 노이즈다.**

## 매니페스트

`SortTagCleanup`은 `manual-sort`·`computed-sort` **공통 게이트**다.
`computed-sort`만 쓴 워크북에서도 요구됐다 (MA_011 260812, twb-lint `manifest.gates`가 검출).
없이 쓰면 로드 거부.

## 재저장 검증

한정형 `computed-sort`·`manual-sort`는 **무수정 수용**됐다 (MA_011 재저장 검증).
정규화는 `<view>` 자식 순서뿐이다.
twb-lint: `manifest.gates`(⑥-a) · `ref.notation`(⑦-e, 한정 표기) · `shelf.refs`(⑪, 참조 해소).
