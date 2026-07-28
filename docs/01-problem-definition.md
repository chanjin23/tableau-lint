# Tableau 저작 AI — 문제정의 (Problem Definition)

> SOR 문서. 스펙은 [`02-specification.md`](./02-specification.md), 인덱스는 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 확정 |
| 버전 | v1.1 (2026-07-28) |
| 소유자 | ax3didim@gmail.com |
| 다음 | [스펙](./02-specification.md) → 설계 |
| v1.1 변경 | §2 공식 REST 검증 추가 · §7 XSD 실측 결과 반영 · §8 로더 문법 게이팅 추가 · §9 해소 표기 |

---

> 범위: **문제정의 단계**만. 아키텍처/구현/라이브러리 선택은 여기서 다루지 않는다.

## 1. 배경

Tableau에는 로컬 `.twb/.twbx` 파일을 **저작·편집**해주는 신뢰 가능한 AI가 없다. 현재 AI에 Tableau 파일 작업을 맡기면 자주 파일이 깨지거나 틀린 결과가 나온다.

## 2. 현황 분석 (2026-07)

| 구분 | 대상 | 능력 | 빈틈 |
|---|---|---|---|
| 공식 `tableau/tableau-mcp` | Cloud/Server API | 데이터 쿼리·콘텐츠 탐색·뷰 렌더 (**읽기**) | 워크북 생성/편집 없음, 쓰기 없음 |
| Tableau Agent(Einstein) | Cloud 세션 | 시트 단위 대화형 탐색 | 대시보드 빌드·데이터모델링 불가, 시트간 인식 없음, **버전관리용 독립 파일 생성 안 됨**, 오프라인·무인 자동화 불가 |
| 커뮤니티 MCP (Loki, hetpatel, wjsutton 등) | 주로 REST API | 쿼리·관리·CSV 추출 | 로컬 파일 저작 도구 없음 |

**결론: 로컬 `.twb/.twbx`를 에러 없이 저작·편집하는 도구는 시장에 없다.** = 이 프로젝트가 노리는 빈틈.

### 2.1 추가 확인 (2026-07-28) — 공식 검증 REST API 등장

공식 XSD 레포 README에 명시:

> Tableau Cloud June 2026 / Server 2026.2부터 REST API로 **구문·시맨틱 양쪽** 검증 가능
> (`Validate Workbook`, `Validate Workbook and Upload`).
> *"Semantic validation: Successful semantic validation means that a workbook will open in Tableau."*

공식이 시맨틱 검증 능력을 갖췄다. 다만 **Cloud/Server 온라인 전용**이다.

- 이 프로젝트 요구는 **로컬·오프라인**(§4 확정 요구) → 대체재가 아니다
- 사용자 환경은 **로컬 전용, Cloud 접근 불가**(2026-07-28 확인) → 이용 불가
- 골든셋 라벨링 오라클로 쓸 여지도 같은 이유로 없음 → **라벨링은 로컬 Tableau Desktop 2026.1 수동**

## 3. 근본 원인 (왜 AI가 Tableau 작업을 못하나)

### 3.1 핵심: "2계층 유효성" 문제
Tableau 파일이 열리려면 **두 계층**을 모두 통과해야 하는데, 흔한 XML 검증은 (A)만 본다.

- **(A) 구문 유효성 (syntactic)** — XML well-formed. 파서로 쉽게 검증. **이건 통과해도 안 열리는 경우가 대부분.**
- **(B) 시맨틱 유효성 (semantic)** — Tableau 내부 스키마 + 참조 + 메타/데이터 일관성. **여기서 깨지면 XML 검증 통과해도 로드 실패.** ← 사용자가 겪는 핵심 고통.

### 3.2 (B) 시맨틱 실패 유형 (웹리서치 + 사용자 경험)
1. **스키마/속성 오류** — AI가 넣은 XML 속성이 "살짝 틀림". well-formed지만 Tableau 스키마 위반 → 로드 실패. (실사례: AI 생성 파일, 에러 스크린샷 보여주니 AI가 수정)
2. **참조 무결성 붕괴** — `<datasource-dependencies>`, `<column-instance>`가 `[datasource].[FieldName]`로 필드 참조. 필드 rename/삭제 후 참조 미갱신 → dangling reference → 로드 실패.
3. **ID/이름 링크 불일치** — worksheet↔dashboard, window↔view 이름·GUID 연결이 어긋남.
4. **버전 속성 불일치** — `<workbook version=...>`와 실제 사용 기능 불일치.
5. **메타↔데이터 불일치** — `.twb` 필드 참조와 `.hyper`/`.tde` 스키마 어긋남 → 열려도 렌더 실패.
6. **LLM 환각 문법** — 지원 안 되는 calc field 문법을 생성 (Tableau가 "문법 지원 여부" 확인 요구).

### 3.3 부가 원인
- **도메인 지식 부재** — 위 스키마·문법·구조를 AI가 정확히 모름.
- **문자열 편집** — AI가 XML을 문자열로 조작 (공식 결론: 수동 XML 편집은 최후수단, 극도로 error-prone). 안전한 트리 편집 미사용.

### 3.4 검증 비용 문제 (사용자 실측)
현재 유일하게 믿을 만한 (B) 검증 = **AI가 Tableau를 직접 실행→스크린샷→확인하는 E2E**. 정확하지만 **너무 느림**. 매 편집마다 앱 기동·렌더 비용. → **빠른 결정론적 시맨틱 검증이 E2E를 대체/축소**해야 실용적.

## 4. 해결 대상 (Problem Statement)

> **로컬 `.twb/.twbx` 파일을 대상으로, 사용자가 자연어로 Tableau 작업을 맡기면 (1) 새 저작, (2) 기존 편집/수정, (3) 데이터 쿼리/분석을 — 파일을 깨뜨리지 않고 정확하게 수행하는 도구를 만든다.**

### 확정된 요구 (사용자 답변 기준)
- 대상: **로컬 `.twb/.twbx` 파일** (Cloud/Server API 아님, 오프라인)
- 작업 유형: **저작 + 편집 + 쿼리 전부**
- 실행 호스트: **미정** (Claude Code/Desktop vs 자체 앱 — 스펙 이후 결정)

## 5. 성공 기준 (무엇을 만족해야 "해결"인가)

- **무에러 보장 (2계층)**: 산출 `.twb/.twbx`가 (A)구문 + (B)시맨틱 모두 통과 → Tableau Desktop/Public에서 항상 로드·렌더된다.
- **빠른 시맨틱 검증**: (B)를 E2E 앱실행 없이 결정론적으로 검출. E2E는 최종 confirm용으로만(선택), 매 편집마다 X.
- **참조무결성**: 필드 참조·ID 링크·메타↔hyper 스키마 일관 (끊긴 참조 없음).
- **정확성**: 요청 편집(필드·calc·색/레이아웃·쿼리)이 의도대로 반영, 미지원 calc 문법 배제.
- **재현성**: 같은 요청 → 같은 무에러 산출 (무인/자동화 가능).

### 검증 비용 목표 (사용자 고통 직결)
느린 E2E(앱 실행→스크린샷) 의존을 **빠른 오프라인 검증으로 대체**하는 것이 이 프로젝트의 실용성 핵심. E2E는 fallback/최종 게이트로 격하.

## 6. 비-목표 (이번 문제정의 범위 밖)

- Cloud/Server REST API 연동 (공식 MCP 영역)
- 실시간·고빈도 데이터 스트리밍
- 구현 기술 선택(언어·라이브러리·MCP/Skill/Plugin 형태) — **설계 단계에서 결정**

## 7. 조사결과: 공식 스키마 (2026-07 확인)

**Tableau가 2026-02 공식 XSD 공개** — `tableau/tableau-document-schemas`. 이게 (A)/(B) 경계를 명확히 그어준다.

- **커버 (=A 구문)**: `.twb` 구조 검증. 버전별 `twb_2026.1.0.xsd`, `twb_2026.2.0.xsd` (YYYY_R 명명, TWB version "26.1" ↔ `twb_2026.1.0.xsd`). 표준 XML 검증기로 오프라인 적용 가능.
- **명시적 非커버 (=B 시맨틱, 리포가 직접 경고)** — "구문검증 통과해도 Tableau에서 열린다는 보장 없음":
  1. connection element 속성
  2. **calc field 내용 (함수명·객체 참조)** ← LLM 환각·미지원 문법이 여기
  3. **named workbook content 참조 (탭 이름 등)** ← dangling reference가 여기
  4. `processContents="skip"` 로 표시된 요소
- **`.twbx`(패키지)는 스키마 미지원** — unpack 후 `.twb`만 검증 가능.

### 결정적 함의 (프로젝트 정체성)
> **(A) 구문 검증 = 공식 XSD로 오프라인 해결됨 (재발명 불필요).**
> **(B) 시맨틱 검증 = 공식이 명시적으로 안 하는 영역. "열리는데 안 열리는" 원인 전부 여기. → 이 프로젝트가 만들어야 할 정확한 빈틈.**
> 즉 핵심 산출물 = XSD 위에 얹는 **시맨틱 검증기**(calc 문법·참조무결성·메타↔hyper 대조) + 안전 편집. 이걸로 느린 E2E를 대체.

메타↔hyper 대조는 `tableauhyperapi`의 `Catalog.get_table_definition()`으로 오프라인 가능(확인됨).

### 7.1 실측 검증 (2026-07-28) — 공식 XSD를 그대로는 쓸 수 없다

위 §7은 **조사 결과**였다. 실사용 워크북 9개로 실제로 돌려본 결과
(상세: [`05-xsd-spike.md`](./05-xsd-spike.md)):

> **정상 파일 9개 전부가 공식 XSD를 통과하지 못한다.** 전처리 3단계를 넣어야 9/9 통과한다.

| 결함 | 내용 | 대응 |
|---|---|---|
| XSD 컴파일 불가 | `user`·`xml` 네임스페이스를 `schemaLocation` 없이 import 하고 그 안의 컴포넌트를 참조 | 스텁 스키마 2개 주입 |
| `_.fcp.` 미모델링 | Tableau 하위호환 접두사(`_.fcp.<기능>.true...<이름>`)를 XSD가 모름 → 파일당 48~55건 오류 | 검증 전 접두사 정규화 |
| 과엄격 | `explain-data`가 필수인데 실제 Tableau는 미사용 시 안 씀 → 파일당 1건 | XSD 패치(`minOccurs="0"`) |

**"(A) 구문 검증은 공식 XSD로 해결됨(재발명 불필요)"는 유효하되, 무료는 아니다.**
vendoring이 원본 복사가 아니라 **패치 파이프라인**이 된다.

부수 확인 — `<workbook version>`은 저작 버전이 아니다. Tableau 2026.1이 만든 파일도
`version='18.1'`(= 최소 호환 버전)로 저장된다. 버전↔XSD 매핑은 `source-build`를 기준으로 해야 한다.

## 8. 시맨틱 커버리지 정밀조사 (E2E 완전제거 가능한가?)

XSD 非커버 4항목 + render 계층을 "오프라인 정적검증으로 잡히는 정도"로 매핑. (Tableau **자체 linter 없음** — 커뮤니티 도구 BMB·python calc 추출기만 존재. 우리가 메울 빈틈.)

| 항목 | 오프라인 잡힘 | 방법 | 비고 |
|---|---|---|---|
| calc 함수명·객체 참조 | **높음** | calc 파서 + 버전별 함수 화이트리스트 + 필드 참조 그래프 | "valid-but-won't-open"의 최대 덩어리. Tableau "Invalid Field Formula" 오프라인 재현 |
| named content 참조(탭·window) | **높음** | 트리 순회로 참조명 존재 검사 (순수 그래프) | dangling reference 여기 |
| 메타↔hyper 불일치(embedded) | **높음** | `hyperapi Catalog`로 hyper 스키마 vs `.twb` 필드 대조 | 로컬 embedded extract 한정 |
| connection 속성 | **중간** | 필수속성·타입 정적검사 O / live DB 실제연결 X | embedded=검증가능, live DB=오프라인 불가 |
| `processContents="skip"` 요소 | **낮음** | 구조적으로 불투명(벤더확장/동적) | 드묾. best-effort/E2E |
| **매니페스트 미선언 기능** (2026-07-28 추가) | **높음** | 기능↔`document-format-change-manifest` 항목 대응표 대조 | ↓ 7.2 — **XSD가 원리적으로 못 잡는 영역** |
| **render 런타임** (blank viz, "rendering 실패", device/phone layout) | **불가** | 실제 쿼리실행·마크렌더 필요 | **E2E 전용 잔여영역** |

### 8.1 실측 추가 (2026-07-28) — 로더 문법 ≠ XSD 문법

과거 작업 기록(`old/generate-report` 함정 W2·I7)과 이번 표본 대조로 확인된 실패 클래스:

> **유효 문법 = `version` 선언 × `<document-format-change-manifest>` 항목 집합.**
> 기능을 쓰면서 대응 매니페스트 항목을 선언하지 않으면
> `no declaration found for element '<요소>'`로 **로드 거부**된다.

실측 쌍: `<manual-sort>` ↔ `SortTagCleanup`, `<edit-group-action>` ↔ `GroupAction`+`GroupActionAddRemove`.

**중요**: 공식 XSD는 `manual-sort`를 무조건 허용한다. 즉 매니페스트 없이 쓴 파일은
**(A) 구문 검증을 통과하고 Tableau에서 열리지 않는다.**
"XSD 통과 = (A) 해결"이 아니라 **"XSD를 따르는 것이 오히려 로드 실패를 유발할 수 있다."**
→ L-B 규칙으로 편입 ([`06-rule-candidates.md`](./06-rule-candidates.md) R1).

### 결론: E2E 완전제거는 불가, 그러나 격하 가능
> **로드-실패(안 열림) 클래스는 대부분 오프라인으로 잡힌다** (calc·참조·메타↔hyper = 가장 흔한 원인). → 매 편집 E2E 불필요.
> **render-정확성(열리지만 빈 화면 등)은 E2E 전용** → E2E는 제거 대신 **최종 1회 게이트로 격하**.
> 실용 타겟: **per-edit 빠른 정적검증 + 최종 optional E2E 게이트.** 이게 사용자의 "매번 느린 E2E" 고통을 직접 해소.

## 9. 열린 질문 (설계 단계에서 해소)

- ~~**함수 화이트리스트 확보처**~~ → 설계 D0 해소: help.tableau.com 1회 스크랩 → 버전별 정적 JSON. 파서는 Lark 경량 문법.
- **live DB connection 처리 정책** — 오프라인 검증 불가 영역을 경고로만 낼지, 범위에서 제외할지. → 경고로 확정(D6), 세부 미정.
- ~~**정확성 측정**~~ → 부분 해소: 골든셋 조달 경로 확보. 정상본 9개 실파일 + 규칙 주입으로 고장본 생성([`06-rule-candidates.md`](./06-rule-candidates.md) §D). 라벨링은 로컬 Tableau Desktop 2026.1 수동.
- 저작(맨바닥 생성) 범위 — 어디까지 자동, 어디부터 템플릿. (여전히 미결, 2차)

### 9.1 신규 열린 질문 (2026-07-28)

- **매니페스트 게이트 대응표를 어디까지 확보할 것인가** — 현재 실측 2쌍뿐. 전수 목록의 출처가 없다.
  후보: `tablangres.rcc`(설치본 내장 XSD 32블록) 역수확 → 설계 D8.
- **XSD 패치 관리** — 상류 갱신 시 패치 재적용·회귀를 어떻게 보장할 것인가.
