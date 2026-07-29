# Tableau 저작 AI — 설계 (Design)

> SOR 문서. 문제정의 [`01-problem-definition.md`](./01-problem-definition.md), 스펙 [`02-specification.md`](./02-specification.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 확정 |
| 버전 | v1.2 (2026-07-29) |
| 소유자 | ax3didim@gmail.com |
| 전제 | [문제정의](./01-problem-definition.md)·[스펙](./02-specification.md) 확정 |
| 다음 | 구현 (MVP) |
| v1.1 변경 | D3 L-A 전처리 3단계·버전키 정정 · L-B 규칙 ⑥ 신설·③ 구체화 · D3.5 구조 모델 신설 · D4 실제 구조 반영 · D5 골든셋 조달 · D8 신설 |
| v1.2 변경 | 규칙 ⑥을 ⑥-a(fcp·표 없음)/⑥-b(일반·표 필요)로 분리 · D8 우선도 하향 (근거 05 F7) |
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

**L-B 시맨틱 (6규칙 — MVP는 ①②③⑥, ④⑤ 2차)**

1. **[MVP] calc 함수 화이트리스트** — Lark로 calc 내 함수토큰 추출 → 버전별 `functions_<ver>.json` 대조.
   - **심각도 = WARNING** (S1-6): 목록에 없음 = 우리 목록의 공백일 수 있다. ERROR로 막지 않는다
   - 파싱 실패 시 해당 calc의 하위 검사를 스킵하고 그 사실을 WARNING으로 보고
2. **[MVP] calc 필드참조 해소** — `[Field]`·`[ds].[Field]` 참조 추출 → 데이터소스별 필드/calc 집합 대조.
   - **특수 네임스페이스 예외 필수**: `[:Measure Names]`·`[:Measure Values]`·`[Parameters].[…]`·
     집합/그룹/bin/계층. 과거 lint가 `[:Measure Names]`에서 오탐한 실측 이력이 있다(함정 S9)
   - 해소 실패가 예외 목록 밖이면 ERROR, 예외 후보가 의심되면 WARNING
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

**출력** = `findings[]`: `{severity, rule, location(xpath/line), cause, fix제안}`. 결정론.
- **정렬 고정** (v1.1): `stage → rule_id → location` 순. 레지스트리의 `pkgutil` 순회 순서에
  findings 순서가 좌우되면 골든셋 회귀 diff에 노이즈가 생긴다(S1-5).

## D3.5 구조 모델 (v1.1 신설)

규칙 ①②③⑥이 공유하는 `WorkbookModel`. **플랫 집합으로는 참조 해소가 불가능하다.**

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

## D4. 저장소 구조 (v1.1 — 실제 구조. 스캐폴딩 [`04-scaffolding.md`](./04-scaffolding.md) 반영)

```
src/twb_lint/
  models.py                      Finding · ValidationReport · WorkbookModel (D3.5)
  config.py                      source-build ↔ XSD/함수목록 매핑
  inspect.py                     구조 모델 추출 [C2]
  cli.py                         CLI 어댑터
  io/twb.py  io/twbx.py          파싱·직렬화 / unpack·pack [C1]
  calc/grammar.lark  extractor.py  Lark 문법 + 함수·필드참조 추출
  validation/
    rule.py  registry.py  engine.py   프로토콜 · 자동수집 · 오케스트레이션
    syntactic/xsd.py                  L-A (전처리 3단계 포함)
    semantic/<rule>.py                L-B 규칙당 파일 1개
  data/schemas/                  vendored XSD + 스텁 2개 (user·xml)
  data/functions/                버전별 함수 화이트리스트 JSON
  data/manifest_gates.json       기능↔매니페스트 대응표 (규칙 ⑥, v1.1 신설)
  mcp/server.py                  MCP 어댑터 (코어는 MCP 미의존)
tests/golden/                    골든셋 (정상 9개 + 주입 고장본)
tools/vendor_schemas.py          XSD vendoring + 스텁·패치 적용
tools/scrape_functions.py        화이트리스트 재생성
```

v1.0의 `server/`·`validator/semantic.py`(단일 파일) 안은 폐기 —
규칙당 파일 1개 + 자동수집 레지스트리로 확정됐다(확장성: 파일 추가만으로 규칙 등록).

**재사용**: `lxml`·`tableauhyperapi`·`document-api-python`·`Lark`·공식 XSD repo. 신규작성 최소화.

## D5. 골든셋 & AC 목표 (S6 해소 / v1.1 조달 경로 확정)

**정상 대조본 — 확보 완료 (9개)**

실사용 워크북. 전부 `source-build 2026.1.x`, `version='18.1'`.
MA_002 현금흐름 ×7 · MA_004 손익계산서 ×1 · 태블로판차분석 ×1.
L-A 전처리 3단계 적용 후 9/9 통과 확인 ([`05-xsd-spike.md`](./05-xsd-spike.md)).
→ **AC7(거짓양성 0)의 기준 집합.**

**고장본 — 주입 방식으로 조달**

과거 실패 기록이 남아 있지 않으므로(고장 파일 미보존), **정상본에 결함을 주입해 생성한다.**
주입 레시피와 기대 라벨은 [`06-rule-candidates.md`](./06-rule-candidates.md) §D에 있다 —
매니페스트 항목 삭제(R1), viewpoint 삭제(R2), 존 name 변조(R3), ds 자식 순서 교체(R4),
`param-domain-type='all'`(R7) 등. 규칙별 ≥3 케이스를 결정론적으로 만들 수 있다.

- 라벨 확정은 **로컬 Tableau Desktop 2026.1 수동 로드** (Cloud REST 검증 사용 불가 — S7)
- 주입 스크립트를 `tests/golden/`에 두어 골든셋을 **재생성 가능하게** 유지한다
  (`.twbx` 실물 대량 커밋 회피 = 레포 용량 문제 해소)
- `.hyper`는 주입 대상이 아니므로 정상본 1개만 재사용

**AC 목표**

- **AC2**: 골든셋 고장 케이스 **100% 검출**(초기 목표, 골든셋 확장하며 유지).
- **AC3 무거짓통과**: 0 목표. 발생 시 해당 유형 L-B 규칙 추가.
- **AC7 거짓양성**: 정상 9개에서 **ERROR 0건**. WARNING 건수는 기록해 추이 관찰.
- **AC5 속도**: `twb_validate` 시간 < E2E의 유의미한 분수. **E2E baseline 실측이 선행 과제**(현재 없음).

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
