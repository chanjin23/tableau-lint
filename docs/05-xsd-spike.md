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

### F5 정리 — 실사용 파일이 낸 4층 + 저작이 낸 1층

| 층 | 증상 | 규칙 | 심각도 | 실측 근거 |
|---|---|---|---|---|
| 매니페스트 게이트 | 로드 거부 D2E8DA72 | ⑥-b | ERROR | 61개 상관, 반례 0 |
| 표기(필터·자리표시자) | 열리되 설정이 버려짐 | ⑦-a·⑦-b | WARNING | 714:0 · 235:0 |
| 표기(매개변수) | 열리되 데이터가 안 나옴 | ⑦-c | WARNING | 3,377:0 |
| 집계·집합 | 열리되 필드가 오류 상태 | ⑧·⑨ | WARNING | 20:0 · 82:0 |
| 표기(필터 level) | 열리되 필터가 버려짐 | **⑦-d** | WARNING | **3,484:0** (F5-f) |

**층은 순서대로만 보인다.** 앞 층을 고치기 전에는 뒤 층의 증상이 나타나지 않는다 —
Tableau가 첫 실패에서 멈추기 때문이다. 그래서 한 반복에 한 층만 고친다
(`/defect-loop`).

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
