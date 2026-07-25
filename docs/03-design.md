# Tableau 저작 AI — 설계 (Design)

> SOR 문서. 문제정의 [`01-problem-definition.md`](./01-problem-definition.md), 스펙 [`02-specification.md`](./02-specification.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 확정 |
| 버전 | v1.0 (2026-07-25) |
| 소유자 | ax3didim@gmail.com |
| 전제 | [문제정의](./01-problem-definition.md)·[스펙](./02-specification.md) 확정 |
| 다음 | 구현 (MVP) |

---

> **Context**: 스펙 확정 후 설계 착수. 사용자 확정 = **집중점 = 검증기(C3-B)**, **패키징 = MCP 코어**. 목표 = 공식 XSD 위에 시맨틱 검증기를 얹어 "구문통과·의미실패(안 열림)" 파일을 오프라인·빠르게 사전차단 → 사용자의 느린 E2E를 대체. 편집/저작/쿼리는 검증기 위에 얹는 후순위.

## D0. 결정 요약 (S6 해소)

| 미결 | 결정 |
|---|---|
| 패키징/호스트 | **Python MCP 서버** (코어, 호스트 독립). deps 전부 Python이라 자연스러움 |
| calc 파서 | 기존 라이브러리 없음 → **Lark 경량 문법**(함수호출·필드참조 추출 전용, 평가기 아님) |
| 함수 화이트리스트 | 공식 JSON 없음 → help.tableau.com 1회 스크랩→**버전별 정적 JSON을 repo 유지** |
| MVP 집중 | **C1 unpack + C2 inspect + C3 검증기(2계층)**. 편집/저작/쿼리 후순위 |
| L-B MVP 범위 | **고가치 3규칙 먼저**: ①함수 화이트리스트 ②필드참조 해소 ③named 참조무결성. ④메타↔hyper·⑤connection = 2차 |

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

**L-A 구문 (공식 XSD)**
- `tableau/tableau-document-schemas` XSD를 repo에 vendoring.
- `.twb`의 `<workbook version>` 파싱 → 버전 매칭 XSD 선택(`26.1`→`twb_2026.1.0.xsd`) → `lxml` XMLSchema 검증.
- 미지원 버전 → 명시 경고(조용히 통과 금지).

**L-B 시맨틱 (5규칙 — MVP는 ①②③ 먼저, ④⑤ 2차)**
1. **[MVP] calc 함수 화이트리스트** — Lark로 calc 내 함수토큰 추출 → 버전별 `functions_<ver>.json` 대조. 미지원/환각 함수 flag.
2. **[MVP] calc 필드참조 해소** — Lark로 `[Field]`·`[ds].[Field]` 참조 추출 → datasource 필드/calc 집합 존재 확인. dangling flag.
3. **[MVP] named-content 참조무결성** — worksheet↔dashboard↔window 이름/GUID 트리 순회 대조. 끊긴 링크 flag.
4. **[2차] 메타↔hyper 대조** — `hyperapi Catalog.get_table_definition()` vs `.twb` 필드/타입. 불일치 flag. (embedded extract 한정)
5. **[2차] connection 필수속성** — 정적 규칙셋으로 필수속성·타입 검사. live DB 실연결은 "미검증" 경고.

**출력** = `findings[]`: `{severity, rule, location(xpath/line), cause, fix제안}`. 결정론.

## D4. 저장소 구조 (예시)

- `server/` — MCP 진입점 + 도구 등록
- `validator/xsd.py` — L-A (버전매칭 + lxml)
- `validator/semantic.py` — L-B 5규칙
- `validator/calc/` — Lark 문법 + 추출기
- `schemas/` — vendored XSD (`twb_2026.1.0.xsd` 등)
- `data/functions_<ver>.json` — 함수 화이트리스트
- `io/twbx.py` — unpack/pack (C1)
- `inspect.py` — 구조 모델 (C2)
- `tests/golden/` — 골든셋 (정상+고장 쌍)
- `tools/scrape_functions.py` — 화이트리스트 재생성 스크립트

**재사용**: `lxml`·`tableauhyperapi`·`document-api-python`·`Lark`·공식 XSD repo. 신규작성 최소화.

## D5. 골든셋 & AC 목표 (S6 해소)

- **골든셋**: L-B 규칙별 고장 케이스 각 ≥3 (MVP 우선 = 환각함수·참조끊김·named불일치; 2차 = 메타불일치·connection누락) + 정상 대조본. 각 고장파일은 **실제 Tableau에서 안 열림 검증**(라벨 신뢰성 확보).
- **AC2**: L-B가 골든셋 고장 케이스 **100% 검출**(초기 목표, 골든셋 확장하며 유지).
- **AC3 무거짓통과**: 검증 통과인데 실제 로드 실패 = 치명결함, 0 목표. 발생 시 해당 유형 L-B 규칙 추가.
- **AC5 속도**: `twb_validate` 시간 < E2E(앱기동·렌더)의 유의미한 분수(벤치 후 목표배수 확정).

## D6. 후순위 / 범위 밖 (이번 설계)

- **C4 편집기·C7 저작·C5 쿼리** — 검증기 안정 후 착수. 편집기는 검증기를 게이트로 재사용.
- **C6 E2E 게이트** — 선택, 최종 confirm 전용. render 계층(blank viz·layout) 잔여만 담당.
- **live DB connection** — 오프라인 검증 불가 → 경고만.
- **패키징(Skill/Plugin)** — MCP 코어 안정 후 래핑.

## D7. 검증 방법 (end-to-end)

1. 골든셋 준비 → 각 고장파일 실제 Tableau 로드 실패 / 정상본 성공 라벨 확정.
2. `twb_unpack`→`twb_inspect`→`twb_validate` 파이프라인 실행.
3. findings vs 라벨 대조 → AC2(검출율)·AC3(무거짓통과) 측정.
4. `twb_validate` 시간 vs E2E 시간 벤치 → AC5.
5. 신버전 TWB 들어오면 `scrape_functions.py` + XSD vendoring 갱신 후 회귀.
