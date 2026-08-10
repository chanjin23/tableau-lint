# 레시피 24 — 도구 설명 뷰 (viz in tooltip)

| 항목 | 값 |
|---|---|
| 판정 표면 | T3 · T4 |
| UI 경로 | 마크 카드 > **도구 설명** > 편집창 > **삽입 > 시트 > \<대상 시트\>** |
| 근거 | 2026-08-10 관찰 `관찰_10` (소유자 조작, UI · 통제 diff) |
| Tableau | 2026.1.1 |

**한 조작이 네 자리를 건드린다.** 도구 설명 텍스트만 고치면 안 된다 —
Tableau가 뒤에서 집합과 필터를 만들어 두 시트를 배선한다.

## ① 매니페스트 +1

```xml
<VizInTooltipHideWorksheet />
```

`SheetIdentifierTracking`과 `WindowsPersistSimpleIdentifiers` 사이에 알파벳 순으로 들어간다.

## ② 데이터 원본에 숨은 집합이 생긴다

```xml
<column datatype='string' name='[지역]' role='dimension' type='nominal' />
<column datatype='string' name='[품목]' role='dimension' type='nominal' />
<group caption='도구 설명(지역,품목)' hidden='true' name='[Tooltip (지역,품목)]'
       name-style='unqualified' user:auto-column='sheet_link' user:ui-vit-column='true'>
  <groupfilter function='crossjoin'>
    <groupfilter function='level-members' level='[지역]' />
    <groupfilter function='level-members' level='[품목]' />
  </groupfilter>
</group>
```

- 이름 규칙: `[Tooltip (<원본 시트의 차원들, 쉼표>)]` · caption은 한국어 `도구 설명(…)`
- **동작 집합과 같은 모양**(`hidden` + `auto-column='sheet_link'` + crossjoin)에
  `user:ui-vit-column='true'`가 하나 더 붙는다 — 이게 도구 설명 뷰 표식이다
- `crossjoin` 아래 `level-members`가 **원본 시트에 올라간 차원 수만큼** 들어간다
- 그 차원들의 `<column>` 정의가 데이터 원본에 실체화된다

## ③ 원본 시트 — 도구 설명 본문

`<pane>` 안, `<encodings>` **다음**:

```xml
<customized-tooltip>
  <formatted-text>
    <run fontcolor='#757575'><![CDATA[<Sheet name="관찰_툴팁시트" maxwidth="300" maxheight="300" filter="<All Fields>">]]></run>
    <run>Æ&#10;</run>
    <run fontcolor='#757575'>지역:&#9;</run>
    <run bold='true'><![CDATA[<[federated.…].[none:지역:nk]>]]></run>
    <run>Æ&#10;</run>
    <run fontcolor='#757575'>품목:&#9;</run>
    <run bold='true'><![CDATA[<[federated.…].[none:품목:nk]>]]></run>
    <run>Æ&#10;</run>
    <run fontcolor='#757575'>매출:&#9;</run>
    <run bold='true'><![CDATA[<[federated.…].[sum:매출:qk]>]]></run>
  </formatted-text>
</customized-tooltip>
```

| 자리 | 규칙 |
|---|---|
| 시트 삽입 | `<Sheet name="…" maxwidth="…" maxheight="…" filter="…">` — **CDATA 안의 문자열**이다 |
| **크기** | `maxwidth`/`maxheight`. **기본값이 이미 300×300**이다 |
| `filter` | `<All Fields>` = 원본 시트의 모든 차원으로 거른다 |
| 필드 참조 | `<[데이터원본].[인스턴스]>` — 꺾쇠로 감싸고 CDATA로 이스케이프 |
| 줄바꿈 | `<run>Æ&#10;</run>` — `Æ`는 Tableau의 줄바꿈 표식. 탭은 `&#9;` |

> **크기 조절이 UI에서 안 보이면** 이 텍스트를 직접 고치면 된다 — 도구 설명 편집창에
> `<Sheet name="관찰_툴팁시트" maxwidth="300" maxheight="300" ...>` 줄이 그대로 보인다.
> 숫자만 바꾸면 `maxwidth`/`maxheight`가 바뀐다. (UI 경로는 미관찰 — `?`)

## ④ 대상 시트 — 동작 필터가 걸린다

툴팁으로 삽입된 시트(`관찰_툴팁시트`) 쪽에:

```xml
<column datatype='string' name='[지역]' role='dimension' type='nominal' />
<column datatype='string' name='[품목]' role='dimension' type='nominal' />
```
```xml
<filter class='categorical' column='[federated.…].[Tooltip (지역,품목)]'>
  <groupfilter function='crossjoin' user:ui-action-filter='[Action - 관찰_툴팁시트]'
               user:ui-enumeration='all' user:ui-marker='enumerate'>
    <groupfilter function='level-members' level='[지역]' />
    <groupfilter function='level-members' level='[품목]' />
  </groupfilter>
</filter>
<slices>
  <column>[federated.…].[Tooltip (지역,품목)]</column>
</slices>
```

- 필터의 `column`이 ②의 **숨은 집합**을 가리킨다 (필드가 아니라 집합이다)
- `user:ui-action-filter='[Action - <대상 시트명>]'` — 동작 이름 규칙
- `<slices>`에도 같은 집합이 등록된다
- 대상 시트의 `datasource-dependencies`에 원본 시트의 차원 `<column>` 사본이 추가된다

## 불변 조건

1. **한 조작 = 4자리** — 매니페스트 · 데이터 원본 집합 · 원본 시트 `customized-tooltip` ·
   대상 시트 필터+slices. 하나라도 빠지면 배선이 끊긴다
2. 집합 이름 `[Tooltip (…)]`이 세 자리(정의 · 필터 `column` · slices)에서 **글자 그대로 일치**
3. `crossjoin` 아래 `level-members` 목록이 ②와 ④에서 **동일**
4. `<actions>` 블록은 **생기지 않는다** — 도구 설명 뷰는 `<action>`이 아니라
   `user:ui-action-filter` 속성으로만 표현된다

## 미관찰 (`?`)

- 크기(`maxwidth`/`maxheight`)를 **UI에서** 바꾸는 경로 — 기본값 300×300만 관찰
- 삽입 시트를 지웠을 때 숨은 집합이 같이 지워지는지
- 원본 시트 차원이 0개일 때(`filter='<All Fields>'`의 crossjoin 대상 없음)

## 재저장 검증 · twb-lint

`twb_validate` → `passed=true`, findings 0.
twb-lint: `set.definition`(⑨)가 숨은 집합의 기반 필드를 본다 · `shelf.refs`(⑪).
`customized-tooltip` 안의 필드 참조를 보는 규칙은 **아직 없다**.
