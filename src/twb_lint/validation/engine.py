"""검증 오케스트레이션 — unpack → inspect → 규칙 순회 → ValidationReport.

mandatory gate: 반환된 리포트의 `passed`가 최종 판정.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from twb_lint import inspect as inspector
from twb_lint.models import Finding, ValidationReport, WorkbookModel
from twb_lint.validation.registry import all_rules
from twb_lint.validation.rule import Rule, Stage

# 엔진이 도는 단계 순서 (구문 먼저, 시맨틱 다음).
_STAGE_ORDER = (Stage.SYNTACTIC, Stage.SEMANTIC)


def validate_model(model: WorkbookModel) -> ValidationReport:
    """이미 추출된 모델을 규칙에 통과시킨다."""
    findings: list[Finding] = []
    by_stage: dict[Stage, list[Rule]] = {stage: [] for stage in _STAGE_ORDER}
    for rule in all_rules():
        by_stage.setdefault(rule.stage, []).append(rule)
    for stage in _STAGE_ORDER:
        for rule in by_stage.get(stage, []):
            findings.extend(rule.check(model))
    return ValidationReport(findings=tuple(findings))


def validate(path: str | Path) -> ValidationReport:
    """파일 경로를 받아 전체 검증 파이프라인을 실행한다."""
    source = Path(path)
    with tempfile.TemporaryDirectory(prefix="twb_lint_") as tmp:
        model = inspector.inspect(source, Path(tmp))
        return validate_model(model)
