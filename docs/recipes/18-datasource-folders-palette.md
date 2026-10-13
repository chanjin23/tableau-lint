# 레시피 18 — 필드 폴더 · 데이터소스 색상 팔레트

| 항목 | 값 |
|---|---|
| 판정 표면 | T2(정리)·T4(색) |
| UI 경로 | 데이터 패널 > 필드 드래그로 폴더 이동 / 마크 카드 > 색상 편집 |
| 근거 | MA_008 `b13bc5a` `7f4e665` `57e556a` `b6256cf` `23690bc`(AI 수용) `b67ed82` |
| Tableau | 2026.1 |

## 폴더 (`b13bc5a` `57e556a` `b6256cf`)

```xml
<datasource>
  <folders-common>
    <folder name='01_공통'>
      <folder-item name='[Calculation_…]' type='field' />
    </folder>
  </folders-common>
</datasource>
```

- 폴더 신설 = `+<folder @name>` (빈 요소 가능, `b6256cf` — 비어 있다가 나중에 채움)
- 필드 이동 = 대상 폴더에 `+<folder-item>` (원 폴더에서 제거)
- `folder-item@name`은 필드의 **내부 name** (caption 아님)

## 색상 팔레트 — 데이터소스 수준이 정본 (`23690bc` `b6256cf` `b67ed82`)

```xml
<datasource>
  <column … name='[Calculation_7200000000000003]' role='dimension' type='nominal' />
  <column-instance column='[Calculation_7200000000000003]' derivation='None'
                   name='[none:Calculation_7200000000000003:nk]' pivot='key' type='nominal' />
  <layout … />
  <style>
    <style-rule element='mark'>
      <encoding attr='color' field='[none:Calculation_7200000000000003:nk]' type='palette'>
        <map to='#002c63'><bucket>&quot;실적&quot;</bucket></map>
        <map to='#a0cbe8'><bucket>&quot;계획&quot;</bucket></map>
      </encoding>
    </style-rule>
  </style>
</datasource>
```

- 값→색 매핑은 여기 한 곳. 시트들은 인코딩 참조만 하고 **상속**받는다 (레시피 10·13)
- 색 변경 = `map@to`만 교체 (`b6256cf` 6건)
- 필드별 `encoding` 블록 추가로 새 필드 팔레트 정의 (`b67ed82` 상수 차원 검정)

### ⚠️ 팔레트 키 인스턴스는 **데이터소스 직속에도** 선언한다 (2026-10-13 MA_028 제보 · 05 F5-q)

- `encoding@field`가 가리키는 `[파생:필드:접미]`는 **데이터소스 직속 `<column-instance>`**로
  선언돼 있어야 한다 (위치: `<column>` 목록 뒤, `<layout>`·`<folders-common>` 앞).
  **워크시트의 `<datasource-dependencies>` 안 선언만으로는 부족하다** — 직속 선언이 없으면
  Tableau가 팔레트를 **통째로 버린다**: 오류 대화상자 없이 색이 기본 색으로 나오고,
  저장하면 항목이 사라진다. 린트 규칙 ⑲(`palette.instance_declared`)이 WARNING으로 말한다
- 실측: 파생 모양 팔레트 키 3629건 중 **3626건**이 직속 선언을 갖는다 (반례 3건은 한 파일의
  합성 ID — 직속 `column-instance`가 0개인 저작물이다)
- 인과 **확정** (2026-10-13 분리 실험): 색이 적용되던 파일에서 팔레트 항목은 두고 직속
  `column-instance`만 지우자 **색이 적용되지 않았다.** 직속 선언은 필요조건이다
- **규칙으로 만들지 않은 두 가지** (같은 제보가 제안했으나 실측이 반례를 냈다):
  - `usr:` 키의 `column@role='measure'` — `measure` 2002 : `dimension` **41**. 정상본에 반례가 있다
  - `[:Measure Names]` 별칭 키의 직속 인스턴스 — 22,904건 중 1,529건 미선언(낡은 별칭 키가 남는다)
- 직속 `column-instance`를 워크시트 사용분의 **합집합**으로 채워야 하는지는 미확정이다
  (정본 MA_008은 합집합 모양). 팔레트 키는 최소한 넣는다

## 재저장 검증

정규화 관찰 없음 (AI 저작 `23690bc` 수용). folder-item 정렬 규칙 미관찰 —
데이터소스 column처럼 정렬될 가능성 있음(`추정`), diff에 위치 이동 나오면 기록할 것.
