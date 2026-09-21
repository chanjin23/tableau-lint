"""규칙 ⑱(`workbook.shape`) — `<worksheets>`가 있는데 비어 있으면 안 된다.

이 규칙의 함정은 둘이다.

1. **증상이 조용하다.** 오류 대화상자가 없어서 `passed=true`를 받은 사용자가 성공으로
   읽는다. 실패02가 정확히 그 파일이었다 (05 F5-p)
2. **워크시트 개수로 걸면 안 된다.** 최초안이 그렇게 했다가 실파일 16개(KPMG 템플릿)를
   거짓 ERROR로 때릴 뻔했다 — `<worksheets>` 요소를 생략한 워크북은 **정상적으로 열린다**

아래 두 테스트가 그 경계를 양쪽에서 고정한다. 하나만 있으면 경계가 다시 무너진다.
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
    """실패02의 모양 — 요소는 있는데 비었다. Tableau가 조용히 `문서1`로 대체한다.

    실파일 303개 중 이 모양은 **2개**뿐이고 둘 다 사용자가 "안 열린다"로 제보한
    파일이다 (05 F5-p).
    """
    ctx = make_ctx(make_twb(extra_body="<worksheets />"))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "문서1" in findings[0].message
    assert findings[0].line is not None


def test_missing_worksheets_element_is_silent(rule: WorkbookShapeRule) -> None:
    """**경계의 반대쪽** — 요소를 생략한 워크북은 열린다 (2026-09-21 사용자 확인).

    `<worksheets>`는 선택 요소(minOccurs=0)이고, 실파일 **16개**(KPMG 화면템플릿)가
    이 모양으로 정상 로드된다. 개수로 걸었던 최초안은 이 16개를 전부 거짓 ERROR로
    때렸다 — AC7 붕괴다.

    **이 테스트가 이 파일에서 가장 중요하다.** 위 테스트만 있으면 구현을
    `findall("worksheets/worksheet")` 개수 판정으로 되돌려도 green이다.
    """
    ctx = make_ctx(make_twb(dashboards=(Dash(name="대시보드"),)))

    assert rule.check(ctx) == []


def test_missing_worksheets_element_is_reported_as_not_checked(
    rule: WorkbookShapeRule,
) -> None:
    """침묵과 **판정 대상 아님**은 다르다 — 후자는 coverage에 남긴다 (02 S5).

    요소가 없으면 "검사했고 문제없음"이 아니라 "이 자리는 판정하지 않는다"다.
    """
    ctx = make_ctx(make_twb(dashboards=(Dash(name="대시보드"),)))

    rule.check(ctx)

    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: WorkbookShapeRule) -> None:
    """검사 못 했으면 말한다 — 빈 리스트는 "전부 검사했고 문제없음"으로 읽힌다 (02 S5)."""
    ctx = make_ctx(make_twb(worksheets=("매출",)))
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
