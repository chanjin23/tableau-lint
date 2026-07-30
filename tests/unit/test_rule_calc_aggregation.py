"""규칙 ⑧(`calc.aggregation`) — 사용자 지정 집계로 올린 계산의 집계 정합.

핵심은 **판정 불가와 위반을 가르는 것**이다. 섞으면 우리 지식의 공백(집계 함수 목록·
못 펼친 참조)이 남의 정상 파일을 막는다 (02 S1-6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.builder import Calc, Ds, make_ctx, make_twb
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.calc_aggregation import CalcAggregationRule


@pytest.fixture
def rule() -> CalcAggregationRule:
    return CalcAggregationRule()


def ctx_for(tmp_path: Path, xml: str) -> Any:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def _wb(*calcs: Calc, instance: str = "라벨") -> str:
    """계산 몇 개 + 그중 하나를 `usr:` 인스턴스로 올린 워크북."""
    return make_twb(
        datasources=(Ds(name="federated.abc", columns=("매출",), calcs=calcs),),
        extra_body=(
            f"<column-instance column='[{instance}]' derivation='User' "
            f"name='[usr:{instance}:qk]' pivot='key' type='quantitative' />"
        ),
    )


def test_non_aggregate_user_instance_is_a_warning(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """실측: `"전체"` 같은 순수 비집계를 usr로 올리면 그 시트가 비어 나온다."""
    ctx = ctx_for(tmp_path, _wb(Calc(name="라벨", formula='"전체"')))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "라벨" in findings[0].message


def test_aggregate_user_instance_is_silent(rule: CalcAggregationRule, tmp_path: Path) -> None:
    ctx = ctx_for(tmp_path, _wb(Calc(name="라벨", formula="SUM([매출])")))

    assert rule.check(ctx) == []


def test_aggregate_reached_through_a_reference_chain_is_silent(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """정상본 20종이 전부 이 모양이다 — 자기는 비집계인데 참조가 집계다."""
    ctx = ctx_for(
        tmp_path,
        _wb(
            Calc(name="합계", formula="SUM([매출])"),
            Calc(name="라벨", formula='IF [합계] > 0 THEN "양수" ELSE "음수" END'),
        ),
    )

    assert rule.check(ctx) == []


def test_lod_alone_does_not_count_as_aggregation(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """LOD 결과는 행 수준 값처럼 쓰인다 — 실측에서 LOD만 참조한 계산이 거부됐다."""
    ctx = ctx_for(
        tmp_path,
        _wb(
            Calc(name="존재", formula="{ MAX([매출]) } = 1"),
            Calc(name="라벨", formula='IF [존재] THEN "있음" ELSE "" END'),
        ),
    )

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]


def test_dimension_instances_are_not_judged(rule: CalcAggregationRule, tmp_path: Path) -> None:
    """`derivation="None"`은 차원으로 올린 것이다 — 집계를 요구하지 않는다."""
    xml = make_twb(
        datasources=(
            Ds(
                name="federated.abc",
                columns=("매출",),
                calcs=(Calc(name="라벨", formula='"전체"'),),
            ),
        ),
        extra_body=(
            "<column-instance column='[라벨]' derivation='None' "
            "name='[none:라벨:nk]' pivot='key' type='nominal' />"
        ),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_unresolvable_reference_is_reported_as_undecided_not_as_a_violation(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """펼치지 못한 참조는 **위반이 아니다** — 검사 못 했다고 말한다 (02 S5)."""
    ctx = ctx_for(tmp_path, _wb(Calc(name="라벨", formula="[어디에도_없는_필드] + 1")))

    assert rule.check(ctx) == []
    notes = ctx.notes_for(rule.id)
    assert [n.status for n in notes] == [CoverageStatus.PARTIAL]
    assert "판정하지 못했다" in (notes[0].reason or "")


def test_missing_tree_reports_the_skip(rule: CalcAggregationRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
