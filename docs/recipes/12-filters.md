# 레시피 12 — 필터 (categorical · quantitative · groupfilter 속성)

| 항목 | 값 |
|---|---|
| 판정 표면 | T4 |
| UI 경로 | 필드를 필터 선반에 드래그 > 편집 |
| 근거 | MA_008 `7353886` `529e436` `146f488` `e6a02cc` `358c382` `b63e1b1` `57e556a` |
| Tableau | 2026.1 |

## categorical (`7353886`)

```xml
<filter class='categorical' column='[none:Calculation_4888733706485760:nk]'>
  <groupfilter function='member' level='[none:…:nk]' member='&quot;true&quot;' … />
</filter>
```

- `column`은 인스턴스 표기. boolean 필터 member는 `'true'`
- 멤버 여러 개면 `groupfilter function='union'` 아래 member들.
  **단일 멤버로 좁히면 union 껍데기가 사라지고 member 하나만 남는다** (`e6a02cc`)

## quantitative (`7353886` `529e436`)

```xml
<filter class='quantitative' column='[usr:Calculation_4888733707464705:qk]' included-values='in-range'>
  <min>1</min>
  <max>1</max>
</filter>
```

시트 복제 시 필터 값이 그대로 상속된다 — min/max 갱신을 잊으면 전 시트가 같은 값
(`529e436`이 그 수정).

## groupfilter의 `user:` 속성 — UI 경로 지문

**같은 결과라도 UI 경로에 따라 속성 조합이 다르다** (`358c382`):

| UI 경로 | 속성 |
|---|---|
| 목록에서 선택(수동) | `user:ui-manual-selection='true'` `user:ui-manual-selection-all-when-empty='true'` (`e6a02cc` — 단일 멤버로 좁힐 때 새로 붙음) |
| 필터 편집 대화상자 다른 경로 | `user:ui-domain='relevant'` `user:ui-enumeration='inclusive'` `user:ui-marker='enumerate'` |

복제 판별에도 쓰인다 — `7e15b84`는 이 속성의 유무로 어느 시트에서 복제됐는지 역추론했다.
AI 저작 시: 관찰된 조합 중 하나를 그대로 쓴다. 섞지 말 것(`추정` — 섞은 관찰 없음).

## filter-group (`57e556a`)

`<filter class='categorical' column='…' filter-group='3'>` — 그룹 번호 속성이 붙는 변형 관찰.
의미 미상(`추정`: 관련 필터 묶음). 관찰대로만 복제.

## 재저장 검증

UI 형태 그대로면 정규화 관찰 없음. twb-lint: `shelf.refs`(⑪) — 필터 column 실존·표기.
