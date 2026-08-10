# 레시피 21 — CSV(텍스트 파일) 데이터 원본 연결

| 항목 | 값 |
|---|---|
| 판정 표면 | T1 · T2 |
| UI 경로 | 새 통합 문서 > 연결 > **텍스트 파일** > `.csv` 선택 (시트는 안 만듦) |
| 근거 | 2026-08-10 관찰 `관찰_A_빈워크북.twb` → `관찰_B_CSV연결만.twb` 대조 (소유자 조작, UI) |
| Tableau | 2026.1.1 |

레시피 [20](./20-empty-workbook.md)의 빈 워크북에 **데이터 원본 하나만** 붙인
통제 diff다. 그래서 "데이터 원본 연결이 더하는 것"이 정확히 갈린다.

## ① 매니페스트가 3항목 늘어난다

```xml
<document-format-change-manifest>
  <AnimationOnByDefault />
  <MarkAnimation />
  <ObjectModelEncapsulateLegacy />     <!-- 추가 -->
  <ObjectModelTableType />             <!-- 추가 -->
  <SchemaViewerObjectModel />          <!-- 추가 -->
  <SheetIdentifierTracking />
  <WindowsPersistSimpleIdentifiers />
</document-format-change-manifest>
```

**항목 이름은 알파벳 오름차순으로 삽입된다** (`_.fcp.` 접두 항목은 접두 없이 정렬).
이 3항목이 `<object-graph>`(아래 ⑤)를 게이팅하는 것으로 보이나, 셋이 한꺼번에
붙어서 **어느 것인지는 미분리**(`추정`).

## ② 데이터 원본 뼈대

```xml
<datasource caption='관찰_data' inline='true'
            name='federated.1l6p7750sw7alz1d1tbgb1y30jni' version='18.1'>
  <connection class='federated'>
    <named-connections>
      <named-connection caption='관찰_data' name='textscan.13kaf2i1o2hoau1fqrdng1m3qxwy'>
        <connection class='textscan' directory='C:/dev/새 폴더'
                    filename='관찰_data.csv' password='' server='' />
      </named-connection>
    </named-connections>
    <relation connection='textscan.13kaf2i1o2hoau1fqrdng1m3qxwy'
              name='관찰_data.csv' table='[관찰_data#csv]' type='table'>
      <columns character-set='UTF-8' header='yes' locale='ko_KR' separator=','>
        <column datatype='string'  name='지역'   ordinal='0' />
        <column datatype='string'  name='품목'   ordinal='1' />
        <column datatype='date'    name='기준월' ordinal='2' />
        <column datatype='integer' name='매출'   ordinal='3' />
        <column datatype='integer' name='수량'   ordinal='4' />
      </columns>
    </relation>
    <metadata-records>…③…</metadata-records>
  </connection>
  <aliases enabled='yes' />
  <column caption='관찰_data.csv' datatype='table'
          name='[__tableau_internal_object_id__].[관찰_data.csv_37303D40AADA432085591F517D3EF1AE]'
          role='measure' type='quantitative' />
  <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
  <semantic-values>
    <semantic-value key='[Country].[Name]' value='&quot;대한민국&quot;' />
  </semantic-values>
  <object-graph>…⑤…</object-graph>
</datasource>
```

| 자리 | 규칙 |
|---|---|
| `datasource@name` | `federated.` + 28자 소문자 영숫자. Tableau 발급 |
| `named-connection@name` | `textscan.` + 28자. 클래스 접두가 붙는다 |
| `relation@connection` | named-connection의 `name`과 **글자 그대로 일치** |
| `relation@table` | `[<파일명에서 확장자 앞 . 을 # 으로>]` — `관찰_data.csv` → `[관찰_data#csv]` |
| `relation@type` | 파일 연결은 `table` (사용자 지정 SQL은 `text`) |
| `connection@directory` | **절대 경로, 슬래시(`/`)**. 백슬래시 아님 |
| 객체 id | `<파일명>_<대문자 HEX 32자>` — 이 문자열이 ③⑤에 그대로 반복된다 |

## ③ metadata-records — capability 1개 + 컬럼 N개

첫 레코드는 `class='capability'`로 **연결 자체의 파싱 옵션**을 싣는다:

```xml
<metadata-record class='capability'>
  <remote-name /><remote-type>0</remote-type>
  <parent-name>[관찰_data.csv]</parent-name>
  <remote-alias /><aggregation>Count</aggregation><contains-null>true</contains-null>
  <attributes>
    <attribute datatype='string' name='character-set'>&quot;UTF-8&quot;</attribute>
    <attribute datatype='string' name='collation'>&quot;ko&quot;</attribute>
    <attribute datatype='string' name='currency'>&quot;₩&quot;</attribute>
    <attribute datatype='string' name='field-delimiter'>&quot;,&quot;</attribute>
    <attribute datatype='string' name='header-row'>&quot;true&quot;</attribute>
    <attribute datatype='string' name='locale'>&quot;ko_KR&quot;</attribute>
    <attribute datatype='string' name='single-char'>&quot;&quot;</attribute>
  </attributes>
</metadata-record>
```

컬럼 레코드는 **CSV 열 순서 그대로**(`ordinal` 0부터), 타입별로 자식이 다르다:

| local-type | remote-type | aggregation | 추가 자식 |
|---|---|---|---|
| `string` | 129 | `Count` | `<scale>1</scale>` `<width>1073741823</width>` `<collation flag='0' name='LKO_RKR' />` |
| `date` | 133 | `Year` | — |
| `integer` | 20 | `Sum` | — |

공통: `<remote-name>` `<local-name>[이름]</local-name>` `<parent-name>[파일명]</parent-name>`
`<remote-alias>` `<ordinal>` `<contains-null>true</contains-null>`
`<object-id>[<객체 id>]</object-id>`.
**`object-id`는 모든 컬럼 레코드가 같은 값**이다 (테이블 하나니까).

## ④ 테이블 객체를 가리키는 `<column>` 1개

```xml
<column caption='관찰_data.csv' datatype='table'
        name='[__tableau_internal_object_id__].[관찰_data.csv_37303D40AADA432085591F517D3EF1AE]'
        role='measure' type='quantitative' />
```

필드가 아니라 **테이블 자체**를 나타내는 내부 컬럼이다. 필드 정의(`<column>`)를
따로 쓰지 않아도 metadata-records에서 필드가 생긴다 — 이 시점엔 사용자 정의
필드가 없으므로 이 하나뿐이다.

## ⑤ `<object-graph>` — relation을 통째로 되풀이한다

```xml
<object-graph>
  <objects>
    <object caption='관찰_data.csv' id='관찰_data.csv_37303D40AADA432085591F517D3EF1AE'>
      <properties context=''>
        <relation connection='textscan.…' name='관찰_data.csv'
                  table='[관찰_data#csv]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='ko_KR' separator=','>
            … ②의 columns와 **글자 그대로 동일** …
          </columns>
        </relation>
      </properties>
    </object>
  </objects>
</object-graph>
```

**②의 `<relation>`과 중복이 아니라 사본이다.** 둘 다 있어야 한다.
추출을 쓰면 `<properties context='extract'>`가 한 벌 더 붙는다 (실파일 관찰).

## 함정 — `<object-graph>`를 빼면 **데이터 원본 탭에서 죽는다**

`<object-graph>` 없이 손저작한 파일은 **정상적으로 열리고 시트도 보이지만,
데이터 원본 탭을 클릭하는 순간 Tableau가 그대로 종료된다** (2026-08-10 분리 실험 V1).
로드 게이트를 통과하므로 층 1이 아니다 — "열리는데 앱이 죽는" 자리다.

실파일 상관: `relation`을 가진 데이터 원본 **113개 전부** `<object-graph>`를
갖는다 (반례 0). twb-lint 규칙 ⑭ `datasource.shape`가 **ERROR**로 잡는다.

`<columns>`는 다르다 — 빼도 데이터 원본 탭이 멀쩡했다(실험 V2). 상관은 39:0이지만
**증상이 없어 규칙화하지 않았다.** 정본 형태는 §②대로 쓰되, 없다고 파일이 깨지진 않는다.

매니페스트 3항목(`ObjectModelTableType`·`ObjectModelEncapsulateLegacy`·
`SchemaViewerObjectModel`)을 빼면 **로드 자체가 거부된다**(실험 V3, `D2E8DA72`) —
`no declaration found for element 'object-graph'`. 규칙 ⑥-b가 잡는다.

## 노이즈

`directory`의 절대 경로(파일을 옮기면 Tableau가 다시 쓴다) ·
`semantic-values`의 국가 추정 · 해시 id 값 자체

## 재저장 검증 · twb-lint

관찰 원본 그대로면 정규화 없음. `twb_validate` → `passed=true`, findings 0.
twb-lint: `datasource.shape`(⑭) `<object-graph>` 누락 · `manifest.gates`(⑥-b) 3항목.
