# Tableau 저작 AI — 설계 (Design)

> SOR 문서. 문제정의 [`01-problem-definition.md`](./01-problem-definition.md), 스펙 [`02-specification.md`](./02-specification.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 확정 |
| 버전 | v1.7 (2026-07-29) |
| 소유자 | ax3didim@gmail.com |
| 전제 | [문제정의](./01-problem-definition.md)·[스펙](./02-specification.md) 확정 |
| 다음 | 구현 (MVP) |
| v1.1 변경 | D3 L-A 전처리 3단계·버전키 정정 · L-B 규칙 ⑥ 신설·③ 구체화 · D3.5 구조 모델 신설 · D4 실제 구조 반영 · D5 골든셋 조달 · D8 신설 |
| v1.2 변경 | 규칙 ⑥을 ⑥-a(fcp·표 없음)/⑥-b(일반·표 필요)로 분리 · D8 우선도 하향 (근거 05 F7) |
| v1.3 변경 | **구현 착수 전 설계 미결 8건 해소** — D3.5 규칙 입력 계약(`ValidationContext`) 개정 · **D3.6 calc 표면 실측 신설** · D3에 L-A 심각도 정책·입력 단계 추가 · D4 구조 갱신 · D5에 AC8·표본 편향 추가 · **D9 입력 방어 신설** |
| v1.4 변경 | **D9.1 신설** — `unpack`의 오류 전달 계약(`ArchiveError`) · zip bomb 2선 방어(선언 크기 ≠ 실제 해제량) |
| v1.5 변경 | **D3.7 신설** — calc 수집을 Lark 문법 파서에서 어휘 스캐너로 뒤집었다 (수식 5,270건 실측: 함수 26종·화이트리스트 미매칭 0) |
| v1.6 변경 | **D3.6.1 신설** — 표기 정규화 계약(`fieldref.py`): 후보 다중화 · 역할 접두사 비고정 · `]]` 이스케이프 · 특수 네임스페이스 3종 |
| v1.7 변경 | **D3.6.2·D3.6.3 신설** — 필드 유니버스 4곳(미해소 687→94) · **규칙 ② 심각도를 ERROR→WARNING으로 내림**(정상 파일에도 잔재 dangling이 있다는 실측) |
| 근거 | [`05-xsd-spike.md`](./05-xsd-spike.md) 실측, [`06-rule-candidates.md`](./06-rule-candidates.md) 규칙 인벤토리 |

---

> **Context**: 스펙 확정 후 설계 착수. 사용자 확정 = **집중점 = 검증기(C3-B)**, **패키징 = MCP 코어**. 목표 = 공식 XSD 위에 시맨틱 검증기를 얹어 "구문통과·의미실패(안 열림)" 파일을 오프라인·빠르게 사전차단 → 사용자의 느린 E2E를 대체. 편집/저작/쿼리는 검증기 위에 얹는 후순위.

## D0. 결정 요약 (S6 해소)

| 미결 | 결정 |
|---|---|
| 패키징/호스트 | **Python MCP 서버** (코어, 호스트 독립). deps 전부 Python이라 자연스러움 |
| calc 파서 | 기존 라이브러리 없음 → **Lark 경량 문법**(함수호출·필드참조 추출 전용, 평가기 아님) |
| 함수 화이트리스트 | 공식 JSON 없음 → help.tableau.com 1회 스크랩→**버전별 정적 JSON을 repo 유지** |
| MVP 집중 | **C1 unpack + C2 inspect + C3 검증기(2계층)**. 편집/저작/쿼리 후순위 |
| L-B MVP 범위 | **고가치 4규칙**: ①함수 화이트리스트 ②필드참조 해소 ③named 참조무결성 ⑥매니페스트 게이트. ④메타↔hyper·⑤connection = 2차 |

### D0.1 v1.1 추가 결정 (스파이크 결과 반영)

| 항목 | 결정 | 근거 |
|---|---|---|
| L-A 실효성 | **성립. 단 전처리 3단계 필수** (스텁 주입·과엄격 패치·fcp 정규화) | 05 F1~F3 |
| XSD 선택 키 | `<workbook version>` → **`source-build`** 로 변경 | 05 F4 |
| 규칙 ⑥ 신설 | 매니페스트 게이트 일관성 — XSD가 못 잡는 로드 거부 클래스 | 05 F5 |
| 심각도 기조 | 확신 있는 것만 ERROR. 화이트리스트 미등재·파싱 실패는 WARNING | 02 S1-6 |
| 대상 버전 | **2026.1 단독**, 로컬 전용 | 02 S7 |
| 골든셋 조달 | 정상본 9개 확보 + **결함 주입으로 고장본 생성** | 06 §D |

## D1. 아키텍처

- **언어/런타임**: Python. 이유 = 핵심 deps 전부 Python: `lxml`(XSD·트리), `tableauhyperapi`(hyper Catalog), `document-api-python`(구조 파싱 보조), `Lark`(calc 문법).
- **형태**: MCP 서버(FastMCP류). 호스트 독립 → Claude Code/Desktop/자체앱 재사용.
- **성격**: 검증 파이프라인 중심. 상태없음(stateless), 결정론.

## D2. MCP 도구 표면 (MVP)

- `twb_unpack(path)` — `.twbx`→`.twb`+`.hyper` 추출 (`.hyper` 무손실). [C1]
- `twb_inspect(path)` — 구조 모델(datasources·fields·calc·sheets·dashboards·참조) 반환. 검증·이해 입력. [C2]
- `twb_validate(path)` — **2계층 검증 → findings[] 반환.** 핵심. [C3]
- (후순위 stub) `twb_edit`, `twb_query`.

### D0.2 v1.3 추가 결정 (구현 착수 전 미결 해소)

문서만으로는 규칙을 못 쓰게 만들던 항목들이다. **정하지 않고 구현에 들어가면 규칙 5개를
다 고치게 되는** 것들이라 코드보다 먼저 확정했다.

| 항목 | 결정 | 근거 |
|---|---|---|
| 규칙 입력 | `check(model)` → **`check(ctx)`**. 컨텍스트가 모델 + 원본 트리 + 정규화 사본을 함께 든다 | D3.5 |
| 입력 오류 소유자 | **엔진**. `Stage.INPUT` 이름으로 나가되 규칙 파일은 없다 | D3.0 |
| L-A 심각도 | 오류 유형별 등급표. **거짓양성과 진짜 오류가 같은 오류코드**라 메시지까지 본다 | D3 L-A |
| "검사 안 함" 표현 | `ValidationReport.coverage` 신설. `passed`와 분리 | D3 출력 |
| 줄번호 | `Finding.line: int \| None` + 정렬 키에 반영 | D3 출력 |
| calc 수집 표면 | 수식 표면 2곳 · 직접 참조 표면 7곳으로 **실측 확정** | **D3.6** |
| 입력 방어 | lxml 파서 옵션·ZIP 상한을 io 구현 **전에** 고정 | **D9** |
| 규칙 ⑥ × version | 열린 질문으로 기록 (MVP read-only에는 무해) | 01 §9.1 |

## D3.0 입력 단계 (v1.3 신설)

파일을 읽지 못하는 경우(없음·디렉토리·확장자 불일치·손상 ZIP)는 **예외가 아니라
ERROR finding**이다 (02 S5). 호출자가 try/except와 게이트 판정을 따로 만들지 않게 하려는
것인데, 소유자가 정해져 있지 않았다.

**엔진이 소유한다.** 규칙에 맡길 수 없는 이유가 구조적이다 — 이 판정은 모델 생성 **전**에
나므로 `ValidationContext`조차 만들 수 없고, 컨텍스트를 받는 규칙이 "컨텍스트를 못 만들어
실패한 상황"을 판정하는 순환이 된다.

- 결과는 `Stage.INPUT` · `rule_id="input.readable"`로 나간다 (판정 경로는 하나로 유지)
- 입력에서 멈추면 **나머지 규칙 전부를 `SKIPPED`로 기록**한다. 이걸 빼면 리포트가
  "ERROR 1건 + 나머지 침묵"이 되어 나머지가 통과한 것처럼 보인다
- `Stage.INPUT`에는 규칙 파일이 없다 — 회귀 테스트로 못 박는다

## D3. C3 검증기 내부 (핵심 산출물)

**L-A 구문 (공식 XSD)** — v1.1 전면 개정, 근거 [`05-xsd-spike.md`](./05-xsd-spike.md)

공식 XSD를 그대로 넣으면 **정상 파일 9/9가 실패한다.** 전처리 3단계가 L-A의 실질이다.

*vendoring 시점 (`tools/vendor_schemas.py`)*
1. **스텁 주입** — 공식 XSD의 `xs:import` 2개가 `schemaLocation` 없이 선언돼 컴파일 불가.
   `user`(→`UserAttributes-AG`) · `xml`(→`lang`/`space`/`base`/`id`) 스텁 스키마를 함께 vendoring 하고
   `schemaLocation`을 주입한다.
2. **과엄격 패치** — `explain-data`가 필수로 선언돼 있으나 실제 Tableau는 미사용 시 안 쓴다 →
   `minOccurs="0"`. **패치는 목록으로 코드에 두고**, 상류 갱신 시 재적용·재검증한다
   (패치 실패 = vendoring 실패로 처리, 조용히 넘기지 않는다).

*검증 시점 (`validation/syntactic/xsd.py`)*
3. **fcp 정규화** — Tableau 하위호환 접두사 `_.fcp.<기능>.<true|false>...<이름>`을
   **트리 사본에서** 벗긴 뒤 검증한다. 요소 태그와 속성 키 양쪽에 적용.
   원본 트리는 불변(S1-1 문자열 편집 금지 및 read-only 원칙).

*XSD 선택*
- 키는 **`source-build`** (`2026.1.1 (…)` → `2026_1` → `twb_2026.1.0.xsd`).
  `<workbook version>`은 최소 호환 버전이라 실사용 파일에서 절대 적중하지 않는다(실측 `18.1`).
- MVP 대상은 2026.1 단독(S7). 미지원 `source-build` → 명시 경고(조용히 통과 금지).
- `version`/`original-version`은 버리지 않는다 — L-B 규칙 ⑥의 입력.

*L-A 위반의 심각도 정책 (v1.3 신설 — 2026-07-29 실측)*

"XSD 위반 = 전부 ERROR"로 두면 안 된다. `explain-data`가 이미 **XSD가 실제 Tableau보다
엄격하다**는 실증이고(F3), 표본 9개로 못 걸른 과엄격이 더 있으면 AC7이 무너진다.

lxml `error_log`의 오류 유형을 찍어 등급표를 만들려 했으나 **실측이 더 나쁜 사실을 알려줬다**:

```
미지/오위치 요소   SCHEMAV_ELEMENT_CONTENT (1871)  "This element is not expected."
필수 자식 누락     SCHEMAV_ELEMENT_CONTENT (1871)  "Missing child element(s)."
                   ^^^^^^^^^^^^^^^^^^^^^^^ 같은 코드다
```

거짓양성(`explain-data`)과 진짜 로드 거부(R4 자식 순서 위반)가 **같은 오류코드를 쓴다.**
코드만으로는 가를 수 없어 메시지 본문까지 본다 (libxml2 메시지는 영어 고정).

| 유형 | 판별 | 심각도 | 근거 |
|---|---|---|---|
| 열거형·데이터타입 위반 | `SCHEMAV_CVC_ENUMERATION_VALID` 등 | **ERROR** | R7 실측 = D2E8DA72 로드 거부 |
| 요소가 허용되지 않음 | 1871 + `not expected` | **ERROR** | R4·R5·R6 실측 = 로드 거부 |
| 필수 자식 누락 | 1871 + `Missing child element` | **WARNING** | `explain-data`가 이 클래스의 거짓양성 |
| 그 외 | — | **WARNING** | 미분류 = 지식의 공백 (S1-6) |

추가 게이트: **검증한 릴리스에서만 ERROR를 낸다.** 미지원 릴리스는 L-A를 실행하지 않고
스킵을 보고한다 — 우리가 그 문법을 모른다는 뜻일 뿐인데 ERROR를 내면 그 릴리스에서 AC7이
즉시 무너진다.

검증: 주입 고장본으로 확인했다. R4 → ERROR, R7 → ERROR, 정상본 9개 → 오류 0건.

**L-B 시맨틱 (6규칙 — MVP는 ①②③⑥, ④⑤ 2차)**

1. **[MVP] calc 함수 화이트리스트** — Lark로 calc 내 함수토큰 추출 → 버전별 `functions_<ver>.json` 대조.
   - **심각도 = WARNING** (S1-6): 목록에 없음 = 우리 목록의 공백일 수 있다. ERROR로 막지 않는다
   - 파싱 실패 시 해당 calc의 하위 검사를 스킵하고 그 사실을 WARNING으로 보고
2. **[MVP] calc 필드참조 해소** — `[Field]`·`[ds].[Field]` 참조 추출 → 데이터소스별 필드/calc 집합 대조.
   - **특수 네임스페이스 예외 필수**: `[:Measure Names]`·`[:Measure Values]`·`[Multiple Values]`·
     `[__tableau_internal_object_id__].[…]`. 과거 lint가 `[:Measure Names]`에서 오탐했다(함정 S9)
   - 대상 집합은 `<column>`만이 아니다 — **D3.6.2**의 네 곳을 전부 모은다
   - **심각도 = WARNING** (v1.7 하향). 정상 파일에도 잔재 dangling이 있다는 실측 때문이다.
     근거와 승격 조건은 **D3.6.3**
3. **[MVP] named-content 참조무결성** — 구체 케이스로 정의(실측 기반, [`06-rule-candidates.md`](./06-rule-candidates.md) R2·R3):
   - 대시보드 worksheet 존 `name` ↔ `<worksheets>` 시트 정의 (dangling = ERROR, 고아 = WARNING)
   - 배치된 시트마다 대시보드 window `<viewpoints>/<viewpoint name>` 존재 (누락 = **내부 오류 2805CF18** = ERROR)
   - 배치된 시트마다 `<window class='worksheet'>` 존재 (누락 = ERROR)
4. **[2차] 메타↔hyper 대조** — `hyperapi Catalog.get_table_definition()` vs `.twb` 필드/타입. (embedded extract 한정)
5. **[2차] connection 필수속성** — 정적 규칙셋으로 필수속성·타입 검사. live DB 실연결은 "미검증" 경고.
6. **[MVP · v1.1 신설] 매니페스트 게이트 일관성** — 기능 요소를 쓰면서
   `<document-format-change-manifest>`에 대응 항목이 없으면 `no declaration found for element`로 로드 거부.
   - **XSD가 원리적으로 못 잡는 영역** — AC3(무거짓통과) 위반의 실증 사례
   - **v1.2: 두 갈래로 분리한다** (근거 [`05-xsd-spike.md`](./05-xsd-spike.md) F7):

   **⑥-a fcp 계열 — 대응표 불필요**
   - 매니페스트 항목 이름에도 fcp 접두사가 붙는다. 접두사를 벗기면 트리의 fcp 기능명과
     10/10 파일에서 완전 일치 → **규칙이 데이터가 아니라 구조에서 도출된다**
   - `_.fcp.<F>....` 사용 ⇒ 매니페스트에 `_.fcp.<F>.true...<F>` 필요
   - ⚠️ **입력이 L-A와 다르다** — fcp 정규화가 요소의 소속 기능을 지우므로
     **정규화 전 원본 트리**를 봐야 한다. D3.5·규칙 인터페이스 설계에 영향
   - 인과(항목 삭제 → 실제 거부) 미검증 → 확정 전까지 WARNING

   **⑥-b 일반 계열 — 대응표 필요**
   - 이름이 요소명과 다르다(`manual-sort`↔`SortTagCleanup`). 표로만 풀린다
   - 항목 **이름 19종은 확보**(F7). 미지수는 "각 항목 ↔ 어느 요소"
   - **표에 있는 기능만 ERROR.** 표에 없는 요소를 추측해 ERROR 내지 않는다(S1-6)
   - 확장 경로: 주입 실험 B([`06`](./06-rule-candidates.md) §D.1) → 실패 시 D8

**출력** (v1.3 개정) = `ValidationReport{findings[], coverage[]}`. 결정론.

*findings* — `{severity, rule_id, location, message, fix, line}`
- **정렬 고정**: `stage → rule_id → line → location`. 레지스트리의 `pkgutil` 순회 순서에
  findings 순서가 좌우되면 골든셋 회귀 diff에 노이즈가 생긴다(S1-5)
- `line`은 **정수**다. 문자열이면 `line 10 < line 9`로 정렬돼 결정론적이지만 사람이 읽기엔
  틀린 순서가 나온다. 줄번호를 모르는 finding(L-B 대조 결과)은 `-1`로 앞에 모인다
- lxml `error_log`가 `error.line`을 주므로 L-A는 항상 채울 수 있다

*coverage* (v1.3 신설) — `{rule_id, status(ran|partial|skipped), scope, reason}`

`findings`가 비었다는 사실만으로는 **"검사했고 문제없음"과 "검사하지 못했음"이 구분되지
않는다.** 소비자가 AI이므로 이 차이를 명시적으로 넘긴다 (02 S5 "조용히 통과 금지").
아래가 전부 "통과"로 보이던 문제를 해소한다:

- 미지원 릴리스라 L-A 미실행 · calc 파싱 실패로 일부 스킵 · live DB · render 계층
- 입력 오류로 파이프라인이 멈춰 규칙이 아예 돌지 않은 경우

엔진이 조립한다 — 규칙이 아무 보고도 하지 않으면 `RAN`으로 기록되고,
`ctx.note_skip()`/`note_partial()`을 부르면 그것이 우선한다.
`report.passed`는 "검사한 범위에서 ERROR 없음"이고, "전부 검사했음"은 `fully_covered`다.

## D3.5 규칙 입력 계약 — `ValidationContext` (v1.3 전면 개정)

v1.1은 `check(model)`이었다. **두 가지 이유로 성립하지 않는다:**

1. 모델만 넘기면 트리가 필요한 규칙(L-A · 규칙 ⑥)이 1MB XML을 **각자 재파싱**한다.
   규칙 수에 비례해 파싱이 늘어 AC5(속도)와 정면 충돌한다
2. 트리를 **하나** 넘겨도 부족하다 — 규칙 ⑥-a는 fcp 정규화 **전** 원본을,
   L-A는 정규화 **후** 사본을 봐야 한다 (05 F7 함의 2)

```
ValidationContext
  model              WorkbookModel  (아래 D3.5.1)
  raw_tree           정규화 전 원본        ← 규칙 ⑥-a의 유일한 유효 입력
  normalized_tree()  fcp 정규화 사본(캐시)  ← L-A 입력
  note_skip()/note_partial()               ← coverage 보고 창구
```

- 파싱은 `inspect.load_context()`에서 **파일당 한 번**. 규칙은 재파싱하지 않는다
- 정규화 사본은 처음 요구될 때 한 번 만들고 캐시한다 (1MB 사본은 싸지 않다)
- 규칙은 컨텍스트를 변경하지 않는다. 예외는 보고(note)와 캐시뿐
- fcp 접두사 처리는 `twb_lint/fcp.py` 한 곳에 모은다 — L-A와 규칙 ⑥-a가 **같은 정규식**을
  반대 방향으로 쓰기 때문이다(하나는 지우고, 하나는 읽는다)

규칙이 지켜야 하는 계약은 테스트로 고정돼 있다(`tests/unit/test_rules_contract.py`):
컨텍스트를 받는다 · 원본 트리를 변경하지 않는다 · 입력이 없으면 조용히 통과하지 않는다 ·
⑥-a는 정규화 전 트리를 본다.

### D3.5.1 구조 모델 `WorkbookModel` (v1.1 신설)

규칙 ①②③⑥이 공유한다. **플랫 집합으로는 참조 해소가 불가능하다.**

- 필드 참조는 `[datasource].[Field]`로 **네임스페이스가 있다.** 데이터소스 2개에 동명 필드가
  있으면 플랫 `set[str]`은 구분하지 못해 오통과(FN) 또는 거짓 dangling(FP)을 낸다
- → `datasources: dict[str, DataSource]`, 각 `DataSource`가 `fields`(내부 `name` + `caption` + 타입) ·
  `calcs`(수식 포함)를 갖는다
- **`name` vs `caption` 구분 필수** — calc 수식이 참조하는 것은 caption이 아닌 내부 이름일 수 있다
  (계산필드는 `[Calculation_1234567890]` 형태). caption만 모으면 규칙 ②가 전량 dangling을 뱉는다.
  구현 착수 시 실파일로 확인할 것
- 시트도 worksheet / dashboard / window를 **구분해서** 담는다 (규칙 ③이 링크 방향을 검사해야 함)
- 매니페스트 항목 집합, `version`/`original-version`/`source-build`도 모델에 포함 (규칙 ⑥ 입력)

규칙 3개가 이 모델을 소비하므로 **구현 착수 전에 확정하는 것이 가장 싸다.**

## D3.6 calc·필드참조 수집 표면 (v1.3 신설 — 2026-07-29 실측)

규칙 ①②의 입력 표면을 정하지 않으면 파싱 실패(=WARNING)가 폭증해 게이트가 노이즈가 된다.
표본 9개를 전수 조사해 확정했다.

### 표면 1 — 수식이 들어 있는 곳 (규칙 ①·② 양쪽)

`formula` 속성을 가진 요소는 **`<calculation>` 하나뿐**이다 (9개 파일 4,757회).
그러나 수식은 한 곳 더 있다:

| 위치 | 실측 | 내용 |
|---|---|---|
| `<calculation class='tableau' formula='…'>` | 4,757회 | 계산필드 본체 |
| `<groupfilter function='filter' expression='…'>` | 3회 | **필터 조건식** |

`groupfilter@expression`이 중요하다 — 적지만 A6이 우려한 조합을 **정확히 다 담고 있었다**:

```
// 연차 이월                                    ← // 라인 주석
DATEDIFF(&apos;year&apos;, [연차년월], [Calculation_2403…])=0   ← XML 엔티티 + 함수 + 필드
&#13;&#10;                                        ← 개행이 수치 참조로 인코딩됨
```

→ 수집기는 **주석·문자열·개행**을 반드시 다뤄야 한다. (XML 엔티티는 lxml이 속성값을
읽는 시점에 이미 풀린다 — 수집기에 도달할 때는 실제 따옴표·개행이다.)
구현 방식은 아래 **D3.7**에서 문법 파서가 아닌 어휘 스캐너로 확정했다.

표본에 `<reference-line>`은 없었다. 그러나 XSD에는 존재하므로 **"표본에 없음 ≠ 안 나옴"**으로
다룬다 — 수집기는 표면 목록을 데이터로 갖고, 목록 밖 요소는 침묵한다(추측 금지).

### 표면 2 — 필드를 **직접** 참조하는 곳 (규칙 ②만)

수식이 아니라 참조 문자열이 그대로 들어간다. 빈도순:

```
column@name 795 · column-instance@name 516 · column-instance@column 403 · format@field 302
text@column 144 · groupfilter@member 116 · filter@column 19 · encoding@field 15
```

### ⚠️ 표기가 **두 가지**다 — 규칙 ②의 최대 함정

```
calc 수식 안       [Calculation_2403322100842499]              내부 이름 그대로
워크시트 속성      [federated.1wko…].[usr:Calculation_1737…:qk]  역할 접두 + 집계 접미
```

실측 분포 (9개 파일):

| 자리 | 값 | 횟수 |
|---|---|---|
| 데이터소스 | `federated` 10,045 · `Parameters` 2,135 · `Sheet1*` 107 · `__tableau_internal_object_id__` 42 | |
| 역할 접두 | `none:` 5,109 · (없음) 4,140 · `usr:` 2,725 · `sum:` 312 · `min:` 157 · `mn:`·`yr:`·`cnt:`·`io:`·`attr:` | |
| 종류 접미 | `:nk` 5,204 · (없음) 4,143 · `:qk` 2,643 · `:ok` 558 | |

**정규화 없이 대조하면 규칙 ②가 전량 dangling을 뱉는다.** 접두/접미를 벗기고 내부 이름으로
맞춰야 한다.

특수 네임스페이스 예외도 실측으로 확인됐다 — `[:Measure Names]`가 **1,294회** 나온다.
과거 lint가 정확히 여기서 오탐했다(함정 S9). `Parameters` 데이터소스 2,135회도 마찬가지로
일반 필드 집합에 없다.

### D3.6.1 표기 정규화 계약 — `fieldref.py` (v1.6 — 2026-07-29 실측)

두 표기를 맞추는 일을 모듈 하나(`twb_lint/fieldref.py`)에 가둔다. 규칙 ②와 인스펙터가
**같은 규칙으로** 이름을 만들어야 하므로 양쪽에서 이 모듈을 쓴다.

**결정 1 — 후보를 여러 개 낸다.** `FieldRef.names`는 `(장식 벗긴 이름, 원문)` 순의
튜플이고, **하나라도 맞으면 해소**로 본다. 벗기는 규칙이 어긋났을 때 판정이 틀리는
방향을 거짓양성이 아니라 거짓음성으로 고정하기 위해서다 (AC7 > AC2).

**결정 2 — 역할 접두사를 목록으로 고정하지 않는다.** `^[a-z]{1,8}:(.+):[a-z]{2}$`
형태로 본다. 목록 방식은 미등재 집계 접두사가 하나만 나와도 그 필드가 통째로
dangling이 된다.

**결정 3 — `]]`는 `]`의 이스케이프다** (실측). 필드 이름에 대괄호가 들어가면:

```
이름   [P_Year](복사본)_2403322090242050
표기   [[P_Year]](복사본)_2403322090242050]
```

`\[[^\]]*\]`로 자르면 여기서 잘못 끊겨 존재하지 않는 참조가 만들어진다. calc 추출기·
정규화기·인스펙터 **세 곳의 대괄호 패턴이 같아야 한다.**

**특수 네임스페이스** (대조에서 제외, 실측 근거):

| 사유 | 형태 | 실측 |
|---|---|---|
| `measure-axis` | `[:Measure Names]`·`[:Measure Values]` | 544회 (표본 10개) |
| `placeholder` | `[Multiple Values]` | 158회 |
| `internal-object-id` | `[__tableau_internal_object_id__].[…]` | 26회 |

### D3.6.2 필드 유니버스 — `<column>`만 모으면 안 된다 (v1.7 — 2026-07-29 실측)

Tableau는 **커스터마이즈된 필드만** `<column>`으로 적는다. 손대지 않은 DB 컬럼은
`<column>`이 아예 없다. 참조 해소의 대상 집합은 네 곳에서 모은다:

| 출처 | `FieldDef.origin` | 없으면 |
|---|---|---|
| `<datasource>/<column>` | `column` | — |
| `<metadata-record class='column'>/<local-name>` | `metadata` | 평범한 DB 컬럼이 전부 dangling |
| `<datasource>/<group>` | `group` | 그룹/집합이 dangling |
| `<datasource>/<column-instance>` | `instance` | 집계 인스턴스가 dangling |
| `<datasource-dependencies>/<column @user:unnamed>` | `adhoc` | 임시 계산이 dangling (**D3.6.4**) |

실측 효과 (표본 10개, 참조 16,754건):

| 단계 | 미해소 |
|---|---|
| `<column>`만 | 687 |
| 네 곳 전부 + 인스턴스 번호(`:qk:3`) 처리 | **94** |

### D3.6.3 ⚠️ 정상 파일에도 dangling 참조가 있다 — 규칙 ②는 ERROR를 낼 수 없다 (v1.7)

남은 94건을 추적한 결과 **전부 정상 파일의 실제 잔재 참조**였다. 예: 삭제된 계산필드를
가리키는 `format@field` 규칙이 5회 남아 있고, 그 파일은 Tableau에서 정상적으로 열린다.

표면별 실측 (dangling / 전체):

| 표면 | 비율 |
|---|---|
| `format@field` | 60 / 1,170 |
| `column-instance@name` · `@column` | 9 / 2,462 each |
| `calc@formula` | 8 / 8,310 |
| `encoding@field` | 6 / 58 |
| `filter@column` · `groupfilter@member` · `lod@column` · `computed-sort@using` | **0** |

**결론: 규칙 ②의 심각도를 WARNING으로 내린다.** v1.1 설계는 "예외 목록 밖이면 ERROR"
였으나, 그대로 두면 정상 골든셋 10/10이 ERROR를 뱉어 AC7이 즉시 무너진다.

ERROR 승격은 **라벨링 배치(TODO D1~D4) 이후**로 미룬다 — "이 dangling이 있으면 안 열린다"를
Tableau 실로드로 확인한 표면에 한해 올린다. dangling 0인 표면 4종이 유력한 후보다.

### D3.6.4 임시 계산은 `<datasources>`에 없다 — 규칙 ②·⑪의 거짓양성 (2026-08-05 실측)

선반에서 더블클릭해 그 자리에 만든 계산(**임시 계산**, ad-hoc calculation)은
데이터 패널에 뜨지 않고 `<datasources>`에도 올라가지 않는다. 정의는 **그것을 쓰는
워크시트의 `<datasource-dependencies>` 안에만** 있다:

```xml
<worksheet name='SEC05_재고관리상태_M+1계획'>
  <datasource-dependencies datasource='federated.1z0…'>
    <column caption='"계획"' name='[Calculation_4000054048137217]'
            user:unnamed='SEC05_재고관리상태_M+1계획'>
      <calculation class='tableau' formula='"계획"' />
  …
  <cols>([federated.1z0…].[none:Calculation_4000054048165890:nk]
       / [federated.1z0…].[none:Calculation_4000054048137217:nk])</cols>
```

D3.6.2의 네 곳은 전부 `<datasources>` 아래라 이 정의를 못 본다. 그래서 규칙 ②는
`calc.field_refs`를, 규칙 ⑪은 `shelf.refs`를 **정상 워크북**에 대해 뱉었다
(실측: MA_008 워크북, 임시 계산 4건 → finding 10건). AC7 위반이다.

**표식은 `@user:unnamed`다** — 값은 그 계산을 만든 워크시트 이름이다. 이 속성이 붙은
`<column>`만 유니버스에 더한다. `<datasource-dependencies>`를 통째로 담으면 안 된다 —
나머지는 주 데이터소스 정의의 **사본**이고, 삭제된 필드의 사본이 남아 있으면 진짜
dangling을 놓친다. `_datasource()`가 `.//`를 쓰지 않는 것과 같은 이유다.

## D3.7 calc 수집은 **문법 파서가 아니라 어휘 스캐너**다 (v1.5 — 2026-07-29 실측)

v1.3까지는 `calc/grammar.lark`(Lark 문법)로 수식을 파싱할 계획이었다. 구현 시점에
뒤집었다.

**왜 뒤집었나.** 문법 파서는 *완전해야* 침묵한다. Tableau calc 언어(IF/CASE·LOD·테이블
계산·블록 주석·이스케이프)의 전체 문법을 공개 사양 없이 세우면, 지원하지 못한 구문마다
파싱 실패 WARNING이 난다. 그런데 규칙 ①②가 실제로 소비하는 것은 **"함수 이름"과
"필드 참조" 두 종류의 토큰뿐**이다 — 구문 트리를 쓰지 않는다.

어휘 스캐너는 주석·문자열을 먼저 먹고 그 밖에서 `NAME(`과 `[...]`만 집는다.
**실패할 수 없으므로** 파싱 실패라는 노이즈 클래스 자체가 없다.

**실측 검증** (표본 10개, 수식 5,270건 = `calculation@formula` 5,267 + `groupfilter@expression` 3):

| 값 | 결과 |
|---|---|
| 추출된 함수 | 26종 |
| 218종 화이트리스트 미매칭 | **0건** |
| 파싱 실패 | 구조상 불가 |

즉 이 방식으로 규칙 ①이 정상본에서 침묵한다 (AC7).

**포기한 것.** 인자 개수·타입 검사처럼 구문 트리가 필요한 검증은 이 수집기로 못 한다.
규칙 인벤토리([`06`](./06-rule-candidates.md))에 그런 규칙이 없으므로 지금은 손실이 아니다.
필요해지면 그때 스캐너 **위에** 파서를 얹는다 — 스캐너를 지울 이유는 없다.

키워드 목록(`IF`·`CASE`·`FIXED` 등)이 유일한 판단 지점이다. 넓게 잡으면 미지 함수를
놓치고(거짓음성), 좁게 잡으면 정상 수식에 경고가 난다(거짓양성). **AC7이 우선이라
넓은 쪽**으로 잡았다 (02 S1-6).

## D4. 저장소 구조 (v1.3 — 실제 구조. 스캐폴딩 [`04-scaffolding.md`](./04-scaffolding.md) 반영)

```
src/twb_lint/
  models.py                      Finding · CoverageNote · ValidationReport · WorkbookModel
  config.py                      source-build ↔ XSD/함수목록 매핑
  fcp.py                         [v1.3] _.fcp. 접두사 — L-A와 규칙 ⑥-a가 공유 (D3.5)
  inspect.py                     구조 모델 + 트리 추출 [C2] — 파싱은 여기서 1회
  cli.py                         CLI 어댑터
  io/twb.py  io/twbx.py          파싱·직렬화 / unpack·pack [C1]
  io/safety.py                   [v1.3] 입력 방어 정책 (D9)
  calc/extractor.py              함수·필드참조 어휘 스캐너 (표면 = D3.6, 방식 = D3.7)
  validation/
    context.py                   [v1.3] ValidationContext — 규칙 입력 계약 (D3.5)
    rule.py  registry.py  engine.py   프로토콜 · 자동수집 · 오케스트레이션
    syntactic/xsd.py                  L-A (전처리 3단계 + 심각도 정책)
    semantic/<rule>.py                L-B 규칙당 파일 1개
  data/schemas/                  vendored XSD + 스텁 2개 + NOTICE (Apache-2.0)
  data/functions/                버전별 함수 화이트리스트 JSON (218종)
  data/manifest_gates.json       기능↔매니페스트 대응표 (규칙 ⑥)
  mcp/server.py                  MCP 어댑터 (코어는 MCP 미의존)
tests/
  conftest.py                    [v1.3] 골든셋 경로 외부화 (env, 미설정 시 skip)
  fixtures/builder.py            [v1.3] 최소 .twb 조각 빌더 — 규칙 단위 테스트 입력
  unit/                          스모크 · fcp · safety · 규칙 계약 · vendored 데이터
  golden/                        [v1.3] AC7 회귀 · 주입 검출 (실파일, env 게이트)
tools/vendor_schemas.py          XSD vendoring + 스텁·패치 적용 + 컴파일 검증
tools/scrape_functions.py        화이트리스트 재생성
tools/inject_defects.py          [v1.3] 결함 주입 → 고장본 + 라벨 대장 생성
```

v1.0의 `server/`·`validator/semantic.py`(단일 파일) 안은 폐기 —
규칙당 파일 1개 + 자동수집 레지스트리로 확정됐다(확장성: 파일 추가만으로 규칙 등록).

**테스트 3층 구조** (v1.3): 스모크(부팅) → **규칙 계약·단위**(최소 XML 조각) → 골든셋(실파일).
가운데 층이 비어 있으면 규칙 하나를 고칠 때마다 1MB 실파일로 디버깅하게 된다.

**재사용**: `lxml`·`tableauhyperapi`·`document-api-python`·`Lark`·공식 XSD repo. 신규작성 최소화.

## D5. 골든셋 & AC 목표 (S6 해소 / v1.1 조달 경로 확정)

**정상 대조본 — 확보 완료 (9개)**

실사용 워크북. 전부 `source-build 2026.1.x`, `version='18.1'`.
MA_002 현금흐름 ×7 · MA_004 손익계산서 ×1 · 태블로판차분석 ×1.
L-A 전처리 3단계 적용 후 9/9 통과 확인 ([`05-xsd-spike.md`](./05-xsd-spike.md)).
2026-07-29 vendored XSD(`data/schemas/`) + `twb_lint.fcp`로 **재확인 9/9**.
→ **AC7(거짓양성 0)의 기준 집합.**

⚠️ **표본 편향** (v1.3 기록) — 9개 중 7개가 MA_002의 변형이다. **실제 다양성은 3종**
(현금흐름 · 손익계산서 · 판차분석)이다. "9개에서 ERROR 0건"은 숫자가 주는 인상보다 약한
근거이므로, 새 규칙을 승격할 때 이 한계를 감안한다. 표본 확대가 AC7의 신뢰도를 직접 올린다.

**경로는 저장소에 없다.** 사내 재무 데이터라 커밋할 수 없어 환경변수로 받는다
(`TWB_LINT_GOLDEN_NORMAL`, 미설정 시 해당 테스트 skip — `tests/conftest.py`).
v1.1까지 문서가 "레포 용량" 때문이라고 적었으나 **실제 사유는 기밀이다.**

**고장본 — 주입 방식으로 조달**

과거 실패 기록이 남아 있지 않으므로(고장 파일 미보존), **정상본에 결함을 주입해 생성한다.**
주입 레시피와 기대 라벨은 [`06-rule-candidates.md`](./06-rule-candidates.md) §D에 있다 —
매니페스트 항목 삭제(R1), viewpoint 삭제(R2), 존 name 변조(R3), ds 자식 순서 교체(R4),
`param-domain-type='all'`(R7) 등. 규칙별 ≥3 케이스를 결정론적으로 만들 수 있다.

- 라벨 확정은 **로컬 Tableau Desktop 2026.1 수동 로드** (Cloud REST 검증 사용 불가 — S7)
- 주입 스크립트(`tools/inject_defects.py`)로 골든셋을 **재생성 가능하게** 유지한다
  (`.twbx` 실물 대량 커밋 회피)
- `.hyper`는 주입 대상이 아니다 — `.twb` 엔트리만 교체하고 나머지는 바이트 그대로 복사한다

**v1.3 실행 결과** — 레시피 6종을 표본 1개에 적용해 고장본 6개 + 라벨 대장(`labels.json`)을
생성했다. 사용자 라벨링 배치 전에 **어느 계층이 잡는지**가 이미 측정된다:

| 레시피 | L-A(XSD) | 함의 |
|---|---|---|
| R4 자식 순서 · R7 enum | **검출** (ERROR) | L-A가 담당하는 영역 확인 |
| R1-a · R1-b · R2 · R3 | **통과** | **AC3 무거짓통과의 실증** — L-B 없이는 게이트가 이 파일들을 승인한다 |

`.hyper` 무손실도 6/6 확인했다(주입 전후 바이트 동일).

**AC 목표**

- **AC2**: 골든셋 고장 케이스 **100% 검출**(초기 목표, 골든셋 확장하며 유지).
- **AC3 무거짓통과**: 0 목표. 발생 시 해당 유형 L-B 규칙 추가.
- **AC7 거짓양성**: 정상 9개에서 **ERROR 0건**. WARNING 건수는 기록해 추이 관찰.
  단 표본 편향(3종 다양성)을 감안한다.
- **AC8 `.hyper` 무손실** *(v1.3 신설)*: `unpack → pack` 라운드트립에서 `.hyper` 엔트리가
  **바이트 단위로 동일**해야 한다. 원칙(S1·07 G6)만 있고 측정 기준이 없었다 —
  등가성이 아니라 동일성으로 고정한다. 재압축·재인코딩이 한 번이라도 끼면 추출 데이터가
  조용히 달라진다. 테스트는 있고 `io` 구현 전까지 `xfail`이다.
- **AC5 속도**: `twb_validate` 시간 < E2E의 유의미한 분수. **E2E baseline 실측이 선행 과제**.
  Tableau Desktop 실행이 필요해 사용자 배치에 묶인다 (여전히 미측정).

## D6. 후순위 / 범위 밖 (이번 설계)

- **C4 편집기·C7 저작·C5 쿼리** — 검증기 안정 후 착수. 편집기는 검증기를 게이트로 재사용.
- **C6 E2E 게이트** — 선택, 최종 confirm 전용. render 계층(blank viz·layout) 잔여만 담당.
- **live DB connection** — 오프라인 검증 불가 → 경고만.
- **패키징(Skill/Plugin)** — MCP 코어 안정 후 래핑.

## D7. 검증 방법 (end-to-end)

1. **정상본 회귀 먼저** — 실사용 9개에 ERROR 0건인지 확인(AC7). 여기서 깨지면 규칙을 고친다.
2. 골든셋 고장본 생성(주입 스크립트) → 각 파일 실제 Tableau 로드 실패 라벨 확정.
3. `twb_unpack`→`twb_inspect`→`twb_validate` 파이프라인 실행.
4. findings vs 라벨 대조 → AC2(검출율)·AC3(무거짓통과) 측정.
5. `twb_validate` 시간 vs E2E 시간 벤치 → AC5. (E2E baseline 1회 실측 필요)
6. XSD vendoring 갱신 시 → 스텁·패치 재적용 + 1번 정상본 회귀 재실행.

**순서가 중요하다.** v1.0은 고장본 검출(AC2)부터 봤다. 실측 결과 **정상본 오탐이 먼저 터지는
문제**임이 드러났으므로(전처리 없으면 9/9 실패) 정상본 회귀를 1번으로 올린다.

## D9. 입력 방어 (v1.3 신설)

**이 도구가 먹는 파일은 AI가 생성한 것**이거나 출처를 모르는 것이다. 파서에 그냥 넘기면
XML/ZIP의 고전적 함정이 그대로 열린다. 정책을 io 구현 뒤로 미루면 이미 `etree.parse(path)`가
여기저기 박힌 뒤에 고치게 되므로 **구현 순서를 뒤집어** 먼저 고정했다 (`io/safety.py`).

| 공격 | 방어 |
|---|---|
| XXE (외부 엔티티로 로컬 파일 탈취) | `resolve_entities=False` · `load_dtd=False` · `no_network=True` |
| billion laughs (엔티티 폭탄) | 위와 동일 — 확장하지 않으면 터지지 않는다 |
| 거대 입력 | 파싱 전 크기 상한 (`.twb` 64MB · `.twbx` 512MB) |
| zip slip (`../` 경로 탈출) | 엔트리 경로를 **해석해** 목적지 하위인지 확인 |
| zip bomb | 엔트리 압축비 200배 · 해제 총량 2GB · 엔트리 수 10,000 상한 |

- 파서는 **반드시 `safety.make_parser()`로만** 만든다. 옵션 하나만 빠져도 방어가 무너지는데,
  파서 없이 `etree.parse(path)`를 부르면 기본 파서(엔티티 해석 활성)가 쓰인다
- 상한은 **실측 대비 수십 배**로 잡았다. 정상 파일을 막으면 그 자체가 AC7 위반이다
  (표본 `.twb` 799KB~1281KB)
- 테스트가 실제 billion laughs·XXE 페이로드로 확인한다

### D9.1 unpack의 오류 전달 — `ArchiveError` (v1.4)

io 함수는 실패 시 **`safety.InputError`를 던진다** — `InputProblem`을 실어서다.
반환값으로 문제를 섞지 않는 이유는 io가 MCP 도구에서 **검증과 무관하게** 직접 쓰이기
때문이다. 거기서는 실패가 곧 도구 실패지 finding이 아니다. 하위 예외는
`twbx.ArchiveError`(ZIP)·`twb.MalformedXmlError`(XML)이며, 호출자는 실패 종류를 몰라도
기반 클래스 하나로 잡을 수 있다.

검증 경로에서만 `inspect.load_context()`가 이걸 잡아 문제 목록으로 바꾼다. 그래서
"입력 오류는 예외가 아니라 finding"(02 S5)이 **엔진 경계에서** 그대로 성립한다.

zip bomb 방어는 **2선이다.** `check_zip_entry()`가 보는 `file_size`는 ZIP 헤더 값이라
아카이브 제작자가 거짓말할 수 있다. 그래서 해제 중 **실제로 읽은 바이트**로 총량 상한을
한 번 더 건다 (`_copy_bounded`). 선언 크기만 믿으면 사전 검사를 통과한 폭탄이 그대로 풀린다.

## D8. 후속 조사 — 로더 내장 XSD 역수확 (v1.1 신설)

설치본에 로더가 실제로 쓰는 스키마가 들어 있다:

```
C:\Program Files\Tableau\Tableau 2026.1\bin\res\tablangres.rcc   (26MB, Qt 리소스)
  xs:schema 32블록 · complexType 9474회 · .xsd 59회 — 압축 없이 평문
```

과거 작업 기록(함정 I1)도 *"twb 전체 XSD가 박혀 있음, 역수확 소스로 유용"* 이라고 적고 있다.

GitHub 공개 XSD보다 **설치된 로더의 실제 문법에 가깝다**고 볼 근거가 있다. 여기서
D3 L-A의 결함 3종(스텁·과엄격)과 규칙 ⑥의 매니페스트 대응표 전수 목록을 얻을 수 있다.

- **우선도**: MVP 이후. 단 규칙 ⑥ 대응표가 2쌍에 머물면 검출 범위가 좁아 조기 착수 가치가 있다
- **주의**: 재배포 불가 자산이다. 추출물을 repo에 커밋하지 않는다 —
  대응표 같은 **사실만** 추출해 데이터 파일로 기록한다

**v1.2 재평가 (F7 이후)** — 대상이 좁아졌고 우선도가 내려갔다.

| 이전 | 지금 |
|---|---|
| 매니페스트 대응표 전수 (미지 다수) | **일반 19종의 요소 매핑만** (fcp 계열은 F7이 구조로 해결) |
| 유일한 확장 경로 | 차선책 — 주입 실험 B([`06`](./06-rule-candidates.md) §D.1)가 먼저 |

실험 B는 로드 거부 메시지가 대응 요소를 직접 알려주므로 배치 1회로 최대 20쌍을 얻는다.
**B가 성공하면 D8은 불필요할 수 있다.** 실패하거나 커버리지가 낮을 때만 착수한다.
