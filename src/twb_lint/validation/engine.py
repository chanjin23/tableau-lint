"""검증 오케스트레이션 — 입력점검 → unpack → inspect → 규칙 순회 → ValidationReport.

mandatory gate: 반환된 리포트의 `passed`가 최종 판정.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from twb_lint import inspect as inspector
from twb_lint.io import safety
from twb_lint.models import (
    CoverageNote,
    CoverageStatus,
    Finding,
    Severity,
    ValidationReport,
)
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import all_rules
from twb_lint.validation.rule import Rule, Stage

# 엔진이 도는 단계 순서 (입력 → 구문 → 시맨틱).
_STAGE_ORDER = (Stage.INPUT, Stage.SYNTACTIC, Stage.SEMANTIC)

INPUT_RULE_ID = "input.readable"
"""입력 점검 결과가 다는 rule_id. 규칙 파일이 없는 유일한 검사다 — 소유자는 엔진이다
(docs/validation/rule.py `Stage.INPUT` 주석 참조)."""


def _input_findings(problems: Sequence[safety.InputProblem]) -> list[Finding]:
    """`io.safety`의 문제 보고를 finding으로 번역한다.

    전부 ERROR다. 파일을 읽지 못하는 것은 "우리 지식의 공백"이 아니라 확정된 사실이라
    S1-6(확신할 때만 ERROR)에 정확히 부합한다.
    """
    return [
        Finding(
            severity=Severity.ERROR,
            rule_id=INPUT_RULE_ID,
            location=str(p.kind),
            message=p.detail,
            fix=p.fix,
        )
        for p in problems
    ]


def _skipped_coverage(reason: str) -> tuple[CoverageNote, ...]:
    """입력 단계에서 멈췄을 때, 돌지 못한 규칙 전부를 SKIPPED로 기록한다.

    이걸 빼면 리포트가 "ERROR 1건 + 나머지 침묵"이 되어 **나머지 규칙이 통과한 것처럼
    보인다.** 실제로는 아예 돌지 않았다 (02 S5).
    """
    return tuple(
        sorted(
            (
                CoverageNote(rule_id=r.id, status=CoverageStatus.SKIPPED, reason=reason)
                for r in all_rules()
            ),
            key=lambda c: c.rule_id,
        )
    )


def validate_model(ctx: ValidationContext, rules: Sequence[Rule] | None = None) -> ValidationReport:
    """이미 만들어진 컨텍스트를 규칙에 통과시킨다.

    findings 순서는 **`stage → rule_id → line → location`으로 고정**한다
    (docs/03-design.md D3). 레지스트리는 `pkgutil` 순회로 규칙을 모으므로 정렬하지 않으면
    파일시스템 순서가 출력에 새고, 골든셋 회귀 diff에 노이즈가 생긴다 (결정론 = 02 S1-5).

    **엔진이 정렬을 보장하므로 개별 규칙은 반환 순서를 신경 쓰지 않아도 된다.**

    coverage도 여기서 조립한다 — 규칙이 아무 보고도 하지 않으면 `RAN`으로 기록된다.

    Args:
        ctx: 검사 대상 컨텍스트 (모델 + 트리 + 보고 창구).
        rules: 사용할 규칙 (기본값 = 레지스트리 전체). 테스트에서 주입한다.
    """
    findings: list[Finding] = []
    coverage: list[CoverageNote] = []
    by_stage: dict[Stage, list[Rule]] = {stage: [] for stage in _STAGE_ORDER}
    for rule in rules if rules is not None else all_rules():
        by_stage.setdefault(rule.stage, []).append(rule)

    # _STAGE_ORDER에 없는 단계(향후 L-C E2E 등)가 조용히 누락되지 않게 뒤에 붙인다.
    extra = sorted(s for s in by_stage if s not in _STAGE_ORDER)
    for stage in (*_STAGE_ORDER, *extra):
        stage_findings: list[Finding] = []
        for rule in sorted(by_stage.get(stage, []), key=lambda r: r.id):
            stage_findings.extend(rule.check(ctx))
            notes = ctx.notes_for(rule.id)
            coverage.extend(
                notes or [CoverageNote(rule_id=rule.id, status=CoverageStatus.RAN)]
            )
        stage_findings.sort(key=lambda f: f.sort_key)
        findings.extend(stage_findings)

    coverage.sort(key=lambda c: (c.rule_id, c.scope))
    return ValidationReport(findings=tuple(findings), coverage=tuple(coverage))


def validate(path: str | Path) -> ValidationReport:
    """파일 경로를 받아 전체 검증 파이프라인을 실행한다.

    **입력 오류는 예외가 아니라 ERROR finding이다** (02 S5). 호출자가 try/except와
    게이트 판정을 따로 만들 필요가 없도록 판정 경로를 하나로 유지한다.
    """
    source = Path(path)

    problems = safety.check_source(source)
    if problems:
        return ValidationReport(
            findings=tuple(_input_findings(problems)),
            coverage=_skipped_coverage("입력 파일을 읽지 못해 검증을 시작하지 못했다"),
        )

    with tempfile.TemporaryDirectory(prefix="twb_lint_") as tmp:
        ctx, load_problems = inspector.load_context(source, Path(tmp))
        if load_problems:
            return ValidationReport(
                findings=tuple(_input_findings(load_problems)),
                coverage=_skipped_coverage("입력 파일을 열지 못해 검증을 시작하지 못했다"),
            )
        return validate_model(ctx)
