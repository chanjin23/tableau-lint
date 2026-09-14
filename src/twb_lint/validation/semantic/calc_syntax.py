"""L-B rule ⑯: calc 수식의 **구조 문법**.

규칙 ①(`calc.functions`)과 묻는 것이 다르다 — ①은 *"그 이름의 함수가 있는가"*,
⑯은 *"문법이 성립하는가"*다. 이름이 전부 실재해도 괄호가 안 닫히면 그 계산필드는
**오류 상태**가 되고, 그 필드를 쓰는 시트가 빈 화면이 된다.

```
SUM([매출]) / SUM([수량]          괄호가 안 닫힘
IF [A] > 0 THEN 1 ELSE 0         END 누락
{FIXED [지역] : SUM([매출])       LOD 중괄호 누락
```

**WARNING이다** (02 S1-6). 수식은 XML 속성값이라 문법이 깨져도 파일은 열린다 —
Tableau가 그 필드에 빨간 느낌표를 단다(층 4 = T2). 대신 조용하지 않다: 그 필드에
의존하는 시트가 통째로 비므로 화면이 사라진 것처럼 보인다.

**이 규칙의 고객은 남의 파일이 아니라 우리 저작본이다.** Tableau 편집기를 통과한
수식만 저장되므로 정상 워크북에는 문법 오류가 원리적으로 없다 — 수식을 손으로 쓰는
것은 `/author-loop`뿐이다 (01 v2.0: *위험은 편집이 아니라 생성에 있다*).

그래서 근거의 절반은 성격이 다르다:

| | 근거 |
|---|---|
| 거짓양성 없음 (AC7) | 정상본 138개 · 수식 **85,316건**에서 위반 **0건** |
| 검출 가치 (AC2) | 주입 레시피 R30. 정상본은 위반 표본을 줄 수 없다 |

구현은 **문법 파서가 아니라 스캐너 위의 카운터**다 (03 D3.7이 예고한 자리).
구문 트리를 세우지 않으므로 지원 못 한 구문마다 파싱 실패가 나는 노이즈 클래스가
없다 — 정상본 85,316건 침묵이 그것을 실측으로 보인다.
"""

from __future__ import annotations

from typing import Any

from twb_lint.calc.extractor import CalcStructure, formulas_in, structure
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_FINDINGS = 200
"""보고 상한. 자른 사실은 `note_partial`로 보고한다 (02 S5)."""


@register
class CalcSyntaxRule(RuleBase):
    id = "calc.syntax"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 수식 문법을 검사하지 못했다")
            return []

        findings: list[Finding] = []
        for el, formula in formulas_in(ctx.raw_tree):
            problem = _first_problem(structure(formula))
            if problem is None:
                continue
            message, fix = problem
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(el),
                    line=el.sourceline,
                    message=(
                        f"{_label(el)} 수식의 문법이 깨졌다 — {message}. "
                        "Tableau가 이 계산필드를 **오류 상태**로 표시하고, "
                        "이 필드를 쓰는 시트가 빈 화면이 된다"
                    ),
                    fix=fix,
                )
            )

        if len(findings) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"문법 위반 {len(findings)}건 중 앞 {MAX_FINDINGS}건만 보고한다",
                scope="calc-syntax",
            )
            findings = findings[:MAX_FINDINGS]
        return findings


def _first_problem(s: CalcStructure) -> tuple[str, str] | None:
    """가장 근본적인 문제 **하나만** 돌려준다.

    괄호가 깨진 수식은 `END` 짝도 대개 같이 어긋난다. 한 수식에서 3건을 뱉으면
    사람이 어디부터 고쳐야 할지 알 수 없다 — 컴파일러가 첫 구문 오류만 내는 것과
    같은 이유로 우선순위를 고정한다.
    """
    if s.paren_underflow:
        return ("여는 `(` 없이 `)`가 나온다", "짝 없는 `)`를 지우거나 앞에 `(`를 넣는다.")
    if s.paren_depth > 0:
        return (
            f"`(` {s.paren_depth}개가 닫히지 않았다",
            f"수식 끝에 `)` {s.paren_depth}개를 더한다.",
        )
    if s.brace_depth > 0:
        return (
            f"LOD 식의 `{{` {s.brace_depth}개가 닫히지 않았다",
            f"`}}` {s.brace_depth}개를 더한다 — `{{FIXED [차원] : SUM([측정값])}}`.",
        )
    if s.brace_depth < 0:
        return ("여는 `{` 없이 `}`가 나온다", "짝 없는 `}`를 지운다.")
    if s.opens != s.ends:
        blocks = " + ".join(
            part
            for part in (
                f"IF {s.ifs}개" if s.ifs else "",
                f"CASE {s.cases}개" if s.cases else "",
            )
            if part
        )
        if s.opens > s.ends:
            return (
                f"{blocks or '블록'}에 `END`가 모자란다 ({s.opens}개 필요, {s.ends}개 있음)",
                f"`END`를 {s.opens - s.ends}개 더한다 — `IF`·`CASE`는 각각 `END`로 닫는다.",
            )
        return (
            f"`END`가 남는다 ({s.opens}개 필요, {s.ends}개 있음)",
            f"남는 `END` {s.ends - s.opens}개를 지운다.",
        )
    if s.ifs and not s.thens:
        return ("`IF`에 `THEN`이 없다", "`IF <조건> THEN <값> ELSE <값> END` 꼴로 쓴다.")
    if s.cases and not s.whens:
        return (
            "`CASE`에 `WHEN`이 없다",
            "`CASE <식> WHEN <값> THEN <값> ELSE <값> END` 꼴로 쓴다.",
        )
    if s.thens and not s.opens:
        return (
            "`IF`·`CASE` 없이 `THEN`이 나온다",
            "블록을 여는 `IF` 또는 `CASE`를 앞에 넣는다.",
        )
    return None


def _label(el: Any) -> str:
    """사람이 찾을 수 있는 이름. `<calculation>`의 이름은 부모 `<column>`이 갖는다."""
    parent = el.getparent()
    if parent is not None:
        name = parent.get("caption") or parent.get("name")
        if name:
            return f"계산필드 `{name}`의"
    return "계산"


def _path_of(el: Any) -> str:
    """요소의 xpath. L-A·규칙 ②의 `location`과 같은 표기를 쓴다."""
    return str(el.getroottree().getpath(el))
