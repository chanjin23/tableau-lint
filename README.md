# twb-lint

**Tableau `.twb/.twbx` 파일을 위한 필수 오프라인 검증 게이트.**

> 철학: **모든 Tableau 산출물(AI 저작·편집 포함)은 twb-lint 게이트를 무조건 통과해야 한다.**
> XML이 well-formed여도 Tableau가 파일을 못 여는 "시맨틱 실패"를 앱 실행 없이 빠르게 잡아, 느린 E2E(앱 실행→스크린샷) 검증을 대체한다.

## 왜?

Tableau 파일이 열리려면 두 계층을 모두 통과해야 한다:

- **(A) 구문(syntactic)** — XML well-formed + 공식 XSD. 통과해도 안 열리는 경우가 대부분.
- **(B) 시맨틱(semantic)** — calc 함수·필드 참조·named 참조·메타↔hyper 일관성. 공식 XSD가 **명시적으로 검증하지 않는** 영역. "열리는데 안 열리는" 원인 전부 여기.

twb-lint = 공식 XSD(A) 위에 **(B) 시맨틱 검증기**를 얹은 것.

배경 문서: [`docs/`](./docs) (문제정의·스펙·설계).

## 상태

**스캐폴딩 단계** — 골격 + stub. 실제 검증 로직은 구현 단계에서 채운다.

MVP 검증 규칙 (고가치 3):
1. `calc.functions` — calc 내 미지원/환각 함수 (함수 화이트리스트)
2. `calc.field_refs` — calc 필드 참조 dangling 해소
3. `named.refs` — worksheet↔dashboard↔window 참조 무결성

2차: `meta.hyper`(메타↔hyper 대조, `[hyper]` extra), `connection.attrs`.

## 설치

```bash
uv sync                 # 런타임 + dev
uv sync --extra hyper   # rule ④용 hyperapi 포함 (2차)
```

## 사용

```bash
# MCP stdio 서버 (Claude Code/Desktop/자체앱)
uv run twb-lint-mcp

# CLI
uv run twb-lint validate path/to/workbook.twbx
```

MCP 도구: `twb_unpack` · `twb_inspect` · `twb_validate`.

## 확장 (규칙 추가)

새 시맨틱 규칙 = **파일 1개 추가, 코어 무수정**:

```python
# src/twb_lint/validation/semantic/my_rule.py
from twb_lint.models import Finding, Severity, WorkbookModel
from twb_lint.validation.rule import RuleBase, Stage
from twb_lint.validation.registry import register


@register
class MyRule(RuleBase):
    id = "my.rule"
    stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:
        return []  # findings 반환
```

레지스트리가 `semantic/`·`syntactic/` 하위 모듈을 자동 수집한다.

## 아키텍처

- `twb_lint/` — 순수 코어 라이브러리 (**MCP를 모름**). CLI·Skill·자체앱이 그대로 import.
- `twb_lint/mcp/` — 얇은 MCP 어댑터.
- `ValidationReport.passed = ERROR 없음` = mandatory gate 판정.
