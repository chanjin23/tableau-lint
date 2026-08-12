# 레시피 22 — 빈 시트에 첫 뷰 만들기 (동반 변경 전량)

| 항목 | 값 |
|---|---|
| 판정 표면 | T2 · T4 |
| UI 경로 | 빈 워크시트에 필드 드래그 (열 · 행 · 색상) |
| 근거 | 2026-08-10 관찰 `관찰_B_CSV연결만.twb` → `관찰_00_base.twb` 대조 (소유자 조작, UI) |
| Tableau | 2026.1.1 |

레시피 [11](./11-shelf-expressions.md)이 *선반 표현식의 문법*이라면, 여기는
**빈 시트에 처음 필드를 놓을 때 같이 생기는 것 전부**다. 이걸 빠뜨리면 선반
문자열만 맞고 필드가 안 뜬다.

관찰 조작: 시트 이름을 `관찰_주시트`로 바꾸고 열=`품목` · 행=`매출` · 색상=`지역`.
두 번째 시트 `관찰_툴팁시트`는 열=`기준월`(월) · 행=`수량`.

## 한 조작이 건드리는 자리 6곳

| # | 자리 | 내용 |
|---|---|---|
| 1 | `worksheet/table/view/datasources` | 쓰는 데이터 원본 참조 |
| 2 | `worksheet/table/view/datasource-dependencies` | `column-instance` + `column` 사본 |
| 3 | `worksheet/table/rows`·`cols` | 선반 표현식 |
| 4 | `worksheet/…/pane/encodings` | 색·크기 등 마크 인코딩 |
| 5 | `windows/window/cards` | 범례 카드 (`edge name='right'`) |
| 6 | `windows/window/viewpoint/highlight` | **자동 생성** 하이라이트 필드 목록 |

## ① + ② 뷰가 쓰는 필드 선언

```xml
<view>
  <datasources>
    <datasource caption='관찰_data' name='federated.1l6p7750sw7alz1d1tbgb1y30jni' />
  </datasources>
  <datasource-dependencies datasource='federated.1l6p7750sw7alz1d1tbgb1y30jni'>
    <column-instance column='[지역]' derivation='None' name='[none:지역:nk]' pivot='key' type='nominal' />
    <column-instance column='[품목]' derivation='None' name='[none:품목:nk]' pivot='key' type='nominal' />
    <column-instance column='[매출]' derivation='Sum'  name='[sum:매출:qk]'  pivot='key' type='quantitative' />
    <column datatype='integer' name='[매출]' role='measure'   type='quantitative' />
    <column datatype='string'  name='[지역]' role='dimension' type='nominal' />
    <column datatype='string'  name='[품목]' role='dimension' type='nominal' />
  </datasource-dependencies>
</view>
```

- **`column-instance`가 먼저, `column`이 뒤.** 섞이지 않는다
- **`column` 사본은 name 오름차순** (매출 · 지역 · 품목). datasource의 `<column>`
  정렬 규칙(레시피 01 E2E-1)과 같은 성질이다
- `column-instance` 순서는 오름차순이 아니다 — 관찰값은 `지역 · 품목 · 매출`이고
  선반 배치 순서와도 다르다. **규칙 미관찰**(`?`). 순서를 지어내지 말고 관찰대로 쓴다
- `<column>`은 데이터 원본 정의의 **사본**이다. 원본에 없는 필드를 여기만 넣으면
  dangling이 된다 (twb-lint 규칙 ②가 이 자리를 본다)

### 인스턴스 이름 표기

| 필드 | derivation | name | 규칙 |
|---|---|---|---|
| 차원(문자열) | `None` | `[none:지역:nk]` | 비집계 + 명목 |
| 측정값(합계) | `Sum` | `[sum:매출:qk]` | 집계 + 양적 |
| 날짜(연도 단위) | `Year` | `[yr:기준월:ok]` | 날짜 부분 + 순서형 |

`type`은 `nominal` / `quantitative` / `ordinal`로 접미(`nk`/`qk`/`ok`)와 짝이다.
`pivot='key'`는 전 인스턴스 공통.

## ③ 선반

```xml
<rows>[federated.1l6p7750sw7alz1d1tbgb1y30jni].[sum:매출:qk]</rows>
<cols>[federated.1l6p7750sw7alz1d1tbgb1y30jni].[none:품목:nk]</cols>
```

**선반은 `[데이터원본].[인스턴스]` 2단 한정**이다. `datasource-dependencies` 안의
`column-instance@name`은 한정자 없는 1단이다 — 같은 필드를 두 표기로 쓴다 (07 G8).

## ④ 색상 인코딩

```xml
<pane selection-relaxation-option='selection-relaxation-allow'>
  <view><breakdown value='auto' /></view>
  <mark class='Automatic' />
  <encodings>
    <color column='[federated.1l6p7750sw7alz1d1tbgb1y30jni].[none:지역:nk]' />
  </encodings>
</pane>
```

`<encodings>`는 `<mark>` **뒤**에 온다.

## ⑤ 범례 카드 — 창 쪽에 붙는다

```xml
<edge name='right'>
  <strip size='160'>
    <card pane-specification-id='0' param='[federated.…].[none:지역:nk]' type='color' />
  </strip>
</edge>
```

색상에 필드를 올리면 `windows/window/cards`에 `edge name='right'`가 **새로 생긴다**.
`param`은 선반과 같은 2단 표기, `pane-specification-id='0'`은 첫 pane.

## ⑥ `<viewpoint><highlight>` — Tableau가 자동으로 만든다

```xml
<viewpoint>
  <highlight>
    <color-one-way>
      <field>[federated.…].[none:지역:nk]</field>
      <field>[federated.…].[none:품목:nk]</field>
    </color-one-way>
  </highlight>
</viewpoint>
```

**손으로 쓰는 것이 아니다.** 뷰에 올린 차원 인스턴스가 자동으로 들어간다
(주시트: 지역·품목 / 툴팁시트: `[yr:기준월:ok]` 하나).

> 이 자리가 실사용 워크북에서 **삭제된 필드의 잔재**가 남는 곳이다. 필드를 지워도
> 이 목록에서 자동으로 빠지지 않아 dangling 참조로 남는다 (2026-08-10 MA_002 감사:
> 대시보드 창 4개의 하이라이트 목록에 지운 필드가 남아 있었다). 파일이 열리고
> 화면도 정상이라 **무해하지만, twb-lint 규칙 ②가 WARNING으로 잡는다**.
>
> **지워도 된다.** `<highlight>` 블록을 통째로 제거한 뒤 사람이 Tableau로 저장해도
> 재생성되지 않았고 경고도 없었다 (MA_011 260811 재저장 검증). "Tableau가 재계산한다"가
> 아니라 **없어도 되는 선택적 블록**이다 — 뷰 필드 구성을 바꿀 때 잔재를 남기지 않으려면
> 지우는 쪽이 낫다.

## 시트 이름 바꾸기 — 3곳 (레시피 09 확인)

`시트 1` → `관찰_주시트`는 `worksheet@name` · `window@name` · `thumbnail@name`
**3곳이 동시에** 바뀐다. 하나라도 빠지면 `named.refs`(규칙 ③)가 ERROR를 낸다.

## 노이즈

`title` strip `size` (29→28) · `saved-dpi-scale-factor` · `source-height` ·
`thumbnail` base64 · `simple-id` uuid 값

## 재저장 검증 · twb-lint

관찰 원본 그대로면 정규화 없음. `twb_validate` → `passed=true`, findings 0.
twb-lint: `shelf.refs`(⑪) · `calc.field_refs`(②) · `named.refs`(③).
