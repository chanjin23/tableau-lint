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

#### R1-b. 일반 계열 — 대응표 필요 [MVP · 표 2쌍뿐]

이름이 요소명과 다르다 → 표로만 풀린다.

- **실측 쌍**: `<manual-sort>` ↔ `SortTagCleanup` (함정 W2 / F5),
  `<edit-group-action>` ↔ `GroupAction` + `GroupActionAddRemove` (함정 I7)
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
