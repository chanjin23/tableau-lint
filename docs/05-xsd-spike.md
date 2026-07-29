# Tableau 저작 AI — XSD 스파이크 실측 (Spike Report)

> SOR 문서. 설계 [`03-design.md`](./03-design.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 완료 |
| 버전 | v1.2 (2026-07-29) |
| 소유자 | ax3didim@gmail.com |
| 목적 | 구현 착수 전 최대 리스크(L-A 실효성) 검증 |
| 결과 | **XSD 노선 유효. 단 전처리 3단계가 전제.** |
| v1.1 변경 | **F7 신설** — fcp 접두사 ↔ 매니페스트 대응 실측 (규칙 ⑥의 절반이 표 없이 풀린다) |
| v1.2 변경 | **F8 신설** — L-A 오류의 심각도는 오류코드만으로 못 가른다 (거짓양성과 진짜 오류가 같은 코드) |

---

## 왜 이 스파이크를 했나

설계 전체가 *"(A) 구문 검증은 공식 XSD로 해결됨"* 이라는 가정 위에 있었다. 검증된 적 없었다.
반대 위험 — 공식 XSD가 **정상 파일을 거부**하면, mandatory gate가 멀쩡한 산출물을 전부 막고
프로젝트 목적이 소멸한다. 가장 크고 가장 싸게 확인 가능한 리스크라 최우선으로 돌렸다.

## 표본

실사용 워크북 9개 (전부 Tableau에서 정상 작동 중인 파일).

| 출처 | 개수 | `source-build` | `.twb` 크기 |
|---|---|---|---|
| `MA_002_경영관리-재무-현금흐름` | 7 | 2026.1.1 | 799~851KB |
| `MA_004_경영관리-재무-손익계산서` | 1 | 2026.1.1 | 1151KB |
| `태블로판차분석_제약_260616` | 1 | 2026.1.0 | 1281KB |

전부 `version='18.1'` · `original-version='18.1'` · `source-platform='win'`.
`.twbx` 구조는 `.twb` + `.hyper`(1~4개) 단순 ZIP.

## 결과 요약

```
공식 XSD 그대로              → XSD 컴파일 자체 실패
  + import 스텁 2개          → 컴파일 OK, 파일당 오류 49~56건
  + fcp 접두사 정규화        → 파일당 1건
  + explain-data 선택화      → 0건 — 9/9 전부 통과
```

**결론: L-A는 성립한다. 단 "공식 XSD를 lxml에 넣으면 끝"이 아니다.**

---

## F1. 공식 XSD가 그대로는 컴파일되지 않는다

```xml
<xs:import namespace="http://www.tableausoftware.com/xml/user"/>      <!-- schemaLocation 없음 -->
<xs:import namespace="http://www.w3.org/XML/1998/namespace"/>          <!-- schemaLocation 없음 -->
```

두 import 모두 위치를 주지 않으면서, 스키마 본문은 그 안의 컴포넌트를 참조한다:

- `user:UserAttributes-AG` — 3곳에서 참조(L2774·L3211·L3280), 정의 없음
- `xml:base` — 참조, 정의 없음

libxml2(lxml)는 미해결 참조로 컴파일을 거부한다:

```
XMLSchemaParseError: attributeGroup, attribute 'ref': The QName value
'{http://www.tableausoftware.com/xml/user}UserAttributes-AG' does not resolve to
a(n) attribute group definition., line 2774
```

**해법**: 스텁 스키마 2개를 vendoring에 포함하고 import에 `schemaLocation`을 주입한다.

- `user` 네임스페이스 → `<xs:attributeGroup name="UserAttributes-AG">` + `<xs:anyAttribute processContents="skip"/>`
- `xml` 네임스페이스 → `lang`/`space`/`base`/`id` 4개 속성 선언

2026_1·2026_2 둘 다 동일 증상, 동일 해법.

## F2. `_.fcp.` 접두사 — 오류의 98%

Tableau의 하위호환 장치. 신기능 요소를 이렇게 직렬화한다:

```xml
<_.fcp.DashboardRoundedCorners.true...format />
<extract _.fcp.VConnDownstreamExtractsWithWarnings.true...user-specific='...' />
```

패턴: `_.fcp.<기능명>.<true|false>...<원래이름>`. 구버전 Tableau는 모르는 이름이라 건너뛰고,
지원 버전만 해석한다. **공식 XSD는 이 규칙을 전혀 모델링하지 않는다.**
→ 최신 기능을 쓴 워크북은 예외 없이 실패한다.

파일별 실측:

| 파일군 | fcp 오류 | 정규화 대상(요소+속성) |
|---|---|---|
| MA_002 (7개) | 48~49 | 53~54 |
| MA_004 | 55 | 60 |
| 태블로판차분석 | 52 | 57 |

**해법**: 검증 직전 트리 사본에서 접두사를 벗긴다 (원본 트리는 불변).

```python
FCP = re.compile(r'^_\.fcp\.[^.]+\.(?:true|false)\.\.\.')
```

요소 태그와 속성 키 양쪽에 적용해야 한다 (속성에도 나타남 — F2 예시 2행).

## F3. XSD가 실제 Tableau보다 엄격하다 — `explain-data`

```xml
<xs:group name="Workbook-ExplainData-G">
  <xs:sequence>
    <xs:element name="explain-data">     <!-- minOccurs 없음 = 필수 -->
```

실제 Tableau는 해당 기능을 안 쓰면 이 요소를 아예 쓰지 않는다. 표본 9개 전부 없다.
스키마가 요구 → 파일당 1건의 거짓 오류.

```
Element 'workbook': Missing child element(s).
Expected is one of ( external, referenced-extensions, explain-data ).
```

**해법**: vendored XSD에 `minOccurs="0"` 패치.

**함의**: "vendored XSD는 원본 그대로"라는 전제가 깨진다. 패치를 코드로 관리하고
(패치 목록 + 적용 스크립트), 상류 갱신 시 재적용·재검증하는 구조가 필요하다.

## F4. `<workbook version>`은 저작 버전이 아니다

```xml
<workbook original-version='18.1'
          source-build='2026.1.1 (20261.26.0410.0924)'
          version='18.1'>
```

Tableau Desktop **2026.1**이 만든 파일인데 `version`은 **18.1**이다.
이 값은 *"이 버전 이상의 Tableau면 열 수 있다"* 는 **최소 호환 버전**이며,
`<document-format-change-manifest>`에 나열된 사용 기능들로부터 역산된다.

공식 XSD 레포 README는 `version='26.1'`을 전제로 매핑을 설명하지만
(README의 예시는 `<ManifestByVersion />`를 쓴 직접 저작 케이스),
**Tableau가 실제로 저장한 파일은 이 규약을 따르지 않는다.**

기존 설계의 매핑은 실사용 파일에서 절대 적중하지 않는다:

```python
XSD_BY_VERSION = {"26.1": ..., "26.2": ...}   # 실제 파일은 "18.1"
```

**해법**: XSD 선택은 `source-build`(= 2026.1.1 → 2026_1)를 1순위 키로 쓴다.
`version`/`original-version`은 호환성 정보 및 F5의 로더 문법 판정에 쓴다.

보조 관측: 2026_1과 2026_2 XSD로 각각 검증한 결과가 동일했다 — 스키마 선택이 극단적으로
민감하지는 않다. 다만 결정론(S1-5)을 위해 선택 규칙 자체는 고정해야 한다.

## F5. 로더 문법 ≠ XSD 문법 — 매니페스트가 문법을 게이팅한다

과거 작업 기록(`old/generate-report`, 2026-07-03 경영_002, 함정 W2)의 실측:

> 공식 XSD(2026_1)에 있는 `<manual-sort>`로 썼더니 로드 거부 —
> `no declaration found for element 'manual-sort' ... content model
> '(datasources?,mapsources?,datasource-dependencies*,filter,sort,perspectives,slices?,aggregation)'`
> 로더는 파일의 `version='18.1'` 선언에 맞는 **레거시 문법**으로 검증한다.

그런데 이번 표본 9개는 **`version='18.1'`이면서 `<manual-sort>`를 쓰고 정상 로드된다** (파일당 11회 출현).
모순처럼 보이지만 매니페스트를 보면 풀린다:

```
<document-format-change-manifest>
  ... AccessibleZoneTabOrder, GroupAction, GroupActionAddRemove,
      ParameterAction, SetMembershipControl, SortTagCleanup, ...
```

**`SortTagCleanup`** — 이 항목이 있으면 캐노니컬 `<manual-sort>`가 유효하고, 없으면 레거시
`<sort class='manual'>`만 유효하다. 같은 계열 실측이 인터랙션 함정 I7에도 있다:

> `edit-group-action`은 매니페스트에 `<GroupAction />`·`<GroupActionAddRemove />`가 없으면
> `no declaration found for element` 로드 거부. **매니페스트 항목 추가 자체는 무해**(I1 격리 실험).

즉 통합 규칙:

> **유효 문법 = `version` 선언 × `document-format-change-manifest` 항목 집합.**
> 기능을 쓰면서 대응 매니페스트 항목을 선언하지 않으면 `no declaration found for element`로 로드 거부된다.

**이것은 XSD가 원리적으로 잡을 수 없는 실패 클래스다.** 공식 XSD는 `manual-sort`를 무조건 허용하므로,
매니페스트 없이 `manual-sort`를 쓴 파일은 **L-A를 통과하고 Tableau에서 열리지 않는다** — AC3(무거짓통과)
위반의 실증 사례. L-B에 규칙으로 편입해야 한다 (→ [`06-rule-candidates.md`](./06-rule-candidates.md) R1).

표본 간 차이도 이 규칙을 뒷받침한다 — 집합 액션을 쓰지 않는 260616 파일에는
`GroupAction`/`GroupActionAddRemove`가 없다 (22개 vs 20개). 매니페스트는 **실제 사용 기능만** 나열한다.

## F6. 부수 관측 — Tableau 설치본에 로더의 실제 XSD가 들어 있다

`C:\Program Files\Tableau\Tableau 2026.1\bin\res\tablangres.rcc` (26MB, Qt 리소스)에
XSD가 **압축 없이** 들어 있다.

```
xs:schema   32개 블록      complexType  9474회      .xsd  59회
```

과거 작업 기록(함정 I1)도 이를 "역수확 소스로 유용"하다고 적고 있다.
GitHub 공개 XSD보다 **설치된 로더가 실제로 쓰는 문법**에 가까울 가능성이 높다.
F1(결함)·F3(과엄격)·F5(매니페스트 게이팅)의 정답이 여기 있을 수 있다.

이번 스파이크 범위 밖으로 두되, **후속 조사 가치가 높다** (→ 03-design D8).

## F7. fcp 접두사가 매니페스트 대응표의 절반을 공짜로 준다 (2026-07-29 실측)

F5로 규칙 ⑥이 생겼지만 대응표가 **2쌍**뿐이라 검출력이 사실상 없었다.
전수 목록의 출처는 D8(설치본 `.rcc` 역수확, 26MB)뿐이고 비쌌다.

가설을 하나 세웠다 — F2의 fcp 기능명(`DashboardRoundedCorners`)과 F5의 매니페스트
항목명(`SortTagCleanup`)이 **같은 이름 체계로 보인다.** 둘을 나란히 놓고 대조한 적이 없었다.

### 실측 (표본 10개 = 정상 9 + `태블로판차분석…연습` 1)

매니페스트 항목 중 3개가 이렇게 생겼다:

```xml
<document-format-change-manifest>
  <_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners />
  <_.fcp.IndividualControlFormatting.true...IndividualControlFormatting />
  <_.fcp.VConnDownstreamExtractsWithWarnings.true...VConnDownstreamExtractsWithWarnings />
  <SortTagCleanup />  <GroupAction />  ...
```

**매니페스트 항목 이름 자체에도 fcp 접두사가 붙는다.** 접두사를 벗기면 트리의 fcp
기능명 집합과 **10/10 파일에서 완전 일치**(예외 0):

| | 트리의 fcp 기능명 | 매니페스트 fcp 항목 |
|---|---|---|
| 1 | `DashboardRoundedCorners` | 동일 |
| 2 | `IndividualControlFormatting` | 동일 |
| 3 | `VConnDownstreamExtractsWithWarnings` | 동일 |

### 함의 1 — fcp 계열은 대응표가 필요 없다

규칙이 데이터가 아니라 **구조에서 도출된다**:

> 트리에 `_.fcp.<F>.<true|false>...<이름>`이 있으면
> 매니페스트에 `_.fcp.<F>.true...<F>`가 있어야 한다.

기능명이 이름 안에 박혀 있으므로 조회표 없이 자기 자신에서 나온다.
→ 규칙 ⑥을 **⑥-a(fcp, 표 없음)** 와 **⑥-b(일반, 표 필요)** 로 쪼갠다.

### 함의 2 — 구현 순서 제약 (중요)

**fcp 정규화(F2)가 이 정보를 지운다.** 정규화 후에는

```
요소      _.fcp.DashboardRoundedCorners.true...format  →  format          (소속 기능 소실)
매니페스트 _.fcp.DashboardRoundedCorners.true...Dash…  →  DashboardRoundedCorners
```

요소 쪽에서 "어느 기능에 속하는지"가 사라져 대조가 불가능해진다.
→ **규칙 ⑥-a는 정규화 전 원본 트리에서 돌아야 한다.** L-A(정규화 후 사본)와 입력이 다르다.

### 함의 3 — 항목 이름 전수 확보 (2종 → 22종)

```
fcp 계열 3 : DashboardRoundedCorners · IndividualControlFormatting ·
             VConnDownstreamExtractsWithWarnings
일반 19    : AccessibleZoneTabOrder · AnimationOnByDefault ·
             AutoCreateAndUpdateDSDPhoneLayouts · GroupAction · GroupActionAddRemove ·
             MarkAnimation · ObjectModelEncapsulateLegacy · ObjectModelExtractV2 ·
             ObjectModelTableType · ParameterAction · ParameterActionClearSelection ·
             ParameterDefaultValues · SchemaViewerObjectModel · SetMembershipControl ·
             SheetIdentifierTracking · SortTagCleanup · WindowsPersistSimpleIdentifiers ·
             WorksheetBackgroundTransparency · ZoneBackgroundTransparency
```

일반 19종은 **이름이 요소명과 다르다**(`manual-sort` → `SortTagCleanup`) → 여전히 표가 필요하다.
아는 것은 2쌍뿐. 나머지 확보 경로는 아래 "다음 실험".

부수 확인: 판차분석 2개만 20종(`GroupAction`·`GroupActionAddRemove` 없음).
F5의 *"매니페스트는 실제 사용 기능만 나열한다"* 와 일치.

### 한계 — 인과는 아직 미검증

표본 10개가 **전부 동일했다**(fcp 3종, 분산 0). 관찰한 것은 *"fcp 요소를 쓰는 파일엔
fcp 매니페스트 항목도 있다"* 는 **동반 출현**뿐이다.
*"항목을 지우면 로드 거부되는가"* 는 확인하지 않았다. 그건 실험이 필요하다.

### 다음 실험 (로컬 Tableau Desktop 2026.1 수동 라벨링)

| | 내용 | 얻는 것 |
|---|---|---|
| **A** | `_.fcp.DashboardRoundedCorners…` 항목만 삭제 → 열어본다 (파일 1개) | 규칙 ⑥-a의 인과 확정 |
| **B** | 일반 19종을 하나씩 삭제한 파일을 만들어 열어본다 | 거부 메시지가 `no declaration found for element '<요소>'`로 **대응 요소를 직접 알려준다** → 2쌍 → 최대 20쌍 |

B가 성립하면 **Tableau가 대응표를 스스로 불러준다.** D8(`.rcc` 역수확)보다 싸다.
쓰지 않는 기능의 항목을 지우면 무반응이며, 그 무반응도 정보다(그 파일이 해당 기능 미사용).

### 재현

```python
FCP = re.compile(r"^_\.fcp\.([^.]+)\.(?:true|false)\.\.\.")
# 트리: 요소 태그 + 속성 키에서 group(1) 수집  →  fcp_features
# 매니페스트: root.find(".//document-format-change-manifest") 자식 태그에서 동일 수집
# 대조: fcp_features == {FCP 접두사 벗긴 매니페스트 항목}   → 10/10 True
```

## F8. L-A 오류의 심각도는 오류코드만으로 못 가른다 (2026-07-29 실측)

F3이 남긴 문제 — `explain-data`가 "XSD가 실제보다 엄격"의 실증이라면, **표본으로 못 걸른
과엄격이 더 있을 때 전부 ERROR로 내면 AC7이 무너진다.** 등급표가 필요했다.

lxml `error_log`의 `type_name`으로 가르려 했고, 주입 실험으로 유형별 값을 찍었다:

| 주입 | `type_name` | 코드 |
|---|---|---|
| `param-domain-type='all'` (R7) | `SCHEMAV_CVC_ENUMERATION_VALID` | 1840 |
| `width='abc'` | `SCHEMAV_CVC_DATATYPE_VALID_1_2_1` | 1824 |
| 미지 요소 추가 | `SCHEMAV_ELEMENT_CONTENT` | 1871 |
| ds 자식 순서 위반 (R4) | `SCHEMAV_ELEMENT_CONTENT` | 1871 |
| **`explain-data` 미패치 (거짓양성)** | **`SCHEMAV_ELEMENT_CONTENT`** | **1871** |

**거짓양성과 진짜 로드 거부가 같은 코드다.**

```
Element 'column': This element is not expected. ...        ← R4, 실제 로드 거부
Element 'workbook': Missing child element(s). ...           ← explain-data, 거짓양성
```

가르는 것은 **메시지 본문**뿐이다. libxml2 메시지는 영어로 고정돼 있어 매칭이 성립한다.

→ 정책: `not expected` = ERROR · `Missing child element` = WARNING · 미분류 = WARNING.
값 위반(enum·datatype)은 코드만으로 ERROR. 상세는 [`03-design.md`](./03-design.md) D3.

검증: 주입 고장본에서 R4·R7 모두 ERROR로 등급이 매겨지고, 정상본 9개는 오류 0건이다.

## 재현 방법

```python
# 1) vendored XSD 준비: import 2개에 schemaLocation 주입 + explain-data minOccurs=0
# 2) 검증
FCP = re.compile(r'^_\.fcp\.[^.]+\.(?:true|false)\.\.\.')
doc = etree.parse(twb_path)
for el in doc.iter():
    if not isinstance(el.tag, str):
        continue
    el.tag = FCP.sub('', el.tag)
    for k in list(el.attrib):
        nk = FCP.sub('', k)
        if nk != k:
            el.attrib[nk] = el.attrib.pop(k)
xsd.validate(doc)   # 표본 9/9 True
```

## 이 스파이크가 바꾼 것

| 문서 | 변경 |
|---|---|
| 01 §7 | XSD 실효성 = 조사 결과 → **실측 결과**로 승격. 결함 3종 기록 |
| 01 §8 | "XSD 통과 = (A) 해결"이 아님. 로더 문법 게이팅(F5)을 시맨틱 실패 유형에 추가 |
| 02 S4 | AC7(거짓양성 0) 신설 — F2가 FP 위험을 실측으로 입증 |
| 03 D3 | L-A에 전처리 3단계 명문화, 버전 선택 키를 `source-build`로 변경 |
| 03 D3 | L-B에 매니페스트 일관성 규칙 추가 |
| 03 D3 (v1.2) | **F7** — 규칙 ⑥을 ⑥-a(fcp, 표 없음)·⑥-b(일반, 표 필요)로 분리. ⑥-a는 정규화 **전** 트리를 입력으로 받아야 한다 |
| 03 D8 (v1.2) | **F7** — `.rcc` 역수확의 대상이 22종 전체에서 **일반 19종의 요소 매핑**으로 좁아졌다. 실험 B가 성공하면 불필요할 수도 |
