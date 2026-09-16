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

### F5-b. 2026-07-30 실측 — 게이트 3쌍 추가 확보 (MA_003 매출표)

사용자가 만든 `MA_003_경영관리-재무-매출표_JWH_260729.twb`가 로드 거부됐다 (D2E8DA72):

```
Error(750,97):  no declaration found for element 'edit-parameter-action'
Error(789,13):  element 'edit-parameter-action' is not allowed for content model
                '(action,datasources,datasource-dependencies*,edit-group-action)'
Error(1965,180): no declaration found for element 'computed-sort'
Error(1977,16): element 'computed-sort' is not allowed for content model
                '(datasources?,mapsources?,datasource-dependencies*,filter,sort,perspectives,slices?,aggregation)'
```

**twb-lint는 이 파일을 finding 0건으로 통과시켰다** — AC3 위반의 두 번째 실증.
분석 결과 원인은 XSD도 자식 순서도 아니다:

- 공식 XSD 2026.1.0은 두 요소를 **그 자리에서 허용한다**
  (`ParameterActions-G`가 `ActionList-ActionList-CT`에 · `Sort-ComputedSort-G`가 `Sort-G`에)
- `<actions>` 자식 순서도 정상본과 **완전히 동일**하다
  (`edit-group-action`×2 → `edit-parameter-action`×2 = 정상본 MA_002와 같다)
- 두 번째 거부 메시지의 content model이 F5의 `manual-sort` 사례와 **글자까지 같다** —
  게이트가 닫힌 상태의 좁은 문법이다

거부된 파일의 매니페스트 항목이 12개, 같은 기능을 쓰는 정상본은 22개였다.
차이 중 이 파일이 실제로 쓰는 기능:

| 없는 항목 | 파일이 쓰는 요소 | 거부 메시지 |
|---|---|---|
| `ParameterAction` | `<edit-parameter-action>` | 실측됨 |
| `ParameterActionClearSelection` | `<clear-option>` | 부모만 실측됨 |
| `SortTagCleanup` | `<computed-sort>` | 실측됨 |

실파일 61개(KPMG·디딤 템플릿 39 + 사내 개발본 22) 전수 상관으로 쌍조건을 확인했다:

| 요소 | 요소 있는 파일 | 항목 없는 예외 | 항목만 있고 요소 없는 파일 |
|---|---|---|---|
| `computed-sort` | 23 | 1 (거부된 그 파일) | 0 |
| `edit-parameter-action` | 28 | 1 (같은 파일) | 0 |
| `clear-option` | 28 | 1 (같은 파일) | 0 |

`clear-option`은 출현 72회 전부 부모가 `edit-parameter-action`이고, 부모가 있으면 항상
있었다 — 그래서 `ParameterActionClearSelection`을 부모가 아니라 `clear-option`에 걸었다.
매개변수 액션에 `clear-option`이 없는 파일에 거짓 ERROR를 내지 않기 위한 선택이다.

세 쌍을 `manifest_gates.json`에 넣은 뒤: 거부된 파일 = **ERROR 3건**(줄 750·773·1965,
Tableau가 지목한 줄과 일치) · 정상본 61개 = **ERROR 0건**(AC7 유지).

### F5-c. 게이트를 통과한 뒤 나온 두 번째 층 — 표기 규약 (같은 파일)

매니페스트를 고친 사본은 **로드된다.** 대신 경고가 두 개 나왔다:

```
'SEC07_상세 실적표' 오류: '측정값 이름' 필드의 필터를 구문 분석하는 동안
오류가 발생했습니다. 필터를 무시합니다.        (SEC06_추이도 같은 오류)

'SEC06_추이' 워크시트에 오류가 있습니다. 다음이 제거됩니다.
 — 이름이 '[Multiple Values]'인 필드가 없습니다.
```

**로드 거부와 성질이 다르다** — 파일은 열리고, Tableau가 **문제 있는 설정만 버린다.**
필터가 사라진 화면은 조용히 틀린 숫자를 보여준다. 정상본 대조로 둘 다 표기 문제였다:

| | 이 파일 | 정상본 | 정상본 실측 |
|---|---|---|---|
| `groupfilter@member` | `[ds].[usr:C_MTD_계획:qk]` | `"[ds].[usr:…:qk]"` | 감싼 것 714 · 안 감싼 것 0 |
| 자리표시자 | `[Multiple Values]` | `[federated.…].[Multiple Values]` | 22개 파일 235회, 전부 한정자 있음 |

`member`는 **값 자리**다 — 필드 참조를 값으로 쓸 때도 문자열 리터럴로 감싼다
(`member='true'`는 불리언, `member='"SAMT"'`는 문자열, 필드 참조도 마찬가지).

여기서 나온 규칙이 ⑦ `ref.notation`이다 (06 R14). **둘 다 WARNING** — S1-6에 따라
"열리지 않는다고 확신할 때만 ERROR"이고, 이 둘은 열린다.

**함의**: 매니페스트 게이트(F5)는 *로드 거부* 층이고, 표기 규약은 그 **뒤의 층**이다.
한 층을 고치면 다음 층이 드러난다 — 게이트가 두 층을 다 봐야 "열리고 제대로 뜬다"를 말할 수 있다.

### F5-d. 세 번째 층 — 수식 안 매개변수 참조 (같은 파일)

표기까지 고치니 대시보드는 뜨는데 **데이터가 하나도 안 나왔다.** `C_P_DATE` 계산필드가
오류 상태(`계산에 오류 있음`)이고 거기에 25개가 종속돼 있었다.

```
DATE(DATEPARSE('yyyyMM', STR([P_YEAR]) + RIGHT("0" + STR([P_MONTH]), 2)))     오류
DATE(DATEPARSE('yyyyMM', STR([Parameters].[P_YEAR]) + …))                     정상본
```

수식 안에서 매개변수를 참조할 때 Tableau는 **항상 `[Parameters].[<내부 이름>]`으로
한정한다.** 한정자가 없으면 그 데이터소스의 컬럼으로 해석되고, 없으니 계산이 깨진다.

실파일 61개: 한정된 참조 **3,377건** · 한정 없는 것은 이 파일뿐(36건, 매개변수 7종 전부).

**규칙 ②는 이것을 원리적으로 못 잡는다.** ②는 자격 없는 참조를 전 데이터소스 필드
합집합과 대조하므로(07 G5의 의도된 트레이드오프 — 좁히면 거짓 dangling이 난다)
`[P_YEAR]`가 `Parameters`에 있다는 이유로 **해소된 것으로 본다.** G5가 명시한
거짓음성의 대가가 여기서 실제로 물렸다. 그래서 ⑦-c는 ②를 고치는 대신 **표기 축**에서
따로 본다: "어느 데이터소스에 있는가"가 아니라 "한정자를 썼는가".

### F5-e. 네 번째 층 — 집계 정합과 집합 정의 (같은 파일)

매개변수까지 고치니 데이터는 나오는데 필드 두 개와 집합 두 개가 빨갛게 떴다.

**(1) 사용자 지정 집계로 올린 비집계 계산**

```
오류: 'C_L_전체' 계산에는 집계되지 않은 수식의 사용자 지정 집계가 필요합니다.
```

뷰가 `<column-instance derivation="User">`(= `usr:` 인스턴스, 마크의 "집계(…)")로
참조하는데 수식(`"전체"`)에 집계가 없다. 실측: 정상본의 `usr:` 인스턴스는 참조 체인을
끝까지 펼치면 **반드시** 집계 함수가 나온다(표본 20종, 반례 0).

**LOD(`{ FIXED … : MAX(…) }`)는 집계로 치지 않는다** — LOD만 참조하는
`C_L_세부현황`이 정확히 같은 오류로 거부됐다. LOD 결과는 행 수준 값처럼 쓰인다.

**(2) 기반 필드 없는 집합**

실파일 61개의 `<group>` 82개는 모양이 둘뿐이다:

```xml
<!-- 사용자 집합 -->
<group … user:ui-builder="filter-group">
  <groupfilter function="empty-level" member="[C_LV1_KEY]" …/>
</group>
<!-- 집합 액션이 만든 자동 집합 -->
<group … hidden="true" user:auto-column="sheet_link">
  <groupfilter function="crossjoin"><groupfilter function="level-members" level="[accs_nm]"/></groupfilter>
</group>
```

MA_003은 **제3의 모양**이었다 — `auto-column="sets"`인데 자식이 빈
`<groupfilter function="union"/>` 하나뿐이라 기반 필드가 어디에도 없다. 그래서
`… IN [C_LV1_KEY 집합]`을 쓰는 계산 3개가 전부 깨졌다.

규칙 ⑧ `calc.aggregation` · ⑨ `set.definition`이 여기서 나왔다. **둘 다 WARNING.**
⑨는 **모양을 열거하지 않고 기반 필드의 유무만 본다** — 모양은 릴리스마다 늘 수 있지만
"집합에는 기반 필드가 있다"는 성질은 바뀌지 않는다.

### F5-f. 저작해 보니 나온 층 — 한정자를 **붙여서** 틀리는 자리 (2026-07-31)

앞의 F5-b~F5-e는 전부 남이 만든 파일을 고치다 나왔다. F5-f는 다르다 —
`/author-loop`으로 **빈 손에서 워크북 하나를 만들어** 열어 본 것이 입력이다.
린터는 통과시켰고(0 findings) Tableau는 경고했다. AC3 위반.

```
동작을 완료할 수 없습니다.
'C:\dev\매출요약.twbx' 통합 문서를 로드하는 동안 경고가 발생했습니다.
'매출 추이' 오류:
필터링을 위해 포함된 '[federated.0d2m1o5x3q7k9w1e5r8t2y4u6i].[none:Calculation_1000000000000003:nk]'
필드가 없습니다.
```

내가 쓴 것과 정상본이 쓰는 것:

```xml
<!-- 내가 쓴 것 — 필터가 버려진다 -->
<filter class='categorical' column='[federated.abc].[none:C_등급:nk]'>
  <groupfilter function='member' level='[federated.abc].[none:C_등급:nk]' member='"고액"' />
</filter>

<!-- 정상본 3,484건 전부 -->
  <groupfilter function='member' level='[none:C_등급:nk]' member='"고액"' />
```

**실측 (실파일 85개 중 이 요소를 쓰는 31개): 비한정 3,484 : 한정 0.**
`level` 속성이 없는 묶음 노드(`function='union'` 등) 430건은 대상 밖이다.

**⑦-b와 방향이 반대다.** `[Multiple Values]`는 한정자를 **붙여야** 하고
`groupfilter@level`은 **떼어야** 한다. "한정자를 붙이면 안전하다"는 직관이
정확히 틀리는 자리이며, 저작(생성)에서만 밟는다 — 기존 파일을 편집할 때는
Tableau가 써 둔 표기를 그대로 두므로 이 층이 드러나지 않는다 (01 v2.0 §2).

더 강한 성질 — *"level은 `filter@column`의 기저 이름과 같다"* — 은 **실측이
부정했다**: `column='[ds].[Action (C_팀명)]'`에 `level='[팀명(복사본)_…]'`인 정상
사례가 있다. 그래서 규칙은 한정자 유무 하나만 본다.

규칙 ⑦-d가 여기서 나왔다. **WARNING** — 파일은 열린다.

### F5-g. 저작 3종을 열어 본 결과 — 검출률 1/8 (2026-07-31)

F5-f 이후 `/author-loop`으로 워크북 3개를 더 만들어 Tableau에서 열었다.
케이스를 겹치지 않게 나눴다 — **A** 매개변수 동작·LOD, **B** 집합·정렬·필터 동작,
**C** 데이터소스 2개·페이지 선반·참조선.

**셋 다 열렸다.** 층 1은 린터가 지켰다 — 저작 중 XSD가 6건을 막았다
(`<group>`을 워크시트 의존성에 배치 · `layout`의 없는 속성 2 · `label` 인코딩 ·
`manual-sort@direction` 누락 · `reference-line` 필수 속성 2).

그런데 **화면은 틀려 있었다.** 사용자가 Tableau에서 찾아낸 결함 7건을 각각 되돌려
넣고 린터를 다시 태운 결과:

| | 결함 | 층 | 린터 |
|---|---|---|---|
| ① | `groupfilter@level` 한정자 (F5-f) | 2 | ✅ `ref.notation` |
| ② | `<group>`에 `user:auto-column='sets'` | 2 | ❌ |
| ③ | 집합을 `<encodings><color>`에 배치 | 2 | ❌ |
| ④ | `command='tsc:filter'` — 관측되지 않은 명령 | 2 | ❌ → ✅ ⑬ (F5-h) |
| ⑤ | `param name='source-field'` — **자리가 틀린** param | 2 | ❌ → ✅ ⑬ (F5-h) |
| ⑥ | 필터 동작에 `<link expression>` 누락 | 2 | ❌ → ✅ ⑬ (F5-h) |
| ⑦ | 도구 설명에 행수준 차원 (집계 수준 불일치) | 4 | ❌ |
| ⑧ | `<pages>`에 `<current-page>` 누락 | 3 | ❌ |

**1/8.** 잡은 하나는 바로 앞 반복에서 규칙화한 ⑦-d다.

#### 대조 수치 (전부 반례 0)

| 축 | 정상본 | 저작본이 쓴 것 |
|---|---|---|
| `<group>` 속성 | `user:ui-builder='filter-group'` **46** | `user:auto-column='sets'` — **2건뿐이고 둘 다 MA_003(거부된 파일)** |
| 집합이 놓이는 자리 ⚠️ | `<filter>` **38** | `<encodings>` — **0** |
| 동작 `command` ⚠️ | `tsc:tsl-filter` **14** · `tsc:brush` **16** | `tsc:filter` — **0** |
| 동작 `param name` ⚠️ | `target` **30** · `exclude` **29** · `field-captions` **15** · `special-fields` 1 | `source-field` — **0** |
| 필터 동작의 필드 매핑 | `<link expression='tsl:…'>` — tsl-filter **14건 전부** | 없음 |
| `column-instance@derivation` | `None` 3487 · `User` 2412 · `Sum` 409 · `Min` 209 · `Month` 55 · `Count` 29 · `Year` 2 · `Month-Trunc` 1 | `Attribute` — **실파일 0건** |
| `<pages>` | **0회** | — |

#### 여기서 배운 것

**1. 필드 매핑이 param이 아니라 URL에 들어 있다.** 필터 동작의 원본↔대상 필드는
`<command>`의 자식이 아니라 `<link expression>`에 퍼센트 인코딩되어 실린다:

```
tsl:<대시보드>?<필드>~s0=&lt;<필드>~na&gt;
```

이걸 빼면 Tableau의 동작 대화상자에 항목은 뜨는데 **필드 열이 비고 편집 버튼이 죽는다.**
`target`도 시트가 아니라 **대시보드** 이름이고, `exclude`는 *필터를 적용하지 않을* 시트다.

**2. 기존 규칙이 왜 비켜갔는지가 규칙 설계의 근거다.**

| | 있는 규칙 | 왜 못 잡나 |
|---|---|---|
| ②③ | ⑨ `set.definition` | *"기반 필드가 있는가"*만 본다. 모양과 놓인 자리는 안 본다 |
| ④⑤⑥ | ⑩ `action.refs` | *"가리키는 대상이 실재하는가"*만 본다. **명령·param 이름 자체는 안 본다** — 오타든 없는 값이든 통과 |
| ⑦ | ⑫ `calc.types` | 미구현 |
| ⑧ | — | 표본 0. 규칙화 조건 미달 |

**3. `derivation='Attribute'`는 근거가 약하다.** 실파일 0건이고 XSD의 `AggType-ST`는
**제약 없는 문자열**이다. 접두사 규칙의 일관성(`Sum→sum:`·`Count→cnt:`·`Month→mn:`)과
Tableau UI의 `특성(담당자)` 표시만이 근거다. 규칙화하지 않는다.

후보 항목은 `docs/06-rule-candidates.md` **R20~R23**.

> ⚠️ 위 표의 동작 두 줄(`command`·`param name`)에는 **내 저작본이 섞여 있었다.**
> 정정된 수치는 F5-h에 있다. 결론(반례 0)은 바뀌지 않지만 `source-field`에 대한
> 판단은 **뒤집혔다** — "존재하지 않는 이름"이 아니라 "자리가 틀린 이름"이다.

### F5-h. `/defect-loop` D1 — 동작의 모양은 셋뿐이다 (2026-07-31, 규칙 ⑬)

F5-g의 결함 ④⑤⑥을 한 규칙으로 묶었다. 셋 다 **같은 층·같은 요소·같은 증상**이다 —
파일은 경고 없이 열리는데 동작 대화상자에서 편집이 막히고 동작이 발동하지 않는다.

#### 먼저 실측을 다시 했다

F5-g의 글롭 `C:\dev\*.twbx`가 **내가 만든 저작본을 정상본으로 셌다.** 갈라서 다시 센다
(실파일 63개 · 동작 140건, 저작본 제외):

| 종류 | 명령 | `<link>` | 건수 |
|---|---|---|---|
| `<action>` 필터 | `tsc:tsl-filter` | 있다 (`expression='tsl:…'`) | **14 : 0** |
| `<action>` 하이라이트 | `tsc:brush` | 없다 | **17 : 0** |
| `<action>` URL | 없다 | 있다 (`expression='http…'`) | **1** |
| `<edit-parameter-action>` | 없다 | 없다 | 75 |
| `<edit-group-action>` | 없다 | 없다 | 47 |
| `<nav-action>` | — | — | **0 — 표본 없음** |

`<action>`은 **세 모양뿐이고 명령과 `<link>`가 짝을 이룬다.** 저작본의
`tsc:filter` + `<link>` 없음은 셋 중 어디에도 없다.

param 이름은 **종류마다 어휘가 갈린다. 교차 0건:**

| 종류 | 관측된 param 이름 |
|---|---|
| `action` / `tsc:tsl-filter` | `target` 14 · `exclude` 14 |
| `action` / `tsc:brush` | `target` 17 · `exclude` 16 · `field-captions` 16 · `special-fields` 1 |
| `edit-parameter-action` | `target-parameter` 75 · `source-field` **70** |
| `edit-group-action` | `selection-clear-set-option` 47 · `target-group` 47 |

**F5-g가 틀렸던 지점이 여기다.** `source-field`는 없는 이름이 아니라 **70건 관측되는
정상 이름**이고, 저작본은 그걸 `<action>`에 붙였다. 전역 화이트리스트로는 못 잡는다 —
종류별로 갈라야 걸린다. 거짓양성 함정 테스트가 이 한 쌍을 고정한다.

#### XSD는 원리적으로 못 잡는다

```xml
<xs:simpleType name="ActionList-CommandName-ST">
  <xs:restriction base="xs:string"><xs:pattern value="[^:]+:[^:]+"/></xs:restriction>
</xs:simpleType>
```

**열거가 아니라 패턴이다.** `tsc:filter`도 `아무거나:아무거나`도 통과한다. `<param>`은
`name`·`value` 둘 다 `xs:string`이다. L-A가 볼 수 있는 것이 없다.

#### 규칙 ⑬ `action.shape` — ⑩과 무엇이 다른가

⑩ `action.refs`는 *가리키는 대상이 실재하는가*(**참조**), ⑬은 *Tableau가 아는 배선
모양인가*(**어휘**)를 본다. 저작본은 가리키는 시트·필드가 전부 실재해서 ⑩이 침묵했다.
그래서 ⑩ 확장이 아니라 **별도 규칙**으로 냈다 — 같은 id 아래 두면 "refs"가 아닌 것이
`action.refs`로 보고된다.

**전부 WARNING이다.** 목록이 좁아서다 — 명령 2종·param 8종이 표본의 전부고,
`<nav-action>`은 어휘 자체를 모른다(→ `note_partial`). 목록 밖은 *틀렸다*가 아니라
*모른다*이므로 ERROR가 될 수 없다 (02 S1-6). 규칙 ①(`calc.functions`)과 같은 구조다.
그리고 층 2다 — `tsc:filter`를 넣은 저작본을 Tableau가 **경고 없이** 열었다.

#### 회귀

- 실파일 63개 `action.shape` **0건** (AC7 유지, 총 ERROR 0)
- 결함 파일 `매출요약.twbx` 1건만 검출
- 주입 레시피 2건 추가 — `R22-unknown-action-command` · `R23-drop-filter-link`.
  둘 다 주입 전 baseline 0, 주입 후 검출
- 게이트 **285 passed** (골든셋) / 271 passed, 14 skipped (미설정)

### F5-i. `/defect-loop` D2 — 측정이 후보를 죽였다 (2026-07-31, 구현 없음)

R20의 두 축을 실측했다. **하나는 폐기했고 하나는 보류했다. 코드 변경은 없다.**

#### (b) 집합이 놓이는 자리 — **폐기. 표본 0이다**

F5-g의 `<filter> 38 : 인코딩 0`은 **두 종류의 집합을 한 칸에 세고 있었다.**
갈라서 다시 세면:

| | 건수 | 파일 | 뷰에 배치된 사례 |
|---|---|---|---|
| 사용자 집합 (`user:ui-builder='filter-group'`) | 46 | 22 | **0** |
| 동작이 만든 집합 (`user:auto-column`, `hidden='true'`) | 80 | 21 | 38 (`<filter>`) |

**38건은 전부 동작 집합이고, 2개 파일(19+19)에서만 나온다.** 동작이 만든 집합은
Tableau가 구조상 필터에 넣는다 — 사용자가 집합을 어디에 놓아도 되는지에 대해
이 38건은 **아무것도 말하지 않는다.**

그리고 사용자 집합 46개는 **뷰에 한 번도 배치되지 않았다.** 계산식
(`… IN [X 집합]`)에서만 참조된다. 배치에 대한 표본이 **0**이다.

`/defect-loop` 멈춤 조건에 걸린다 — *"정상본 표본이 0개다 → 규칙화하지 않는다."*
R24(`<pages>`)와 같은 자리다. 게다가 집합을 색상에 올려 IN/OUT으로 칠하는 것은
Tableau의 정규 기능이라, 38:0을 규칙으로 만들면 **정상 워크북을 때린다.**

#### (a) 집합의 모양 — **불변식은 섰는데 증상 귀속이 안 된다**

| `<group>` 속성 조합 | 건수 | 파일 |
|---|---|---|
| `caption` + `ui-builder` (hidden 없음) — 사용자 집합 | 46 | 22 |
| `caption` + `hidden='true'` + `auto-column='sheet_link'` | 60 | 21 |
| `hidden='true'` + `auto-column='exclude'` | 20 | 21 |
| `caption` + `auto-column='sets'` — **hidden 없음** | **2** | **1 (MA_003, 거부된 파일)** |

성질로 읽으면: **집합은 사용자 것이거나 시스템 것이다. 시스템 표식(`auto-column`)을
달았으면 숨겨진다(`hidden='true'`).** 실측 **80 : 2**, 반례 2건은 거부된 파일 하나뿐.
`<group>` 128개 중 `ui-builder`도 `auto-column`도 없는 것은 0개다.

**그런데 증상을 이 축에 귀속시킬 수 없다.** 관측된 세 사례가 전부 교락돼 있다:

| 파일 | `auto-column='sets'` | 집합을 인코딩에 | 증상 |
|---|---|---|---|
| MA_003 | ✅ | — | 집합에 **기반 필드도 없다** → 규칙 ⑨가 이미 잡는다 |
| 저작 B | ✅ | ✅ | 집합이 필터처럼 굴었다 — **둘을 한꺼번에 고쳤다** |
| 매출요약 | ✅ | ✅ | 열린다. 집합은 확인 안 됐다 |

저작 B에서 **한 반복에 두 층을 고친 것**이 지금 값을 치르게 한다. 어느 쪽이
증상을 냈는지 모르는 채로 규칙을 만들면 우리 추측을 남의 파일에 강제한다.

#### 분리 실험을 사용자에게 넘긴다

매출요약이 두 후보를 다 갖고 있고 이미 열려 있으므로 대조군이 된다. 하나씩만 되돌렸다:

| 변형 | 되돌린 것 | 유지한 것 |
|---|---|---|
| `매출요약_V1_속성만.twbx` | `auto-column='sets'` → `ui-builder='filter-group'` | 색상에 올린 집합 |
| `매출요약_V2_자리만.twbx` | 색상을 `[none:지역:nk]`로 | `auto-column='sets'` |

둘 다 ERROR 0 (남은 WARNING은 원본에도 있던 ⑬ 동작 결함 — 층을 섞지 않으려고 안 고쳤다).
결과가 오면 규칙화한다. **오기 전에는 하지 않는다.**

### F5 정리 — 실사용 파일이 낸 4층 + 저작이 낸 2층

| 층 | 증상 | 규칙 | 심각도 | 실측 근거 |
|---|---|---|---|---|
| 매니페스트 게이트 | 로드 거부 D2E8DA72 | ⑥-b | ERROR | 61개 상관, 반례 0 |
| 표기(필터·자리표시자) | 열리되 설정이 버려짐 | ⑦-a·⑦-b | WARNING | 714:0 · 235:0 |
| 표기(매개변수) | 열리되 데이터가 안 나옴 | ⑦-c | WARNING | 3,377:0 |
| 집계·집합 | 열리되 필드가 오류 상태 | ⑧·⑨ | WARNING | 20:0 · 82:0 |
| 표기(필터 level) | 열리되 필터가 버려짐 | **⑦-d** | WARNING | **3,484:0** (F5-f) |
| 동작 모양 | 열리되 동작이 안 먹음 | **⑬** | WARNING | 14:0 · 17:0 · 어휘 교차 0 (F5-h) |

**층은 순서대로만 보인다.** 앞 층을 고치기 전에는 뒤 층의 증상이 나타나지 않는다 —
Tableau가 첫 실패에서 멈추기 때문이다. 그래서 한 반복에 한 층만 고친다
(`/defect-loop`).

### F5-j. 저작본이 신기능 서식을 **맨 이름**으로 썼다 (2026-09-07, 규칙 ⑮)

MA_004 손익계산서 저작본. 린터 `passed=True · findings=0`, Tableau는 거부했다 — AC3 위반.

```
동작을 완료할 수 없습니다. … 오류 코드: D2E8DA72
Error(770,70): value 'corner-radius-top-left' not in enumeration
… 같은 메시지 88건 (모서리 4면 × 22개 존)
```

**F5의 다른 사례와 형태가 다르다.** 지금까지 게이트 위반은 전부
`no declaration found for element 'X'`였다 — 요소 자체를 모른다는 말이다. 이번은
요소(`format`)도 속성(`attr`)도 알지만 **값이 열거에 없다**고 한다. 같은 원인의 다른
얼굴이다: 매니페스트가 열거값을 게이팅한다. F5-e의 `relation@type='table'`
(`value 'table' not in enumeration`)과 같은 계열이다.

공식 XSD는 이 값을 **허용한다** — `twb_2026.1.0.xsd` 4688~4692행,
`StyleAttribute-ST`에 `corner-radius`와 4면이 전부 열거돼 있다. L-A가 통과시킨 이유다.

대조 (실파일 254개):

| 표기 | 건수 | 파일 수 |
|---|---|---|
| `<_.fcp.DashboardRoundedCorners.true...format attr='corner-radius…'>` | **11,033** | 252 |
| `<format attr='corner-radius…'>` | **88** | 1 (거부된 그 파일) |

**11,033 : 0.** 매니페스트 항목 `_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners`도
252/254가 갖고 있고 거부된 파일에는 없었다.

같은 방식으로 fcp 접두가 요구되는 표면을 전수로 셌다:

| 기능 | 표면 | fcp : 맨 |
|---|---|---|
| `DashboardRoundedCorners` | `zone-style` 안 `format[@attr^='corner-radius']` | **11,033 : 0** |
| `IndividualControlFormatting` | `style-rule[@element='parameter-ctrl']` 안 `format[@field]` | **468 : 0** |
| `VConnDownstreamExtractsWithWarnings` | `extract/@user-specific` (속성) | 256 |

대조군으로 `@field` 붙은 다른 서식도 셌다 — `cell` 11,555 · `label` 10,876 ·
`header` 2,636 · `axis` 1,291건이 **전부 맨 표기**다. 즉 "`@field`면 fcp"가 아니라
**기능별 표면**이다. `legend`만 맨 238 : fcp 21로 혼재라 규칙에서 뺐다.

**원인은 우리 문서였다.** `docs/recipes/15-zone-style.md`가 모서리 반경을 맨
`<format>`으로 적어 놨다 — fcp 정규화 **후**의 모양을 그대로 옮긴 것으로 보인다.
정규화가 접두사를 지운다는 F7 함의 2가 레시피 저작에서 재발한 셈이다.

**고침본 확인 (같은 날, 사용자 재저장)** — 접두사 88건 + 매니페스트 항목 1개만 고친
파일이 **열렸고**, Tableau가 재저장하며 우리 표기 87건을 무수정 수용했다(나머지 1개
존은 사용자가 "모든 모서리 동일" 버튼을 눌러 4면 4건 → 단수 `corner-radius` 1건으로
접혔다 — 두 표기 다 정본이다). 인과와 정본이 **양방향으로** 확정됐다.

같은 재저장에서 **다음 층이 드러났다**: `<members>` 14건이 사라졌다. 매개변수 column이
`source-field`와 리터럴 `<members>`를 **둘 다** 갖고 있었고, 코퍼스에서 그 둘은 배타적이다
(`source-field`+members 없음 1,067 · source-field 없음+members 776 · 둘 다 4). 층 2는
별도 반복으로 넘긴다.

→ 규칙 ⑮ `format.fcp_prefix` (ERROR). 주입 레시피 R28.
⑥과 방향이 반대다 — ⑥은 *"fcp를 썼는데 선언이 없다"*, ⑮는 *"fcp로 썼어야 하는데 안 썼다"*.
접두가 없으면 기능이 트리에 나타나지 않아 **⑥은 볼 대상 자체가 없다.**

### F5-k. 불리언 필터 member를 따옴표로 감쌌다 (2026-09-14, 규칙 ⑦-f)

같은 MA_004 손익계산서. F5-j의 층 1(로드 거부)을 고치고 나니 **파일은 열리는데**
경고가 떴다. 린터는 `passed=True · findings=0` — AC3 위반 두 번째다.

```
동작을 완료할 수 없습니다.
'…\MA_004_경영관리-재무-손익계산서_JWP.twb' 통합 문서를 로드하는 동안 경고가 발생했습니다.
'SEC06_01_영업이익 추이_A/R' 오류:
'F_CY' 필드의 필터를 구문 분석하는 동안 오류가 발생했습니다. 필터를 무시합니다.
'SEC04_03_워터폴' 오류:
'C_WF_여부' 필드의 필터를 구문 분석하는 동안 오류가 발생했습니다. 필터를 무시합니다.
'SEC04_02_세부 현황' 오류:
'C_레벨2' 필드의 필터를 구문 분석하는 동안 오류가 발생했습니다. 필터를 무시합니다.
'SEC04_01_손익 항목 리스트' 오류:
'C_레벨1' 필드의 필터를 구문 분석하는 동안 오류가 발생했습니다. 필터를 무시합니다.
```

**F5-c와 오류 문구가 같고 방향이 반대다.** F5-c는 따옴표를 *빼서* 필터가 버려졌고
(규칙 ⑦-a), 여기는 따옴표를 *씌워서* 버려졌다. 네 필드 전부 `datatype='boolean'`이다:

```xml
<column caption='C_레벨1' datatype='boolean' name='[Calculation_9100000000000013]'
        role='dimension' type='nominal'>…</column>
…
<groupfilter function='member' level='[none:Calculation_9100000000000013:nk]'
             member='&quot;true&quot;' />        <!-- 감쌌다 = 결함 -->
```

**어느 쪽이 맞는지는 `level`이 가리키는 컬럼의 `datatype`이 정한다.** ⑦-a는
*"member가 필드 참조면 감싼다"*만 알았고, member가 **값**일 때의 표기는 보지 않았다
— 그래서 `member='true'`도 `member='"true"'`도 똑같이 통과시켰다.

대조 (실파일 138개, `groupfilter@member` 14,931건을 `level` 컬럼의 `datatype`으로 갈랐다):

| `level` 컬럼 datatype | member 표기 | 건수 |
|---|---|---|
| `boolean` | 맨값 (`true`) | **5,923** |
| `boolean` | 따옴표 (`"true"`) | **0** |
| `string` | 따옴표 (`"영업현금흐름"`) | **5,569** |
| `string` | 맨값 | **0** |
| (컬럼 미해소 — `[:Measure Names]` 등) | 따옴표 | 3,436 |

**5,923 : 0.** 양방향 다 반례 0이다. 깨진 파일에서는 `boolean`+따옴표가 **정확히 4건**
나왔고, 그 4건이 오류 문구의 4개 필드(`C_레벨1`·`C_레벨2`·`C_WF_여부`·`F_CY`)와
**1:1로 맞는다** — 귀속이 셀 수준에서 확정됐다.

**문자열 쪽(맨값)은 규칙에 넣지 않았다.** 코퍼스 수치는 같은 방향이지만 그 모양이
실제로 어떤 증상을 내는지 관측하지 못했다. 이번 파일이 낸 것은 불리언 4건뿐이다 —
측정 없이 넓히면 그 자리가 통째로 거짓양성 위험이 된다 (02 S1-6).

**WARNING이다.** 파일이 열리므로 ERROR가 아니다(층 2). 다만 조용하지 않다 —
`C_레벨1 = true`로 걸러져야 할 행이 그대로 남아 **틀린 숫자의 표가 배포된다.**

→ 규칙 ⑦-f (WARNING). 주입 레시피 R29. 신규 rule id 없음 — ⑦-a와 **같은 속성의
반대 방향**이라 ⑦의 여섯째 표면으로 넣었다(⑦-e를 ⑦에 넣은 것과 같은 기준).
`level`의 컬럼을 못 찾거나 동명 필드의 `datatype`이 데이터소스마다 갈리면 판정하지
않고 `note_partial`로 보고한다.

### F5-l. 계산필드 **구조 문법** — 정상본이 표본을 줄 수 없는 첫 규칙 (2026-09-14, 규칙 ⑯)

사용자 질문에서 출발했다: *"twb_validate 말고 계산필드 문법에 대한 lint도 만들 수 있어?"*
결함 파일이 아니라 **역량 질문**이 입력이라 `/defect-loop`과 순서가 반대다 — 증상을
먼저 잡는 대신 **재료가 있는지를 먼저 쟀다.**

`03` D3.7이 이 자리를 예고해 뒀다:

> 인자 개수·타입 검사처럼 구문 트리가 필요한 검증은 이 수집기로 못 한다. …
> 필요해지면 그때 스캐너 **위에** 파서를 얹는다 — 스캐너를 지울 이유는 없다.

실측 결과 **파서는 필요 없었다.** 구조 문법은 구문 트리가 아니라 *짝이 맞는가*이고,
그것은 스캐너의 토큰 열에 카운터를 얹으면 나온다.

대조 (실파일 138개, 수식 **85,316건** = `calculation@formula` + `groupfilter@expression`):

| 검사 | 정상본 위반 |
|---|---|
| `(` `)` 균형 | **0** |
| LOD `{` `}` 균형 | **0** |
| `IF`·`CASE` ↔ `END` 짝 | **0** |
| `THEN` 없는 `IF` | **0** |
| `WHEN` 없는 `CASE` | **0** |
| `IF`·`CASE` 없는 고아 `THEN` | **0** |

**0건이 "검사가 아무것도 안 한다"는 뜻일 수 있어 반대쪽도 쟀다** — 일부러 깨뜨린 8종
전부 검출, 거짓양성 함정 4종(문자열 속 `END`, 주석 속 `(`, `ELSEIF`, LOD 콤마) 전부 침묵.
주석·문자열·필드 참조가 토큰 우선순위에서 먼저 먹히는 것이 그 침묵의 이유다.

**이 규칙은 근거의 절반을 코퍼스에서 얻을 수 없다.** Tableau 편집기를 통과한 수식만
저장되므로 **정상본에 문법 오류는 원리적으로 없다.** `/defect-loop`의 평소 방법
(불변식 N : 반례 0)이 AC7 쪽만 채우고 검출 가치는 비운다 — 그 절반은 주입 레시피
R30이 만든다.

이것은 결함이 아니라 **01 v2.0의 명제 그대로**다: *위험은 편집이 아니라 생성에 있다.*
수식을 손으로 쓰는 것은 `/author-loop`뿐이라, 이 규칙의 고객은 남의 파일이 아니라
우리 저작본이다.

**부수 실측 — 인자 개수 표를 코퍼스에서 벌 수 있다.** 화이트리스트 JSON에는 이름만
있고 서명이 없는데, 145,000여 회의 호출을 함수별로 세니 **39종 중 38종이 인자 개수
단일 고정**이었다 (`DATEADD` 3개:11,637 · `DATEPARSE` 2개:10,181 · `SUM` 1개:12,039 …).
유일한 변동은 `MIN` — 1개(집계)와 2개(행수준) 두 형태이고 **둘 다 Tableau 정본**이다.
다만 218종 중 39종만 관측되므로 나머지 179종은 판정 불가(`note_partial`)다.
**구현하지 않았다** — 커버리지 39/218에서 오는 침묵이 규칙의 값어치를 정하는데,
그 판단을 먼저 받아야 한다.

→ 규칙 ⑯ `calc.syntax` (WARNING). 주입 레시피 R30.
**신규 rule id다** — ①(`calc.functions`)은 *"그 이름의 함수가 있는가"*를 묻고 ⑯은
*"문법이 성립하는가"*를 묻는다. ⑬을 ⑩에서 가른 기준과 같다(⑦-e·⑦-f를 ⑦에 접은 것은
질문이 같아서였다).

### F5-m. 집계 ↔ 행수준 혼합 — "0건"의 뜻을 뒤집었다 (2026-09-14, 규칙 ⑧-c)

사용자 지적에서 나왔다: *"AI가 잘못 잡는 게 집계·차원에 대한 문법인 것 같아.
IF절이면 차원이면 결과도 차원, 조건식이 집계면 결과도 집계여야 되는데."*

Tableau가 거부하는 그 자리다:

```
SUM([매출]) + [수량]                        집계 + 행수준
IF SUM([A]) > 0 THEN [B] ELSE 0 END        조건은 집계, 분기는 행수준
```

    오류: 집계 및 비집계 인수를 이 함수와 함께 혼합할 수 없습니다.

**`TODO.md`가 이 후보에 경고를 달아 뒀었다** — *"시제품 실측이 실파일에서 혼합
0건을 냈다. 잡을 게 없는 규칙을 만들기 전에 …"*. 그 수치는 맞았고 **읽기가 틀렸다.**

정상 워크북은 Tableau 편집기를 통과했으므로 혼합이 **있을 수 없다.** 0건은 규칙이
무용하다는 뜻이 아니라 **AC7 근거**다 — F5-l(규칙 ⑯)에서 같은 구조를 이미 봤다.
검출 근거는 코퍼스가 아니라 주입 레시피와 우리 저작본에서 온다 (01 v2.0).

검사 성질 — **집계 함수의 인자 안도 아니고 LOD 중괄호 안도 아닌 자리**에서 집계
호출과 행수준 참조가 동시에 나오면 혼합이다. 가리는 자리가 둘인 것이 요점이다:

| 수식 | 판정 | 왜 |
|---|---|---|
| `SUM([A]) + [B]` | 혼합 | `[B]`가 집계 밖 |
| `SUM([A] + [B])` | 정상 | 둘 다 집계 인자 안 |
| `SUM([A]) + SUM([B])` | 정상 | 바깥에 맨 참조 없음 |
| `{FIXED [a] : SUM([b])} + [c]` | 정상 | LOD 결과는 행수준 값이다 (⑧-a와 같은 판단) |
| `MIN([A], [B])` | 정상 | **2인자 `MIN`은 행수준 함수** |

대조 (실파일 138개 · 수식 85,316건): **혼합 0건.**

**첫 시제품은 21건을 오탐했다.** 전부 MA_006 `F_PERIOD` 계열이었고 원인은
`MIN(DATE(…), {MAX(…)})` — 2인자 `MIN`을 집계로 읽은 것이다. 인자 수로 성격이
갈리는 함수가 실재한다는 것이 F5-l의 인자수 실측(`MIN` 1개:4,849 · 2개:49)에서
이미 나와 있었는데, 그 사실을 이 검사에 옮기지 않아서 생긴 오탐이다.
**인자 수를 보게 고치니 21 → 0.**

⚠️ 부수로 **자기 프로브의 결함을 두 번 고쳤다.** ① 토큰 정규식의 문자 클래스에
쉼표가 빠져 인자 수가 항상 0으로 세졌다(그래서 모든 `MIN`이 집계로 분류됐다).
② 중첩 호출이 바깥 프레임의 "내용 있음"을 표시하지 않아 `YEAR(TODAY())` 같은 수식이
0인자로 세졌다. 둘 다 **실측 수치를 먼저 의심해서** 잡혔다 — `YEAR` 0인자 5,161건은
있을 수 없는 값이다. 수치가 이상하면 코퍼스가 아니라 도구를 먼저 본다.

→ 규칙 **⑧-c** (WARNING). 주입 레시피 R31.
**신규 rule id 없음** — ⑧-a·⑧-b와 입력은 다르지만(수식만 본다 vs 수식×`derivation`)
묻는 것이 같다: *집계 수준이 맞는가*. `calc.types`(⑫)는 이것을 떼고 나면 **순수
타입 정합**(문자열↔숫자·`IF` 분기 반환형)만 남는다 — 그쪽은 아직 증상이 없다.

### F5-n. `paramctrl` 존에 `mode`가 없다 — 내부 오류 CB5AF9D4 (2026-09-14, 규칙 ⑰)

같은 MA_004. F5-k(필터 member)를 고친 판은 **열렸고**, 그 위에 대시보드를 채운 판이
안 열린다. 린터는 `passed=True · findings=0` — AC3 위반 세 번째다.

```
동작을 완료할 수 없습니다.
내부 오류 - 예기치 않은 오류가 발생하여 작업을 완료할 수 없습니다.
오류 코드: CB5AF9D4
```

**원인 탐색이 이전과 달랐다.** 거부 메시지가 요소를 지목하지 않는다(D2E8DA72와 달리
`no declaration found for element`가 없다). 그래서 **"정상본에 0번 나오는 모양"을
전수로 훑었다** — 요소 · (요소, 속성) · (부모, 자식) · (요소, 속성, 값) 네 축이다.

첫 수확은 둘 다 **오답이었다**:

| 후보 | 대조 | 왜 아니었나 |
|---|---|---|
| `<windows saved-dpi-scale-factor='1.25'>` | 238 : 0 | XSD `Window-WindowsAttributes-AG`에 정식 선언. 화면 배율 125%의 흔적일 뿐 |
| 매개변수의 `source-field` + `<members>` 공존 | 1,138 : 0 | 배타 자체는 사실인데 **열렸던 판에도 있었다** |

**"열렸던 판"과의 차분이 둘을 죽였다.** 파일이 열렸다는 사실이 라벨이므로, 그 판에
이미 있던 것은 원인일 수 없다. 정상본 대조만으로는 이 둘을 못 걸러낸다 — 코퍼스에
없다고 해서 결함인 것은 아니다(우리 코퍼스가 100% 배율에서만 저장됐을 뿐이다).

⚠️ **F5-j의 "`source-field`+members 둘 다 4건"은 반례가 아니었다.** 그 4건은 바로 이
MA_004 자신의 **워크시트 내 사본**이다(매개변수 2개 × 사본 2). `<datasource
name='Parameters'>`의 직속 자식만 세면 정상본 1,138건 중 공존은 **0건**이다.
집계 단위를 잘못 잡아 자기 결함을 코퍼스에 섞어 넣은 것이다.

**진짜 원인은 속성 조합이었다.** (요소, 속성) 존재만 보는 축으로는 안 잡힌다 —
`zone`도 `mode`도 각각은 코퍼스에 흔하다. **종류별 속성 키 조합**을 세자 나왔다:

| | `paramctrl` 존 | `mode` 없는 것 |
|---|---|---|
| 정상본 238개 | **2,475** | **0** |
| 열렸던 11:08 판 | 0 | 0 |
| 안 열리는 14:29 판 | 6 | **6** |

`mode`는 컨트롤 위젯 종류다 — `compact` 2,473 · `type_in` 2. 없으면 Tableau가 그릴
컨트롤을 정하지 못한다. 존 6개가 들어온 판에서만 오류가 났으므로 **귀속이 판 단위로
확정됐다.**

**XSD는 못 잡는다.** `mode`는 zone의 **선택** 속성으로 선언돼 있어 L-A가 통과시킨다.
F5의 매니페스트 게이팅과는 또 다른 경로의 "XSD 통과 ≠ 열린다"다 — 이번엔 게이트가
아니라 **로더의 런타임 요구사항**이다.

→ 규칙 ⑰ `zone.shape`. 주입 레시피 R32.
**신규 rule id다** — ③(`named.refs`)은 *존이 가리키는 이름이 실재하는가*, ⑰은
*그 종류의 존이 갖춰야 할 것을 갖췄는가*. ⑬을 ⑩에서 가른 기준과 같다.

### ❌ 고침본 확인 실패 — `mode`는 원인이 아니었다 (같은 날)

`mode` 6건을 채운 고침본을 사용자가 열었더니 **CB5AF9D4가 그대로 났다.**
2,475 : 0은 사실이지만 **상관이지 인과가 아니다.**

**규칙 ⑰을 ERROR → WARNING으로 내렸다.** 이 저장소의 기준은 *"파일이 안 열린다고
확신할 때만 ERROR"*이고, ⑭가 ERROR인 근거는 *"인과가 실험으로 확정됐고 상관만이
아니다"*였다. ⑰에는 그 확정이 없다. 확인 전에 ERROR로 커밋한 것이 절차 위반이었다
(`/defect-loop` §3: *"사용자가 확인해 주기 전에는 규칙화하지 않는다"*).

남은 값어치는 **저작 쪽**이다 — `/author-loop`이 paramctrl 존을 손으로 쓸 때
정상본과 같은 모양으로 쓰게 한다. 정상본 238개에서 finding 0건이라 게이트를
시끄럽게 하지도 않는다.

**이 반복에서 배운 것**: 정상본 대조로 나온 *"N : 0"*은 **후보**를 만들 뿐이고,
고침본이 열려야 **원인**이 된다. 이번 탐색에서 N:0 후보가 셋 나왔는데
(`saved-dpi-scale-factor` 238:0 · `source-field`+members 1,138:0 · `mode` 2,475:0)
**셋 다 원인이 아니었다.** 앞의 둘은 "열렸던 판과의 차분"이 죽였고, 셋째는 고침본이
죽였다. 두 관문을 다 통과해야 인과다.

### CB5AF9D4 — 원인 미확정, 분리 실험으로 넘긴다

남은 차분 네 덩어리 중 하나에 있다:

| | 덩어리 | 변형 |
|---|---|---|
| A | `<actions>` + `edit-parameter-action` | `V1_no_actions` |
| B | 워크시트 존 16개 배치 (+viewpoint·zoom·layout-cache) | — (B 단독 검증은 V4) |
| C | `paramctrl` 존 6개 | `V2_no_paramctrl` |
| D | 워크시트 `<layout-options><title>` 10개 | `V3_no_layout_options` |

`V4_only_sheets`는 A·C·D를 한꺼번에 빼 **B 단독으로도 깨지는가**를 가른다.
기하 불변식은 후보에서 **탈락했다** — 정상본에서도 `layout-flow` 자식 크기 합이
5,584·3,336건 어긋난다(238/238 파일). 존 트리의 부모-자식 종류 조합에서 0건짜리가
셋 나왔지만 조합 희소성이라 단독으로는 약하다.

### F5-o. 동적 존 표시 = `<datagraph>` — 게이트 3쌍 추가 (2026-09-16, 규칙 ⑥)

사용자 저작본 `MA_004_…_JWLH_260916.twbx`가 로드 거부됐다. 린터는
`passed=True · findings=0`(WARNING 1건은 기준선) — AC3 위반이다.

```
오류 코드: D2E8DA72
Error(18998,14): no declaration found for element 'datagraph'
Error(19234,12): element 'datagraph' is not allowed for content model
  '(document-format-change-manifest,repository-location?,preferences,style-theme?,
    style,local-data?,datasources?,datasource-relationships?,mapsources?,
    shared-views?,actions?,worksheets?,dashboards?,windows?,thumbnails?,external?)'
```

**F5의 정본 패턴이다** — 거부 메시지가 요소를 직접 지목한다. 06 §D.1이 예고한
*"로드 거부 메시지가 대응 요소를 직접 알려준다"*가 또 한 번 그대로 작동했다.

**`<datagraph>`는 동적 존 표시(Dynamic Zone Visibility)의 저장 형식이다.** 사용자의
말이 이 귀속을 확정했다 — *"내가 표시 유형 제어를 요구했는데 datagraph를 썼네"*.
AI가 엉뚱한 기능을 쓴 것이 아니라 그 기능의 직렬화가 이 모양이다. 내용이 그대로 말한다:

```xml
<datagraph><graph>
  <nodes>
    <single-value-field-node fieldname="[…].[Calculation_72…072]" …/>
    <dashboard-zone-visibility-node dashboard-identifier="{9E8D…}" zone-id="…" …/>
  </nodes>
  <edges>…</edges>
</graph></datagraph>
```

필드 값 노드 → 존 가시성 노드로 이어지는 그래프다. 06 **R8**이 *"`<datagraph>`
(동적 존 표시) 삽입 [보류]"*로 적어 둔 항목이고, 여기서 표본이 생겼다.

대조 (실파일 243개):

| | datagraph 보유 15개 | 미보유 228개 |
|---|---|---|
| `DatagraphCoreV1` | **15** | **0** |
| `DatagraphNodeSingleValueFieldV1` | **15** | **0** |
| `DatagraphNodeDashboardZoneVisibilityV1` | **15** | **0** |
| `ZoneVisibilityControl` | **15** | **0** |

**양방향 반례 0.** 깨진 파일에는 넷 다 없다.

⚠️ **네 항목이 완전히 동시출현해 코퍼스로는 분리되지 않는다** — `simple-id`와 같은
상황이고, 거기서 *"둘 다 요구"*가 과요구로 드러난 전례가 있다 (F5의 2026-08-10 실험).
그래서 **뭉뚱그리지 않고 이름이 대응하는 요소에만** 걸었다:

| 요소 | 요구 항목 |
|---|---|
| `<datagraph>` | `DatagraphCoreV1` |
| `<single-value-field-node>` | `DatagraphNodeSingleValueFieldV1` |
| `<dashboard-zone-visibility-node>` | `DatagraphNodeDashboardZoneVisibilityV1` |

`DatagraphNode<X>V1` ↔ `<x-node>`라는 이름 대응이 이례적으로 명확해서 가능했다.
거부 메시지가 실측으로 지목한 것은 `datagraph` 하나뿐이고, 나머지 둘은 **이름 대응 +
15:0 상관**이다 — 그 사실을 `manifest_gates.json`의 `source`에 적어 뒀다.

**`ZoneVisibilityControl`은 표에 넣지 않았다.** 같은 15:0으로 붙어 다니지만 대응이
요소가 아니라 **속성**(`zone@hidden-by-user`, 정상본 15:0)이고 이 표는 요소 단위다.
`known_items_unmapped`에 넣어 `note_partial`로 보고한다 (11 → 12종). 속성 게이트가
필요해지면 그때 스키마를 넓힌다 — 지금 넓히면 근거 없는 자리가 늘어난다.

⚠️ **골든셋 라벨이 오염됐다.** 이 깨진 파일이 `MA_004_경영관리-재무-손익계산서/`
안에 있어서 `CLAUDE.md`의 골든셋 glob(`MA_00*/*.twbx`)이 **정상본으로 집어 든다.**
게이트를 돌리면 AC7 테스트가 이 파일로 깨진다 — 규칙이 틀린 것이 아니라 라벨이 틀린
것이다. 그 폴더의 나머지 5개는 전부 ERROR 0이다.

→ 규칙 ⑥ 게이트 3쌍 추가 (**ERROR**). 주입 레시피 R33.
`known_items_unmapped` 11 → 12종 (Datagraph 3종은 애초에 목록에 없었고 —
표본 10개에 datagraph 파일이 없었다 — `ZoneVisibilityControl`이 새로 들어왔다).

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
