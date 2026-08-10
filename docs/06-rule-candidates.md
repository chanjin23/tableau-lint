# Tableau 저작 AI — 규칙 후보 인벤토리 (Rule Candidates)

> SOR 문서. 설계 [`03-design.md`](./03-design.md), 스파이크 [`05-xsd-spike.md`](./05-xsd-spike.md),
> 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | 🔄 living doc (규칙 확정·구현 시 갱신) |
| 버전 | v1.0 (2026-07-28) |
| 소유자 | ax3didim@gmail.com |
| 출처 | `old/generate-report` 함정 문서 + `05-xsd-spike.md` 실측 |

---

## 왜 이 문서가 있나

`old/generate-report`에 **실제로 Tableau가 파일을 거부한 사례**가 함정 문서로 축적돼 있다
(1단계 A/B/C/D · 2단계 S/C/W/X · 3단계 I 계열). 골든셋 고장 파일은 아직 없지만,
**"무엇이 파일을 못 열게 만드는가"의 실측 목록**은 이미 존재한다.

이 문서는 그 자산을 twb-lint 규칙 후보로 번역한다. 각 항목은:

- **원천** — 어느 함정에서 왔나 (추적 가능해야 라벨 신뢰성이 산다)
- **계층** — L-A(XSD가 잡음) / L-B(시맨틱, 우리가 만들어야 함) / 정적 불가
- **심각도** — [`02-specification.md`](./02-specification.md) S1-6 원칙에 따른 배정
- **상태** — MVP / 2차 / 보류

### 심각도 배정 원칙 (S1-6 재확인)

> **파일이 열리지 않는다고 확신할 때만 ERROR. 우리 지식의 공백은 WARNING.**

과거 파이프라인도 같은 결론에 독립적으로 도달했다:

> lint Tier 승격 원칙: **사람 완성본 twbx에서 오탐 0인 검사만 Tier A**
> — `TABLEAU-PIPELINE-ARCHITECTURE.md:217`

---

## A. 로드 거부/크래시 — ERROR 후보

### R1. 매니페스트 미선언 기능 사용 [L-B · MVP]

- **증상**: `no declaration found for element '<요소>'` + content model 나열 → 로드 거부
- **조건**: `<document-format-change-manifest>`에 대응 기능 항목 없이 그 기능의 요소를 사용
- **왜 중요한가**: **XSD가 원리적으로 못 잡는다.** 공식 XSD는 `manual-sort`를 무조건 허용하므로
  이 파일은 **L-A를 통과하고 Tableau에서 안 열린다** → AC3(무거짓통과) 위반의 실증 사례
- **비고**: 과거 lint는 W2를 WARN으로 격하했다 —
  *"수제 생성본만 로드 거부되고 Tableau 저장본은 정상이라 게이트 불가"*.
  게이팅 조건(매니페스트 항목)을 몰랐기 때문이다. **조건을 알면 ERROR로 정밀화할 수 있다** —
  twb-lint가 기존 자산보다 나아지는 첫 지점

**2026-07-29 실측([`05-xsd-spike.md`](./05-xsd-spike.md) F7)으로 두 갈래로 쪼개진다.**

#### R1-a. fcp 계열 — 대응표 불필요 [MVP · 지금 구현 가능]

매니페스트 항목 이름 **자체에도 fcp 접두사가 붙는다.** 접두사를 벗기면 트리의 fcp
기능명과 10/10 파일에서 완전 일치한다.

```xml
<_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners />   <!-- 매니페스트 -->
<_.fcp.DashboardRoundedCorners.true...format />                     <!-- 사용 요소 -->
```

- **규칙**: `_.fcp.<F>....`를 쓰면 매니페스트에 `_.fcp.<F>.true...<F>`가 있어야 한다
- **표가 필요 없다** — 기능명이 이름 안에 박혀 있어 자기 자신에서 도출된다
- ⚠️ **입력은 정규화 전 원본 트리.** fcp 정규화가 요소의 소속 기능을 지운다 (F7 함의 2)
- **심각도**: 인과 확정(실험 A) 전까지 WARNING. 확정되면 ERROR (S1-6)

#### R1-b. 일반 계열 — 대응표 필요 [MVP · 표 5쌍]

이름이 요소명과 다르다 → 표로만 풀린다.

- **실측 쌍**: `<manual-sort>` ↔ `SortTagCleanup` (함정 W2 / F5),
  `<edit-group-action>` ↔ `GroupAction` + `GroupActionAddRemove` (함정 I7),
  `<computed-sort>` ↔ `SortTagCleanup`,
  `<edit-parameter-action>` ↔ `ParameterAction`,
  `<clear-option>` ↔ `ParameterActionClearSelection` (뒤 3쌍은 05 F5-b, 2026-07-30 실측)
- **항목 이름 19종은 확보됨**(F7 함의 3) — 모르는 것은 **각 항목 ↔ 어느 요소**인가
- **구현**: `data/manifest_gates.json` 대조
- **한계**: 표에 있는 기능만 ERROR, 나머지는 검사 안 함(침묵).
  표에 없는 요소를 추측해서 ERROR 내지 않는다
- **확장 경로**: 실험 B(§D) → 실패 시 D8(`.rcc` 역수확)

### R2. 대시보드 시트 배치 ↔ window viewpoint 불일치 [L-B · MVP = rule ③]

- **증상**: XML은 well-formed인데 열자마자 **내부 오류 2805CF18**
  로그: `logic-assert: m_windowDoc->HasVisualDoc(doc->GetLocator())`
- **조건**: 대시보드에 worksheet 존을 배치했는데 대시보드 window의 `<viewpoints>`에
  해당 `<viewpoint name='시트명'>`이 없음. 또는 worksheet window 자체가 없음
- **원천**: 함정 S1 (2026-07-03 경영_002) — 과거 파이프라인에서 **게이트로 승격된 검사**
- **구현**: `dashboards/*/zones[@name]` ↔ `windows/window[@class='dashboard']/viewpoints/viewpoint[@name]`
  ↔ `windows/window[@class='worksheet'][@name]` 3자 대조
- **상태**: rule ③(named 참조 무결성)의 **가장 구체적인 실측 케이스**. 이걸로 rule ③을 정의한다

### R3. worksheet 존 참조 ↔ `<worksheets>` 정의 불일치 [L-B · MVP = rule ③]

- **조건**: 대시보드 존의 `name`이 `<worksheets>`에 없는 시트를 가리킴(dangling),
  또는 정의됐는데 어디서도 안 쓰이는 고아 시트
- **원천**: `verify_stage2.ps1`의 "워크시트 참조 무결성 — 1:1, 고아 시트 0개"
- **심각도**: dangling = ERROR / 고아 = WARNING (고아는 열리기는 한다)

### R4. datasource 자식 요소 순서 위반 [L-A · XSD가 잡음]

- **증상**: `element 'column' is not allowed for content model '(repository-location?,connection?,…)'`
  → 로드 거부 (D2E8DA72)
- **정답 순서**: `connection` → `column`들 → `column-instance` → `extract?` → `layout?` → `style` → `semantic-values?`
- **원천**: 함정 W1 — 과거 파이프라인에서 게이트로 승격
- **비고**: **L-A가 자동으로 커버한다**(XSD sequence). 별도 L-B 규칙 불필요 —
  단 05-xsd-spike의 전처리 3단계가 적용된 뒤에야 그렇다

### R5. `<actions>` 자식 순서 위반 [L-A · XSD가 잡음]

- **조건**: `edit-group-action`이 `edit-parameter-action`보다 뒤 → `element … is not allowed` 거부
- **원천**: 함정 I7. R4와 같은 계열(content model sequence) → L-A 커버

### R6. `<group>` 위치 위반 [L-A · XSD가 잡음]

- **조건**: 마지막 `column-instance` 직후·`<layout>` 앞이 아니면 거부. `<style>` 직전이면 `not allowed`
- **원천**: 함정 I7. L-A 커버

### R7. 속성 enum 위반 [L-A · XSD가 잡음]

- **실측**: `param-domain-type='all'` → `value 'all' not in enumeration` → 로드 거부 (D2E8DA72).
  정답은 `'any'`. 생략하면 매개변수 미인식(Null)
- **원천**: 함정 B10 (2026-07-08 경영_002)
- **비고**: *"PowerShell `[xml]` 파싱·자체 검증은 전부 통과했는데도"* 거부됐다 —
  well-formed ≠ 스키마 유효의 교과서적 사례. **L-A의 존재 이유**

### R8. `<datagraph>` (동적 존 표시) 삽입 [보류]

- **증상**: `std::out_of_range: invalid unordered_map<K,T> key` → 로드 거부
- **원천**: 함정 I1 — 6가지 변형 전부 실패, **미해결**
- **상태**: 정답 직렬화가 미확인이라 규칙화 불가.
  "수제 `<datagraph>` 존재 = WARNING(위험 영역)" 정도가 한계

---

## B. 열리지만 잘못 렌더 — WARNING 후보

### R9. 색상 팔레트 게이팅 3요소 누락 [L-B · 2차]

- **증상**: ds `<style>`에 색상 `<map>` 버킷이 있는데 **로드 시 조용히 무시**됨
- **조건(gating trio)**: `<connection>` 안 `<metadata-records>` + `<aliases enabled='yes'/>`
  + ds 레벨 `<column-instance>` 3개가 모두 있어야 적용
- **원천**: 함정 S3 → `lint_stage2.ps1` L6 (Tier A = 오탐 0 확인)
- **비고**: **기존 lint에 오탐 사례가 있다** — `[:Measure Names]`는 column-instance가
  존재할 수 없는 특수 필드라 L6이 오탐(함정 S9). twb-lint 구현 시 특수 필드 예외 필수

### R10. worksheet 존 `show-title='false'` 누락 [L-B · 2차]

- **증상**: 시트 제목이 표 위에 중복 표시
- **원천**: 함정 S2 → `lint_stage2.ps1` L5 (Tier A)

### R11. 죽은 매개변수 [L-B · 2차]

- **조건**: 루트 Parameters ds에 정의됐으나 run/calc/action 어디서도 참조 안 됨
- **원천**: `lint_stage3.ps1` L3-1
- **보정 이력**: `param-domain-type='any'` + paramctrl 조합은 **참조로 인정**해야 한다
  (입력 위젯 자체가 화면 요소) — 함정 I4에서 오탐 발견 후 보정

### R12. 입력 매개변수 이중 표시 [L-B · 2차]

- **조건**: `param-domain-type='any'` 매개변수가 텍스트 run 참조와 paramctrl을 **동시에** 가짐
- **증상**: 같은 값이 큰 글씨 + 입력 박스로 두 번 렌더
- **원천**: 함정 I4 → `lint_stage3.ps1` L3-2

### R13. manual sort 사전 미등재 라벨 [L-B · 2차]

- **조건**: 동적 라벨 계산식(▼/▶ 등)을 쓰면서 `<sort class='manual'>` dictionary에
  두 상태 라벨을 모두 bucket으로 등재하지 않음
- **증상**: 사전에 없는 라벨의 행이 **제자리에서 사라짐**(목록 밖으로 밀림, 로드는 성공)
- **원천**: 함정 I7

### R14. 참조 표기 규약 위반 [L-B · **구현됨 = rule ⑦**]

필드가 **존재하는데도** 표기가 그 자리의 규약과 달라 Tableau가 설정을 버리는 클래스다.
규칙 ②(필드 참조 해소)와 묻는 것이 다르다 — ②는 "가리키는 필드가 있는가",
⑦은 "그 자리에 쓸 수 있는 표기인가".

- **R14-a `groupfilter@member` 따옴표 누락**
  - **증상**: *"'측정값 이름' 필드의 필터를 구문 분석하는 동안 오류가 발생했습니다.
    필터를 무시합니다."* — 로드는 성공, **필터만 사라진다**
  - **조건**: `member` 값이 `[ds].[field]` 형태인데 따옴표로 감싸이지 않음.
    `member`는 값 자리라 필드 참조도 문자열 리터럴로 쓴다
  - **실측**: 실파일 61개에서 감싼 것 714건 · 안 감싼 것은 거부된 파일 1개(14건), 반례 0
- **R14-b `[Multiple Values]` 한정자 누락**
  - **증상**: *"이름이 '[Multiple Values]'인 필드가 없습니다"* → 그 필드가
    **워크시트에서 제거된다**
  - **조건**: `text@column`·`<rows>`·`<cols>`에 데이터소스 한정자 없이 `[Multiple Values]`
  - **실측**: 정상본 22개에서 235회, **전부** `[federated.…].[Multiple Values]`
  - ⚠️ 규칙 ②는 이 이름을 특수 자리표시자로 **제외한다**(옳다 — 필드가 아니다).
    빠진 것이 한정자 유무이고 그것이 ⑦-b다. 제외를 지우면 ②가 정상본 235곳을 뱉는다
- **R14-c 수식 안 매개변수 참조의 한정자 누락**
  - **증상**: 계산필드가 `계산에 오류 있음` 상태 → 종속 시트가 **데이터를 못 낸다**
  - **조건**: 수식이 `[P_YEAR]`처럼 참조. 정답은 `[Parameters].[P_YEAR]`
  - **실측**: 한정된 참조 3,377건 · 한정 없는 것은 거부된 파일뿐(36건, 매개변수 7종 전부)
  - ⚠️ **규칙 ②가 원리적으로 못 잡는다** — ②는 자격 없는 참조를 전 데이터소스 합집합과
    대조하므로(07 G5) 매개변수 이름이 `Parameters`에 있다는 이유로 해소로 본다.
    G5가 명시한 거짓음성의 대가가 여기서 물렸다
  - 이름이 데이터 컬럼에도 있으면 **보고하지 않는다** — 매개변수를 가리킨다고 단정 못 한다
- **심각도**: 셋 다 **WARNING** — 파일은 열린다 (02 S1-6). 단 화면은 조용히 틀린다
- **원천**: 2026-07-30 MA_003 매출표 실측 (05 F5-c · F5-d)

### R15. 사용자 지정 집계(`usr:`)로 올린 비집계 계산 [L-B · **구현됨 = rule ⑧**]

- **증상**: *"'C_L_전체' 계산에는 집계되지 않은 수식의 사용자 지정 집계가 필요합니다"*
  → 파일은 열리되 그 필드가 빨갛게 뜨고 **시트가 비어 나온다**
- **조건**: `<column-instance derivation="User">`가 가리키는 계산의 참조 체인에 집계가 없음
- **실측**: 정상본의 `usr:` 인스턴스는 체인을 펼치면 반드시 집계가 나온다(20종, 반례 0)
- ⚠️ **LOD는 집계로 치지 않는다** — LOD만 참조한 `C_L_세부현황`이 같은 오류로 거부됐다
- **판정 불가와 위반을 가른다**: 참조를 못 펼쳤으면 `note_partial`. 집계 함수 목록이
  불완전하면 거짓양성이 나는 구조라 공백을 위반으로 읽지 않는다
- **원천**: 2026-07-30 실측 (05 F5-e)

### R16. 기반 필드 없는 집합 [L-B · **구현됨 = rule ⑨**]

- **증상**: `… IN [X 집합]`을 쓰는 계산이 **전부** 오류 상태
- **조건**: `<group>` 안 어디에도 기반 필드(`member`·`level`·`column`)가 없음
- **실측**: 실파일 61개의 `<group>` 82개 전부가 기반 필드를 갖는다 (반례 0)
- **모양이 아니라 성질을 본다**: 사용자 집합(`ui-builder="filter-group"` + `empty-level`)과
  자동 집합(`hidden` + 중첩 `level-members`) 둘 다 통과시키되, 기반 필드가 없으면 잡는다.
  속성 이름을 열거하면 새 모양이 나올 때마다 거짓양성이 난다
- **원천**: 2026-07-30 실측 (05 F5-e)

### R17. 동작(`<actions>`) 배선 끊김 [L-B · **구현됨 = rule ⑩**]

- **증상**: 파일은 열린다. 그 동작이 발동하지 않거나, 대상 필드·집합이 오류 상태가 된다
- **왜 XSD가 못 잡나**: 배선의 절반이 `<param name= value= />`에 실리는데 XSD에서
  이 둘은 **임의 문자열 쌍**이다. 없는 `target-parameter`를 넣어도 L-A는 통과한다
- **표면 9종** (실측 2026-07-31, 실파일 84개 중 `<actions>` 보유 33개):

  | 표면 | 대조 대상 | 해소 : 미해소 |
  |---|---|---|
  | `source@worksheet` | 워크시트 | 81 : 0 |
  | `source@dashboard` | 대시보드 | 153 : 0 |
  | `source@datasource` | 데이터소스(이름 ∪ caption) | 4 : 0 |
  | `exclude-sheet@name` | 시트 ∪ 대시보드 | 3,016 : 0 |
  | `param exclude` (콤마 목록) | 시트 ∪ 대시보드 | 979 : 0 |
  | `param target` | 시트 ∪ 대시보드 | 30 : 0 |
  | `param target-group` | 집합 이름 ∪ 필드 | 46 : 0 |
  | `param target-parameter` 한정자 | `[Parameters].` | 83 : 0 |
  | `param target-parameter` 대상 | Parameters의 필드 | 77 : **6** |
  | `param source-field` | 전 데이터소스 필드 | 75 : **4** |

- **심각도: 전부 WARNING.** R2·R3(규칙 ③)가 ERROR인 것과 대비된다 — 저쪽은
  *viewpoint 누락 = 2805CF18*이라는 **로드 거부 실측**이 있었다. 동작 배선에는 없다.
  반례 10건이 오히려 반대를 시사한다:
  - `target-parameter` 6건 — `[Parameters].[ColorStart]`인데 그 파일 `Parameters`에는
    `매개 변수 1~6`뿐. **진짜 dangling**이고 골든셋 밖 파일(`old/`)이다
  - `source-field` 4건 — 가리키는 이름이 `groupfilter@level`에만 있고 `<column>`·
    `<column-instance>` 어디에도 없다. 규칙 ②의 **잔재 dangling과 같은 계열**이며
    **골든셋 파일 1개가 여기 포함된다** → 이 표면은 ERROR가 될 수 없다
- **`<actions>` 안의 `<datasources>`·`<datasource-dependencies>`는 동작이 아니다** —
  동작이 참조하는 필드 정의의 사본이다(84개 중 3개 파일). 배선으로 읽으면 통째로 오탐
- **같은 결함을 여러 번 말하지 않는다** — `exclude-sheet`는 파일당 수백 번 나온다.
  (표면, 값)으로 합치고 등장 횟수를 메시지에 적는다
- **콤마 목록을 무조건 쪼개지 않는다** — 통째로 해소되면 그대로 둔다. 실측 1,460개
  시트·대시보드 이름에 콤마는 없었지만 금지된 것은 아니다
- **원천**: 01 v2.0 §4 T3 · 2026-07-31 전수 실측

### R18. 선반 배치 참조 끊김 [L-B · **구현됨 = rule ⑪**]

사용자가 **페이지·필터·마크·열·행**에 올린 것이 실재하는 필드인가 (01 v2.0 §4 T4-a).
끊기면 파일은 열리되 그 필드가 워크시트에서 제거되거나 오류 상태로 뜬다.

- **규칙 ②와 자리가 다르다.** ②는 `REFERENCE_SURFACES` 9자리만 본다. 선반은 그 밖에
  있었다 — 마크 인코딩의 `color`·`size`·`tooltip`, 열·행의 **요소 텍스트**,
  필터의 `<slices>/<column>`, 정렬·축 계열이 무주공산이었다
- **실측** (2026-07-31, 실파일 84개 전수. ②가 이미 보는 자리는 뺐다):

  | 표면 | 해소 : 미해소 |
  |---|---|
  | `<slices>/<column>` (필터 선반) | 2,462 : 0 |
  | `groupfilter@level` (필터) | 2,553 : 0 |
  | `<cols>` (열 선반, 텍스트) | 445 : **10** |
  | `<rows>` (행 선반, 텍스트) | 445 : **6** |
  | `tooltip`·`color`·`size`@column (마크) | 871 : 0 |
  | `computed-sort`·`manual-sort`·`sort`·`alphabetic-sort`·`shelf-sort-v2` | 429 : 0 |
  | `pane@x-axis-name` · `@y-axis-name` | 140 : **12** |
  | `reference-line`·`label-data`·`order`·`table-calc@ordering-field` | 17 : 0 |
  | `<pages>/<column>` (페이지 선반) | **실측 0회** |

- **심각도: WARNING.** 반례 28건이 전부 골든셋 파일 하나(`태블로판차분석`)에서 나왔고
  그 파일은 열린다 — `Calculation_0630847643873281`·`Calculation_2012107314806786`을
  열·행·축이 가리키는데 데이터소스 어디에도 없다. ②의 잔재 dangling과 같은 계열이다
- **`<pages>`는 실측 0회인데도 넣었다. 근거는 추측이 아니라 공식 XSD다** —
  내용 모델이 `<column>` 자식 목록이고 타입이 `QualifiedName-ST`로, 실측 2,462:0인
  `<slices>/<column>`과 같은 구조다 (`twb_2026.1.0.xsd:5497`)
- **보지 않는 것**: `<dictionary>/<bucket>`(그룹·집합의 **값** 목록, 반례 172건) ·
  `<formatted-text>/<run>`(텍스트 서식 **본문**, 반례 34건) ·
  `<datasource-dependencies>` 하위(정의 사본) · ②가 이미 보는 9자리
- **T4-b(어떤 필드를 어떤 선반에 놓으면 오류인가)는 여기 없다** — 정답지가 없다
  (01 v2.0 §7 · `TODO.md` L1)
- **부수 산물: `fieldref` 다층 장식 결함**을 이 스캔이 드러냈다.
  `[pcto:sum:값:qk]`·`[cum:usr:LinPack_…]`처럼 장식이 **겹쳐 붙는데** 한 겹만
  벗기고 있었다. 벗겨지지 않을 때까지 반복하도록 고쳤고, 반례가 48 → 28로 줄었다.
  규칙 ②의 거짓 dangling도 같은 만큼 준다
- **원천**: 01 v2.0 §4 T4-a · 2026-07-31 전수 실측

### R19. `groupfilter@level`에 데이터소스 한정자 [L-B · **구현됨 = rule ⑦-d**]

필터의 `level`은 **비한정 이름**이어야 한다. 붙이면 파일은 열리되 그 필터가 버려진다.

```
'매출 추이' 오류: 필터링을 위해 포함된
'[federated.0d2m…].[none:Calculation_…:nk]' 필드가 없습니다.
```

- **실측** (2026-07-31, 실파일 85개 중 이 요소를 쓰는 31개):
  **비한정 3,484 : 한정 0.** `level` 없는 묶음 노드 430건은 대상 밖
- **R18의 `groupfilter@level 2,553 : 0`과 축이 다르다.** 저기는 *"가리키는 필드가
  실재하는가"*(규칙 ⑪), 여기는 *"그 자리에 쓸 수 있는 표기인가"*(규칙 ⑦)다.
  한정된 `level`은 필드가 멀쩡히 실재해도 버려지므로 ⑪이 원리적으로 못 잡는다
- **⑦-b와 방향이 반대다** — `[Multiple Values]`는 붙여야 하고 `level`은 떼야 한다.
  자리마다 한정 여부가 정해져 있다는 것이 규칙 ⑦의 성질이다
- **더 강한 성질은 실측이 부정했다**: `level`이 `filter@column`의 기저 이름과
  다른 정상 사례가 있다(`column='[ds].[Action (C_팀명)]'` ↔ `level='[팀명(복사본)_…]'`).
  남는 불변식은 한정자 유무뿐
- **심각도: WARNING.** 파일은 열린다. 정상본 85개에서 finding 0건
- **발견 경로가 다르다.** 앞의 R1~R18은 전부 남이 만든 실파일에서 나왔다.
  이건 `/author-loop`이 **빈 손에서 만든** 워크북이 냈다 — 편집 경로에서는
  Tableau가 써 둔 표기를 그대로 두므로 밟을 일이 없는 층이다 (01 v2.0 §2)
- **원천**: docs/05-xsd-spike.md F5-f · 주입 레시피 `R21-qualify-filter-level`

### R20-a. 집합의 모양 — 시스템 표식과 숨김의 짝 [L-B · **보류 — 증상 귀속 대기**]

규칙 ⑨ `set.definition`은 *"집합에 기반 필드가 있는가"*만 본다. 모양은 안 본다.

성질: **집합은 사용자 것이거나 시스템 것이다. 시스템 표식(`user:auto-column`)을
달았으면 숨겨진다(`hidden='true'`).**

| `<group>` 속성 조합 | 건수 | 파일 |
|---|---|---|
| `caption` + `ui-builder='filter-group'` (hidden 없음) | 46 | 22 |
| `caption` + `hidden='true'` + `auto-column='sheet_link'` | 60 | 21 |
| `hidden='true'` + `auto-column='exclude'` | 20 | 21 |
| `caption` + `auto-column='sets'` — **hidden 없음** | **2** | **1 (MA_003, 거부된 파일)** |

**80 : 2.** `<group>` 128개 중 두 표식이 다 없는 것은 0개다.

⚠️ **불변식은 섰는데 증상을 이 축에 귀속시킬 수 없다.** 관측된 세 사례가 전부
교락돼 있다 — MA_003은 기반 필드도 없어 ⑨가 이미 잡고, 저작 B는 **속성과 배치를
한꺼번에 고쳤고**, 매출요약은 집합을 확인하지 않았다. 분리 실험본
(`매출요약_V1_속성만` · `매출요약_V2_자리만`)을 사용자에게 넘겼다.
**결과가 오기 전에는 규칙화하지 않는다.**

- 이 규칙은 ⑨의 독스트링과 부딪힌다 — *"모양을 열거하지 않고 기반 필드의 유무만
  본다"*. 속성 값이 아니라 **두 표식의 짝**을 보는 성질 형태라야 그 원칙을 지킨다
- **원천**: 05 F5-g · **F5-i** · 2026-07-31 저작 B안

### ~~R20-b. 집합이 놓이는 자리~~ [**폐기 — 표본 0**]

F5-g의 `<filter> 38 : 인코딩 0`은 **두 종류의 집합을 한 칸에 셌다.**

| | 건수 | 파일 | 뷰에 배치된 사례 |
|---|---|---|---|
| 사용자 집합 (`ui-builder`) | 46 | 22 | **0** |
| 동작이 만든 집합 (`auto-column`+`hidden`) | 80 | 21 | 38 (`<filter>`, **2개 파일**) |

38건은 전부 **동작 집합**이고 Tableau가 구조상 필터에 넣는 것이다. 사용자가 집합을
어디에 놓아도 되는지는 말하지 않는다. 그리고 **사용자 집합 46개는 뷰에 한 번도
배치되지 않았다** — 계산식에서만 참조된다. 배치 표본이 **0**이다.

멈춤 조건: *"정상본 표본이 0개다 → 규칙화하지 않는다."* 더구나 집합을 색상에 올려
IN/OUT으로 칠하는 것은 Tableau의 정규 기능이라, 38:0을 규칙으로 만들면 **정상
워크북을 때린다.** R24와 같은 자리다 — 표본이 생기면 그때 되살린다.

- **원천**: 05 **F5-i**

### R21+R22. 동작의 모양 — 명령·param 어휘·`<link>` 짝 [L-B · **구현됨 = 규칙 ⑬ `action.shape`**]

두 후보를 하나로 냈다. **같은 요소·같은 층·같은 증상**이다 — 파일은 경고 없이 열리는데
동작 대화상자에서 편집이 막히고 동작이 발동하지 않는다.

규칙 ⑩ `action.refs`는 *"가리키는 시트·매개변수·집합·필드가 실재하는가"*(**참조**)를 본다.
⑬은 *"Tableau가 아는 배선 모양인가"*(**어휘**)를 본다. 저작본은 가리키는 대상이 전부
실재해서 ⑩이 침묵했다 — 그래서 ⑩ 확장이 아니라 **별도 규칙**이다.

**`<action>`은 세 모양뿐이고, 명령과 `<link>`가 짝을 이룬다** (실파일 63개 · 동작 140건):

| 종류 | 명령 | `<link>` | 건수 |
|---|---|---|---|
| 필터 | `tsc:tsl-filter` | 있다 — `expression='tsl:…'`에 필드 매핑이 실린다 | **14 : 0** |
| 하이라이트 | `tsc:brush` | 없다 | **17 : 0** |
| URL | 없다 | 있다 — `expression='http…'` | **1** |

```xml
<link caption='제품 필터' delimiter=',' escape='\'
      expression='tsl:&lt;대시보드&gt;?&lt;필드&gt;~s0=&amp;lt;&lt;필드&gt;~na&amp;gt;'
      include-null='true' multi-select='true' url-escape='true' />
```

param 이름은 **종류마다 어휘가 갈린다. 교차 0건:**

| 종류 | 관측된 param 이름 |
|---|---|
| `action` / `tsc:tsl-filter` | `target` 14 · `exclude` 14 |
| `action` / `tsc:brush` | `target` 17 · `exclude` 16 · `field-captions` 16 · `special-fields` 1 |
| `edit-parameter-action` | `target-parameter` 75 · `source-field` **70** |
| `edit-group-action` | `selection-clear-set-option` 47 · `target-group` 47 |

> **F5-g의 수치가 정정됐다.** 그 표는 내 저작본을 정상본으로 셌다. `source-field`는
> **없는 이름이 아니라 70건 관측되는 정상 이름**이고, 저작본이 그걸 `<action>`에 붙인
> 것이 결함이었다. 전역 화이트리스트로는 못 잡는다 — 종류별로 갈라야 걸린다.

- **모양이 아니라 성질로 잡을 수 있는가**: 명령·param 이름은 열거형이라 없다.
  **화이트리스트 + "목록 밖은 WARNING"**이 맞다 — 규칙 ①(`calc.functions`)과 같은 구조다:
  우리 목록이 불완전할 수 있으므로 ERROR가 아니다
- **XSD가 못 잡는 이유**: `ActionList-CommandName-ST`가 `<xs:pattern value="[^:]+:[^:]+"/>`
  일 뿐 열거가 아니고, `<param>`은 `name`·`value` 둘 다 `xs:string`이다
- **`<nav-action>`은 실파일 0건** — 어휘를 모르므로 판정하지 않고 `note_partial`한다
- **아직 안 한 것**: `<link expression>` 안의 **필드**를 대조하면 참조 무결성 축이 넓어진다
  (지금 이 자리의 필드는 아무도 안 본다). 축이 달라 ⑬이 아니라 ⑩의 몫이다
- 주입 레시피 `R22-unknown-action-command` · `R23-drop-filter-link`
- **원천**: 05 F5-g · **F5-h** · 2026-07-31 저작 B안

### R23. 집계 수준 정합 — 인코딩에 올린 행수준 차원 [L-B · **미구현** — 규칙 ⑫ 몫]

마크 그레인보다 잘게 쪼개진 필드를 도구 설명·색상 등에 **행수준 그대로** 올리면
Tableau가 그 필드를 빨갛게 칠한다. 집계(`ATTR()`/`MIN()`)로 감싸야 한다.

- 실측 사례: 그레인이 `월 × 제품`인 라인 차트의 도구 설명에 `[none:담당자:nk]` →
  빨간 필드 + 렌더 실패. `특성(담당자)`로 바꿔야 한다
- **⑧ `calc.aggregation`과 다르다** — ⑧은 *계산필드의 수식*에 집계가 있는지 본다.
  이건 *뷰의 그레인 대비 필드의 그레인*이라 뷰 전체를 봐야 한다
- ⚠️ **`derivation='Attribute'`는 실파일 0건이다.** 관측된 값은
  `None`/`User`/`Sum`/`Min`/`Month`/`Count`/`Year`/`Month-Trunc`뿐이고
  XSD의 `AggType-ST`는 **제약 없는 문자열**이다. 접두사 규칙의 일관성만이 근거다
- **판정에 필요한 것**: "뷰의 그레인"을 정적으로 계산할 수 있는가. 행·열·페이지·세부 정보에
  올라간 차원의 집합이 그레인인데, 데이터 없이 필드 간 함수 종속을 알 수 없다.
  **잘못 판정하면 정상 파일을 막는다** — 규칙 ⑫ 착수 전에 이것부터 정한다
- **원천**: 05 F5-g · 2026-07-31 저작 C안

### R24. `<pages>`의 `<current-page>` [**표본 없음 — 규칙화하지 않는다**]

페이지 선반을 쓰면서 창의 `<viewpoint>`에 `<current-page>`가 없으면 그릴 페이지가
없어 캔버스가 빈다 — **가설이다.**

**실파일 85개에서 `<pages>`는 0회 나온다.** 공식 XSD만 있다
(`VisualDoc-CurrentPage-G` → `<multibucket>` → `<bucket>`).

`/defect-loop` 멈춤 조건에 걸린다: *"정상본 표본이 0개다 → 규칙화하지 않는다."*
관측만 남긴다. 표본이 생기면 그때 R번호를 살린다.

---

## C. 정적 검증 불가 — 범위 밖 (명시적으로 표기)

| 항목 | 왜 불가 | 원천 |
|---|---|---|
| 가표 잔존 (상태 매개변수에 반응 안 하는 값 영역) | HTML 원본과의 대조가 필요 | 함정 I3 |
| `RUNNING_SUM` 계산 방향 무시 | 수제 twb에서 도큐먼트 모델에 반영 안 됨(원인 미상) | 함정 S8 |
| paramctrl 폭 과점으로 이웃 워크시트 `##` 렌더 | 로더의 flow 재계산 결과 | 함정 I5 |
| live DB connection 실연결 | 오프라인 불가 | 01 §8 |
| render 런타임 (blank viz 등) | 실제 쿼리·마크 렌더 필요 | 01 §8 |

이 항목들은 **"오프라인 미검증" 경고로 표기**한다 (S5 범위한계 명시). 조용히 통과시키지 않는다.

---

## D. 골든셋 조달에의 함의

고장 파일이 남아 있지 않지만, **위 항목들은 고장 파일을 만드는 레시피다.**
정상 워크북(현재 9개 확보)에서 출발해 R1~R7을 의도적으로 주입하면
"실제 Tableau에서 안 열림"이 라벨로 보장된 고장 파일을 결정론적으로 생성할 수 있다.

| 규칙 | 주입 방법 | 기대 라벨 |
|---|---|---|
| R1-b | 매니페스트에서 `SortTagCleanup` 삭제 (`manual-sort`는 유지) | 로드 거부 |
| R1-a | 매니페스트에서 `_.fcp.DashboardRoundedCorners…` 삭제 (사용 요소는 유지) | 로드 거부(미검증 — 실험 A) |
| R2 | 대시보드 window `<viewpoints>`에서 viewpoint 1개 삭제 | 내부 오류 2805CF18 |
| R3 | 존의 `name`을 없는 시트명으로 변경 | 로드 거부 |
| R4 | ds에서 `<style>`을 `<column>` 앞으로 이동 | D2E8DA72 |
| R7 | `param-domain-type`을 `'all'`로 변경 | D2E8DA72 |

**정상 대조본 = 원본 9개, 고장본 = 주입본.** 각 주입본은 Tableau Desktop 2026.1에서
실제로 열어 라벨을 확정한다(로컬 전용 — Cloud REST API 검증은 사용 불가).

이 방식이면 D5의 "규칙별 고장 케이스 ≥3"을 손으로 워크북을 만들지 않고 채울 수 있다.

### D.0 구현 완료 (2026-07-29) — `tools/inject_defects.py`

위 6종이 결정론적 스크립트가 됐다. 원본은 읽기만 하고, `.twb` 엔트리만 교체하며
나머지(특히 `.hyper`)는 **바이트 그대로** 복사한다 — 확인됨(6/6 동일).

```bash
python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>              # 6종
python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b  # + 16종
```

산출물과 함께 **라벨 대장**(`labels.json`)이 나온다. `observed`·`error_text` 칸이 비어
있으며, 사용자가 채우면 그대로 AC2·AC3 측정 입력이 된다.

**첫 실행이 이미 하나를 증명했다** — 어느 계층이 잡는지가 라벨링 전에 측정된다:

| 레시피 | vendored XSD(L-A) | 함의 |
|---|---|---|
| R4 자식 순서 | **검출** `SCHEMAV_ELEMENT_CONTENT` → ERROR | L-A 담당 확인 |
| R7 enum | **검출** `SCHEMAV_CVC_ENUMERATION_VALID` → ERROR | L-A 담당 확인 |
| R1-a · R1-b · R2 · R3 | **오류 0건 — 그대로 통과** | **AC3 무거짓통과의 실증** |

아래 4종은 L-A를 통과하고도 Tableau가 열지 못하는 파일이다. **L-B 규칙 ③·⑥이 없으면
게이트가 이 파일들을 승인한다** — 이 프로젝트가 존재하는 이유가 여기서 측정된다.

### D.1 주입은 라벨링만 하는 게 아니다 — 대응표를 캔다 (2026-07-29)

R1-b의 미지수는 "**어느 항목이 어느 요소를 게이팅하는가**"다. 그런데 로드 거부 메시지가
그 답을 직접 뱉는다:

```
no declaration found for element 'manual-sort'
                                  ^^^^^^^^^^^ 대응 요소
```

→ **실험 B**: 확보된 항목 19종을 하나씩 지운 파일을 만들어 연다.
거부되면 메시지에서 대응 요소를 읽는다. 열리면 그 파일이 해당 기능을 안 쓴다는 뜻이며,
그것도 정보다(다른 표본에서 재시도).

**Tableau가 대응표를 스스로 불러준다.** 배치 1회로 2쌍 → 최대 20쌍.
성공하면 D8(`.rcc` 26MB 역수확)이 불필요해질 수 있다.

전제: *"매니페스트 항목 추가 자체는 무해"*(함정 I1 격리 실험)의 **역방향은 미검증**이다 —
삭제가 항상 거부를 유발하는지는 실험이 답한다.

---

## R25 — `<object-graph>` 누락 → ✅ **규칙 ⑭ `datasource.shape`** (2026-08-10)

**증상은 층 1~4 어디에도 없다.** 파일이 열리고 시트도 보이는데, **데이터 원본 탭을
클릭하는 순간 Tableau가 그대로 종료된다.** 저장할 것도 없이 앱이 사라진다.

| | |
|---|---|
| 발견 | `/author-loop` 저작본(`관찰_base.twb`)을 소유자가 열어 확인 |
| 린터(당시) | `passed=true`, findings **0** — 잡는 규칙이 없었다 |
| 상관 | `relation`을 가진 데이터 원본 **113 : 0** 전부 `<object-graph>` 보유 |

### 분리 실험이 후보 셋을 갈랐다 (2026-08-10)

결함 표본은 세 조각이 한꺼번에 빠져 있었다. 정본(`관찰_B_CSV연결만.twb`)에서
하나씩만 지운 변형 3개를 열었다:

| 변형 | 뺀 것 | Tableau | 결론 |
|---|---|---|---|
| V1 | `<object-graph>` | **데이터 원본 클릭 시 즉시 종료** | 인과 확정 → 규칙 ⑭ ERROR |
| V2 | `<relation type='table'>`의 `<columns>` | **이상 없음** | **후보 폐기** — 상관 39:0이었지만 증상이 없다 |
| V3 | 매니페스트 3항목 | **로드 거부** D2E8DA72 | 규칙 ⑥-b 게이트 `object-graph` 추가 |

V3의 거부 메시지는 세 자리를 한꺼번에 지목했다 — 세 항목이 데이터 원본의
객체 모델 문법을 통째로 연다:

```
Error(119,178): value 'table' not in enumeration                    ← relation@type
Error(120,95):  missing required attribute 'dim-percentage'         ← columns
Error(120,95):  missing required attribute 'measure-percentage'
Error(124,21):  no declaration found for element 'object-graph'     ← object-graph
```

### 심각도 — 층 1이 아닌데 ERROR인 유일한 규칙

- 인과가 실험으로 확정됐다 (V1). 상관만 보고 낸 것이 아니다
- 실파일 114개 finding 0건 — 거짓양성 위험 없음 (AC7)
- 증상이 층 4보다 무겁다. **빨간 느낌표는 보고 고치지만 앱 종료는 작업분이 날아간다**

→ `01 v2.0 §4`의 실패 4층에 이 자리가 없다. **층 분류의 빈칸**이다 (`TODO.md` L6).

### 남은 미분리

V3는 3항목을 한꺼번에 지웠다 — `object-graph`를 게이팅하는 것이 셋 중 어느 것인지
모른다. 대응표는 셋 다 요구한다(과요구 가능). `simple-id`에서 같은 과요구가
실험으로 드러난 전례가 있다 (`TODO.md` L5).
