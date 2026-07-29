"""규칙 ③(`named.refs`) — 3자 대조.

**이 규칙만 ERROR를 낸다.** 근거는 표본 10개 전부에서 세 집합이 일치한다는 실측이다.
그래서 여기 테스트의 절반은 "정상 상태에서 침묵하는가"를 본다 — AC7이 먼저다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Dash, make_twb
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.semantic.named_refs import NamedRefsRule


@pytest.fixture
def rule() -> NamedRefsRule:
    return NamedRefsRule()


def ctx_for(tmp_path: Path, xml: str) -> ValidationContext:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def test_a_consistent_workbook_is_silent(tmp_path: Path, rule: NamedRefsRule) -> None:
    xml = make_twb(
        worksheets=("S1", "S2"),
        dashboards=(Dash(name="D", zones=("S1", "S2")),),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_an_unplaced_worksheet_is_not_reported(tmp_path: Path, rule: NamedRefsRule) -> None:
    """대시보드에 없는 시트는 정상이다 (표본 10개 중 1개가 그렇다)."""
    xml = make_twb(worksheets=("S1", "S2"), dashboards=(Dash(name="D", zones=("S1",)),))

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_dangling_zone_is_an_error(tmp_path: Path, rule: NamedRefsRule) -> None:
    """R3 — 정의가 없는 시트를 배치했다."""
    xml = make_twb(worksheets=("S1",), dashboards=(Dash(name="D", zones=("S1", "Ghost")),))

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "Ghost" in findings[0].message


def test_a_dangling_zone_is_reported_once(tmp_path: Path, rule: NamedRefsRule) -> None:
    """정의가 없으면 viewpoint·window도 당연히 없다 — 같은 사실을 3번 말하지 않는다."""
    xml = make_twb(
        worksheets=(),
        dashboards=(Dash(name="D", zones=("Ghost",), viewpoints=()),),
        worksheet_windows=(),
    )

    assert len(rule.check(ctx_for(tmp_path, xml))) == 1


def test_missing_viewpoint_is_an_error(tmp_path: Path, rule: NamedRefsRule) -> None:
    """R2 — 로드 시 내부 오류 2805CF18."""
    xml = make_twb(
        worksheets=("S1",),
        dashboards=(Dash(name="D", zones=("S1",), viewpoints=()),),
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "2805CF18" in findings[0].message


def test_missing_worksheet_window_is_an_error(tmp_path: Path, rule: NamedRefsRule) -> None:
    xml = make_twb(
        worksheets=("S1",),
        dashboards=(Dash(name="D", zones=("S1",)),),
        worksheet_windows=(),
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "window class='worksheet'" in findings[0].message


def test_no_dashboards_reports_the_skip(tmp_path: Path, rule: NamedRefsRule) -> None:
    """대조할 것이 없었던 것과 문제없는 것은 다르다 (02 S5)."""
    ctx = ctx_for(tmp_path, make_twb(worksheets=("S1",)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
