# 레시피 01 — 계산 필드 추가

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 |
| UI 경로 | 데이터 패널 > **계산된 필드 만들기** |
| 근거 | MA_008 `b13bc5a`(UI·확인) · `23690bc`(AI 저작 수용) · `98fb49c`(참조 0 유효) |
| Tableau | 2026.1 |

## XML 변경 — 어디에 무엇을

`<datasource>` 직속으로 `<column>` 1개. 자식으로 `<calculation>`.

```xml
<column caption='C_목표값' datatype='real' name='[C_계획값(복사본)_5290055430385670]' role='measure' type='quantitative'>
  <calculation class='tableau' formula='SUM(IF [idct_gcode] = &quot;목표&quot; THEN [idct_val] END)' />
</column>
```

| 속성 | 값 규칙 |
|---|---|
| `caption` | 표시명. 이후 개명해도 `name`은 유지된다 — 참조가 안 깨진다 (`e6a02cc`) |
| `name` | 내부 키. **모든 참조는 이걸 쓴다.** UI 신규 생성 = `[Calculation_<대략 16자리 숫자>]`, UI 복제 = `[<원본caption>(복사본)_<숫자>]`. AI가 임의 고유 숫자로 발급해도 수용됨 (`23690bc`: `Calculation_7200000000000001`~`5` 수용) |
| `datatype`/`role`/`type` | 수식 결과에 맞게 — 측정값: `real·measure·quantitative`, 차원 문자열: `string·dimension·nominal`. 라벨 수식을 집계식으로 바꾸면 `string→real`, `nominal→ordinal` 동반 전환 (`1d2aa95`) |
| `formula` | XML 이스케이프 필수 — `"`→`&quot;`, 줄바꿈→`&#13;&#10;`. 주석(`//`)도 수식 문자열 일부 (`b63ddda`) |

## 불변 조건

1. **워크시트가 이 필드를 쓰면** 그 워크시트의 `view/datasource-dependencies`에
   같은 `<column>`(+ 필요 시 `<column-instance>`)이 **복제돼 들어가야 한다** (`b13bc5a`).
   수식이 참조만 해도(선반에 없어도) 원본 컬럼이 의존성에 올라온다 (`35db682`)
2. **참조 0이어도 유효** — 어떤 시트도 안 쓰는 필드는 그냥 존재해도 된다 (`98fb49c`)
3. **빈 껍데기도 유효** — `formula=''`로 저장했다가 나중에 채우는 흐름이 무해하다 (`7f4e665`→`35db682`)
4. 다른 필드 참조는 `[name]` 표기 (calc 안에서는 `[Calculation_...]` — 07 G8의 2종 표기 주의).
   매개변수 참조는 `[Parameters].[매개 변수 N]` 한정 필수 (lint ⑦-c)
5. 매니페스트 항목 불필요 — 계산필드 추가만으로 매니페스트가 바뀐 관찰 없음

## 재저장 검증 (레시피가 정본인가)

`b13bc5a`(UI 저장 원본) 형태 그대로 쓰면 정규화 대상 아님. `23690bc`에서 AI 저작분
"한 글자도 안 바뀜" 확인. 주의: 의존성 `column-instance` **순서**는 컬럼 정의 순서를
따른다 — 어기면 Tableau가 재배열한다 (`227b603` 정규화 1)

## twb-lint 연계

`calc.field_refs`(②)·`calc.functions`·`calc.aggregation`이 이 표면을 검사.
임시(ad-hoc) 계산은 별도 레시피(datasource 등재 없이 dependencies에만, `9cac21f`).
