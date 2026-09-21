"""규칙 ⑱(`workbook.shape`) — 워크북에 워크시트가 최소 1개.

이 규칙의 함정은 **증상이 조용하다는 것**이다. 오류 대화상자가 없어서 `passed=true`를
받은 사용자가 성공으로 읽는다. 실패02가 정확히 그 파일이었다 (05 F5-p).

`<worksheets />`(비어 있음)와 `<worksheets>` 자체가 없는 경우를 **둘 다** 잡아야 한다 —
XSD는 앞쪽만 보고, 그마저 WARNING이다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import Dash, make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.workbook_shape import WorkbookShapeRule


@pytest.fixture
def rule() -> WorkbookShapeRule:
    return WorkbookShapeRule()


def test_workbook_with_a_worksheet_is_silent(rule: WorkbookShapeRule) -> None:
    ctx = make_ctx(make_twb(worksheets=("매출",)))

    assert rule.check(ctx) == []


def test_empty_worksheets_element_is_an_error(rule: WorkbookShapeRule) -> None:
    """실패02의 모양 — 요소는 있는데 비었다. Tableau가 조용히 `문서1`로 대체한다."""
    ctx = make_ctx(make_twb(extra_body="<worksheets />"))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "문서1" in findings[0].message


def test_missing_worksheets_element_is_also_an_error(rule: WorkbookShapeRule) -> None:
    """**XSD가 침묵하는 쪽이다** — `<worksheets>`는 선택 요소라 없어도 구문은 유효하다.

    워크시트 0개라는 결함은 같으므로 여기서 잡는다. 실파일 253개 중 이 모양이 1개
    있었고(`MA_015…/old/…템플릿`), 대시보드만 있고 워크시트가 없는 실패02와 같은
    모양이었다.
    """
    ctx = make_ctx(make_twb(dashboards=(Dash(name="대시보드"),)))

    assert [f.severity for f in rule.check(ctx)] == [Severity.ERROR]


def test_finding_points_at_the_worksheets_line_when_there_is_one(
    rule: WorkbookShapeRule,
) -> None:
    ctx = make_ctx(make_twb(extra_body="<worksheets />"))

    assert rule.check(ctx)[0].line is not None


def test_missing_tree_reports_the_skip(rule: WorkbookShapeRule) -> None:
    """검사 못 했으면 말한다 — 빈 리스트는 "전부 검사했고 문제없음"으로 읽힌다 (02 S5)."""
    ctx = make_ctx(make_twb(worksheets=("매출",)))
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
