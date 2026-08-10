# twb-lint

**Tableau `.twb/.twbx` 오프라인 검증 게이트 + 저작 레시피.**

> AI가 Tableau 파일을 만지면 자주 깨진다. twb-lint는 Tableau를 실행하지 않고
> **"열었을 때 빨간 느낌표가 없는가"**를 판정하고(검증),
> UI 조작별 XML 정답지(레시피)로 애초에 안 틀리게 쓴다(저작).

## 왜

실패는 층으로 온다 — 앞 층을 고치기 전에는 뒤 층이 보이지 않는다:

| 층 | 사용자가 보는 것 |
|---|---|
| 1 | 파일이 안 열린다 |
| 2 | 열리는데 필터가 사라졌다 — 조용히 틀린 숫자 |
| 3 | 열리는데 데이터가 하나도 안 나온다 |
| 4 | 열리는데 빨간 느낌표 |

공식 XSD는 구문만 본다 — 이 4층은 전부 **시맨틱** 영역이고, 그 빈틈이 twb-lint다.

## 상태

- **규칙 11종 가동** · 정상 실파일 61개 ERROR 0 · 주입 결함 6종 중 5종 차단
- 심각도 원칙: **확신할 때만 ERROR**(층 1은 막는다) · 나머지는 WARNING(층 2~4는 말한다)
- 그래서 `passed=true`는 "괜찮다"가 아니다 — **findings를 읽는다**
- 대상: **Tableau 2026.1 · 로컬 오프라인**

## 설치

```bash
uv sync
# uv가 차단된 머신: python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
```

## 사용

```bash
uv run twb-lint validate path/to/workbook.twbx   # CLI
uv run twb-lint-mcp                              # MCP stdio 서버
```

MCP 등록 (Claude Code):

```bash
claude mcp add twb-lint -- uv run --directory /path/to/tableau-lint twb-lint-mcp
```

| MCP 도구 | 하는 일 |
|---|---|
| `twb_validate` | 게이트 판정 — `passed=false`면 내보내지 않는다 |
| `twb_inspect` | 판정 없이 구조(필드·시트·버전)만 추출 — 편집 전 정찰 |
| `twb_unpack` | `.twbx`를 풀어 `.twb`를 꺼낸다 |

## XML을 쓸 때 — 저작 레시피

검증은 사후다. 만들 때는 [`docs/recipes/`](./docs/recipes)의 **조작별 실측 정답지**를 따른다:

```
1. docs/recipes/README.md 매핑표에서 작업 → 레시피 조회
2. 레시피대로 XML 작성 (불변 조건·동반 변경 포함)
3. twb_validate 통과 + findings 확인
4. (최종 1회) Tableau에서 열어 재저장 diff 확인
```

매핑표에 없는 작업은 지어내지 않는다 — 미관찰로 기록한다.

## 더 알아보기

| 문서 | 내용 |
|---|---|
| [`docs/09-usage.md`](./docs/09-usage.md) | **사용 상세** — MCP 도구 스펙·편집 왕복·한계·규칙 추가법 |
| [`docs/01-problem-definition.md`](./docs/01-problem-definition.md) | 무엇을 판정하는가 (T1~T4 · 실패 4층) |
| [`docs/08-authoring-recipes.md`](./docs/08-authoring-recipes.md) | 저작 레시피 문제정의 |
| [`docs/07-implementation-guide.md`](./docs/07-implementation-guide.md) | 구현 함정 G1~G10 · 검증 파이프라인 |
| [`docs/tableau-ai-sor.md`](./docs/tableau-ai-sor.md) | 문서 전체 인덱스 (SOR) |
