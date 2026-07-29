"""L-A 규칙(`xsd.schema`)의 배선 — 정책이 아니라 **연결**을 본다.

심각도 정책 자체는 `test_severity_policy.py`가, 정상본 무오탐은 골든셋 회귀가 본다.
여기서는 규칙이 스키마를 실제로 태우는지, 캐시가 도는지, 못 했을 때 말하는지를 본다.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint import config
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.syntactic import xsd


@pytest.fixture
def rule() -> xsd.XsdRule:
    return xsd.XsdRule()


def ctx_for(xml: str, source_build: str | None = None) -> Any:
    from pathlib import Path

    from twb_lint.models import WorkbookModel

    model = WorkbookModel(
        source=Path("fixture.twb"),
        source_build=source_build or "2026.1.1 (20261.26.0410.0924)",
    )
    return make_ctx(xml, model=model)


def test_schema_is_compiled_once_per_path() -> None:
    """MCP는 상주 프로세스다 — 매 호출 재컴파일하면 그 비용이 매번 실린다 (AC5)."""
    path = config.xsd_path("2026.1")
    assert path is not None

    first = xsd.load_schema(str(path))
    second = xsd.load_schema(str(path))

    assert first is second


def test_unsupported_release_warns_and_reports_the_skip(rule: xsd.XsdRule) -> None:
    """미지원 릴리스에서 ERROR를 내면 "우리가 모른다"가 "파일이 틀렸다"가 된다."""
    ctx = ctx_for(make_twb(), source_build="2099.9.0 (x)")

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_is_reported_not_silently_passed(rule: xsd.XsdRule) -> None:
    """빈 리스트만 반환하면 "검사했고 문제없음"으로 기록된다 (02 S5)."""
    ctx = ctx_for(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_schema_violations_become_findings_with_line_numbers(rule: xsd.XsdRule) -> None:
    """픽스처 XML은 **의도적으로** XSD 유효하지 않다 (builder 독스트링) — 배선 확인용이다."""
    ctx = ctx_for(make_twb(worksheets=("Sheet 1",)))

    findings = rule.check(ctx)

    assert findings, "L-A가 아무것도 내지 않았다 — 스키마가 태워지지 않았을 수 있다"
    assert {f.rule_id for f in findings} == {"xsd.schema"}
    assert all(f.line is None or f.line > 0 for f in findings)


def test_truncation_is_reported_not_silent(
    rule: xsd.XsdRule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """상한으로 자를 때 조용히 자르면 "이게 전부"로 읽힌다 (02 S5)."""
    monkeypatch.setattr(xsd, "MAX_FINDINGS", 1)
    ctx = ctx_for(make_twb(worksheets=("A", "B"), extra_body="<bogus /><bogus2 />"))

    findings = rule.check(ctx)

    assert len(findings) <= 1
    notes = ctx.notes_for(rule.id)
    assert [n.status for n in notes] == [CoverageStatus.PARTIAL]
    assert "만 보고한다" in (notes[0].reason or "")
