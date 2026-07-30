"""규칙 ⑨(`set.definition`) — 집합의 기반 필드.

모양(속성 이름)을 열거하지 않고 **기반 필드의 유무**만 본다. 모양은 릴리스마다 늘 수
있지만 "집합에는 기반 필드가 있다"는 성질은 바뀌지 않는다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.set_definition import SetDefinitionRule

USER_SET = (
    "<group caption='C_LV1_KEY 집합' name='[C_LV1_KEY 집합]' name-style='unqualified'>"
    "<groupfilter function='empty-level' member='[C_LV1_KEY]' />"
    "</group>"
)
ACTION_SET = (
    "<group name='[Action (Accs Nm)]' hidden='true' name-style='unqualified'>"
    "<groupfilter function='crossjoin'>"
    "<groupfilter function='level-members' level='[accs_nm]' />"
    "</groupfilter></group>"
)
BROKEN_SET = (
    "<group caption='C_LV1_KEY 집합' name='[C_LV1_KEY 집합]' name-style='unqualified'>"
    "<groupfilter function='union' />"
    "</group>"
)


@pytest.fixture
def rule() -> SetDefinitionRule:
    return SetDefinitionRule()


def test_set_without_a_base_field_is_a_warning(rule: SetDefinitionRule) -> None:
    """실측: 기반 필드가 없으면 `… IN [집합]`을 쓰는 계산이 전부 깨진다."""
    findings = rule.check(make_ctx(make_twb(extra_body=BROKEN_SET)))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "C_LV1_KEY 집합" in findings[0].message
    assert findings[0].line is not None


@pytest.mark.parametrize("body", [USER_SET, ACTION_SET])
def test_both_observed_shapes_are_silent(rule: SetDefinitionRule, body: str) -> None:
    """실파일 61개에 있는 모양은 둘뿐이고 둘 다 기반 필드를 갖는다."""
    assert rule.check(make_ctx(make_twb(extra_body=body))) == []


def test_workbook_without_sets_reports_that_it_checked_nothing(rule: SetDefinitionRule) -> None:
    """검사할 게 없었다는 사실도 남긴다 — 조용한 통과와 구분되지 않으면 안 된다 (02 S5)."""
    ctx = make_ctx(make_twb())

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: SetDefinitionRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
