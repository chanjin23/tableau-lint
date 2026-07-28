"""검증 오케스트레이션 — unpack → inspect → 규칙 순회 → ValidationReport.

mandatory gate: 반환된 리포트의 `passed`가 최종 판정.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from twb_lint import inspect as inspector
from twb_lint.models import Finding, ValidationReport, WorkbookModel
from twb_lint.validation.registry import all_rules
from twb_lint.validation.rule import Rule, Stage

# 엔진이 도는 단계 순서 (구문 먼저, 시맨틱 다음).
_STAGE_ORDER = (Stage.SYNTACTIC, Stage.SEMANTIC)


def validate_model(model: WorkbookModel, rules: Sequence[Rule] | None = None) -> ValidationReport:
    """이미 추출된 모델을 규칙에 통과시킨다.

    findings 순서는 **`stage → rule_id → location`으로 고정**한다 (docs/03-design.md D3).
    레지스트리는 `pkgutil` 순회로 규칙을 모으므로 정렬하지 않으면 파일시스템 순서가
    출력에 새고, 골든셋 회귀 diff에 노이즈가 생긴다 (결정론 = 02 S1-5).

    엔진이 정렬을 보장하므로 **개별 규칙은 반환 순서를 신경 쓰지 않아도 된다.**

    Args:
        model: 검사 대상 구조 모델.
        rules: 사용할 규칙 (기본값 = 레지스트리 전체). 테스트에서 주입한다.
    """
    findings: list[Finding] = []
    by_stage: dict[Stage, list[Rule]] = {stage: [] for stage in _STAGE_ORDER}
    for rule in rules if rules is not None else all_rules():
        by_stage.setdefault(rule.stage, []).append(rule)

    # _STAGE_ORDER에 없는 단계(향후 L-C E2E 등)가 조용히 누락되지 않게 뒤에 붙인다.
    extra = sorted(s for s in by_stage if s not in _STAGE_ORDER)
    for stage in (*_STAGE_ORDER, *extra):
        stage_findings: list[Finding] = []
        for rule in sorted(by_stage.get(stage, []), key=lambda r: r.id):
            stage_findings.extend(rule.check(model))
        # location은 아직 문자열이다 — 라인 번호가 생기면 정렬 키를 함께 고쳐야 한다
        # (라인 10이 라인 9보다 앞서는 사전식 정렬 문제).
        stage_findings.sort(key=lambda f: (f.rule_id, f.location))
        findings.extend(stage_findings)
    return ValidationReport(findings=tuple(findings))


def validate(path: str | Path) -> ValidationReport:
    """파일 경로를 받아 전체 검증 파이프라인을 실행한다."""
    source = Path(path)
    with tempfile.TemporaryDirectory(prefix="twb_lint_") as tmp:
        model = inspector.inspect(source, Path(tmp))
        return validate_model(model)
