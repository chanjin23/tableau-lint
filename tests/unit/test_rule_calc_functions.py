"""규칙 ①(`calc.functions`) — 화이트리스트 대조.

**WARNING 고정**이 이 규칙의 핵심 성질이다. 목록에 없음 = "그 함수가 없다"가 아니라
"우리 목록이 불완전하다"일 수 있다 (02 S1-6 · 07 G3). ERROR가 되면 우리 데이터의
공백이 남의 정상 파일을 막는다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.builder import Calc, Ds, make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity, WorkbookModel
from twb_lint.validation.semantic.calc_functions import CalcFunctionsRule

BUILD = "2026.1.1 (20261.26.0410.0924)"


@pytest.fixture
def rule() -> CalcFunctionsRule:
    return CalcFunctionsRule()


def ctx_for(xml: str, source_build: str | None = BUILD) -> Any:
    return make_ctx(
        xml, model=WorkbookModel(source=Path("fixture.twb"), source_build=source_build)
    )


def test_known_functions_are_silent(rule: CalcFunctionsRule) -> None:
    ctx = ctx_for(
        make_twb(
            datasources=(
                Ds(
                    name="ds",
                    calcs=(Calc(name="c1", formula="ZN(SUM([a])) + DATEDIFF('y', [b], [c])"),),
                ),
            )
        )
    )

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == []


def test_unknown_function_is_a_warning_not_an_error(rule: CalcFunctionsRule) -> None:
    ctx = ctx_for(
        make_twb(datasources=(Ds(name="ds", calcs=(Calc(name="c1", formula="FROBNICATE([a])"),)),))
    )

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "FROBNICATE" in findings[0].message
    assert findings[0].line is not None


def test_one_finding_per_function_not_per_occurrence(rule: CalcFunctionsRule) -> None:
    """환각 함수 하나가 calc 100개에 퍼지면 건당 보고는 리포트를 못 읽게 만든다."""
    ctx = ctx_for(
        make_twb(
            datasources=(
                Ds(
                    name="ds",
                    calcs=(
                        Calc(name="c1", formula="FROBNICATE([a])"),
                        Calc(name="c2", formula="FROBNICATE([b]) + FROBNICATE([c])"),
                    ),
                ),
            )
        )
    )

    findings = rule.check(ctx)

    assert len(findings) == 1
    # 세는 단위는 **수식**이다 — 한 수식 안에서 두 번 써도 그 수식 1곳이다.
    assert "수식 2곳" in findings[0].message


def test_groupfilter_expressions_are_covered_too(rule: CalcFunctionsRule) -> None:
    """수식 표면은 2곳이다 — 한쪽만 보면 커버리지가 조용히 달라진다 (03 D3.6)."""
    ctx = ctx_for(
        make_twb(extra_body="<groupfilter function='filter' expression='BOGUSFN([a])' />")
    )

    assert [f.severity for f in rule.check(ctx)] == [Severity.WARNING]


def test_unsupported_release_reports_the_skip(rule: CalcFunctionsRule) -> None:
    """목록이 없으면 조용히 통과하지 않는다 (02 S5)."""
    ctx = ctx_for(make_twb(source_build=None), source_build=None)

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: CalcFunctionsRule) -> None:
    ctx = ctx_for(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
