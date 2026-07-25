# Tableau 저작 AI — 스캐폴딩 (Scaffolding)

> SOR 문서. 설계 [`03-design.md`](./03-design.md), 인덱스 [`tableau-ai-sor.md`](./tableau-ai-sor.md). 코드 사용법은 루트 [`README.md`](../README.md).

## 문서 관리

| 항목 | 값 |
|---|---|
| 상태 | ✅ 완료 (골격 + stub, 전 검사 green) |
| 버전 | v1.0 (2026-07-25) |
| 다음 | 구현 — L-B MVP 3규칙 + XSD + I/O 실로직 |

---

## 확정 결정

| 항목 | 값 |
|---|---|
| 이름 | `twb-lint` (모듈 `twb_lint`) |
| 구조 | 단일 패키지 + src-layout |
| MCP SDK | 공식 `mcp[cli]` (설치 확인: mcp 1.28.1) |
| 빌드툴 | `uv` (0.10.4) |
| Python | 3.11+ (실행환경 3.14) |
| 품질 | ruff · mypy(strict) · pytest — 전부 green |
| 철학 | **mandatory gate** — `ValidationReport.passed = ERROR 없음` |

## 확장성 3대 메커니즘 (실증됨)

1. **코어↔MCP 분리** — `twb_lint/`는 MCP 미의존. `twb_lint/mcp/server.py`만 어댑터. 코어 순수 import로 `engine.validate` 동작 확인.
2. **규칙 플러그인 레지스트리** — `registry._discover()`가 `syntactic/`·`semantic/` 하위 모듈을 pkgutil로 자동 import. **새 규칙 = 파일 1개 + `@register`, 코어 무수정.** (현재 4규칙이 나열 없이 자동수집됨)
3. **통합 `Finding`/`ValidationReport`** — 전 단계 공용. stage 추가로 L-C(E2E) 확장 가능.

## 생성물

- `pyproject.toml` · `README.md` · `.gitignore`
- `src/twb_lint/` — `models.py`·`config.py`·`inspect.py`·`cli.py` + `io/`·`calc/`·`validation/`(engine·rule·registry·syntactic·semantic)·`data/`·`mcp/`
- `tests/` — `unit/test_smoke.py`(4 pass) + `golden/`(placeholder)
- `tools/` — `scrape_functions.py`·`vendor_schemas.py`(stub)

전체 트리·인터페이스 계약은 플랜 Part IV / 루트 README 참조.

## 검증 (실행 결과)

```
uv sync --extra dev          # OK
uv run pytest -q             # 4 passed
uv run ruff check .          # All checks passed
uv run mypy                  # Success: no issues (25 files)
# MCP 부팅 → tools: twb_inspect, twb_unpack, twb_validate
# registry → calc.field_refs, calc.functions, named.refs, xsd.schema
```

## 다음 (구현 단계)

1. `io/twbx.py`·`io/twb.py`·`inspect.py` 실로직 (unpack/parse/모델추출).
2. `validation/syntactic/xsd.py` — vendored XSD + lxml (`tools/vendor_schemas.py` 먼저).
3. L-B MVP 3규칙 실로직 + `calc/extractor.py` Lark 파싱 + 함수 화이트리스트(`tools/scrape_functions.py`).
4. 골든셋 구축 → AC2/AC3 측정.
