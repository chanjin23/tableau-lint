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


def _wb_derived(
    *calcs: Calc, target: str = "C_매출", derivation: str = "Sum", in_worksheet: bool = True
) -> str:
    """⑧-b용 — 계산 하나에 집계 파생 인스턴스를 건 워크북."""
    instance = (
        f"<column-instance column='[{target}]' derivation='{derivation}' "
        f"name='[{derivation.lower()}:{target}:qk]' pivot='key' type='quantitative' />"
    )
    body = (
        f"<worksheets><worksheet name='S'><table><view>"
        f"<datasource-dependencies datasource='federated.abc'>{instance}"
        f"</datasource-dependencies></view></table></worksheet></worksheets>"
        if in_worksheet
        else instance
    )
    return make_twb(
        datasources=(Ds(name="federated.abc", columns=("매출", "idct_val"), calcs=calcs),),
        extra_body=body,
    )


def test_aggregate_formula_with_an_aggregate_derivation_is_a_warning(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """⑧-b — `SUM(SUM(…))`이 된다. 실측: MA_011에서 알약이 빨개지고 시트가 안 그려졌다."""
    ctx = ctx_for(tmp_path, _wb_derived(Calc(name="C_매출", formula="SUM([idct_val])")))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "다시 집계했다" in findings[0].message
    assert "derivation='Sum'" in findings[0].message
    assert findings[0].line is not None


def test_row_level_formula_with_an_aggregate_derivation_is_silent(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """정본 모양 — 행 수준 계산을 선반에서 `SUM()`으로 올린 것이다."""
    ctx = ctx_for(
        tmp_path,
        _wb_derived(Calc(name="C_매출", formula='IF [매출] = "x" THEN [idct_val] END')),
    )

    assert rule.check(ctx) == []


def test_bare_lod_formula_with_an_aggregate_derivation_is_silent(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """LOD 결과는 행 수준처럼 쓰인다 — `SUM({ FIXED … })`는 정상이다.

    중첩 LOD를 한 겹만 벗기면 바깥 `AVG(`가 남아 위반으로 보였다 (실측 MA_008 6건).
    """
    formula = "{ FIXED [매출] : AVG({ FIXED [매출], [idct_val] : SUM([idct_val]) }) }"
    ctx = ctx_for(tmp_path, _wb_derived(Calc(name="C_매출", formula=formula)))

    assert rule.check(ctx) == []


def test_aggregate_through_a_reference_chain_is_a_warning(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """비율 계산(`[집계A] / [집계B]`)도 집계식이다 — 실측 MA_011 `C_영업이익률`."""
    ctx = ctx_for(
        tmp_path,
        _wb_derived(
            Calc(name="C_이익", formula="SUM([idct_val])"),
            Calc(name="C_매출", formula="[C_이익] / SUM([idct_val]) * 100"),
        ),
    )

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]


def test_datasource_only_instance_is_not_reported(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """어느 워크시트도 쓰지 않는 잔재다 — 실측 위반 65건 중 63건이 여기였다."""
    ctx = ctx_for(
        tmp_path,
        _wb_derived(Calc(name="C_매출", formula="SUM([idct_val])"), in_worksheet=False),
    )

    assert rule.check(ctx) == []


def test_aggregate_derivation_on_a_plain_column_is_silent(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """`SUM([매출액])` — 계산이 아닌 원본 컬럼에 거는 집계는 정상 그 자체다."""
    ctx = ctx_for(tmp_path, _wb_derived(target="매출"))

    assert rule.check(ctx) == []


def test_missing_tree_reports_the_skip(rule: CalcAggregationRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


# ⑧-c — 한 수식 안에서 집계와 행수준을 섞었다 (2026-09-14 실측, 05 F5-m)


def _mix_wb(formula: str, *, with_param: bool = False) -> str:
    """`C_혼합` 하나만 든 워크북. `매출`·`수량`은 원본 컬럼(= 행수준 확정)이다."""
    sources = [Ds(name="federated.abc", columns=("매출", "수량"), calcs=(
        Calc(name="C_혼합", formula=formula),
        Calc(name="C_집계", formula="SUM([매출])"),
    ))]
    if with_param:
        sources.append(Ds(name="Parameters", columns=("P_기준",)))
    return make_twb(datasources=tuple(sources))


def mixed_findings(rule: CalcAggregationRule, ctx: Any) -> list[Any]:
    return [f for f in rule.check(ctx) if "섞었다" in f.message]


@pytest.mark.parametrize(
    ("formula", "why"),
    [
        ("SUM([매출]) + [수량]", "덧셈에서 섞였다"),
        ("IF SUM([매출]) > 0 THEN [수량] ELSE 0 END", "조건은 집계, 분기는 행수준"),
        ("IF [수량] > 0 THEN SUM([매출]) ELSE 0 END", "조건은 행수준, 분기는 집계"),
        ("[수량] / SUM([매출])", "나눗셈에서 섞였다"),
        ("SUM([매출]) + [C_집계] + [수량]", "집계 계산필드는 무죄, 원본 컬럼이 범인"),
    ],
)
def test_mixed_levels_are_a_warning(
    rule: CalcAggregationRule, tmp_path: Path, formula: str, why: str
) -> None:
    """Tableau는 *'집계 및 비집계 인수를 혼합할 수 없습니다'*로 거부한다.

    파일은 열리므로 WARNING이다 — 대신 그 필드를 쓰는 시트가 빈 화면이 된다.
    """
    findings = mixed_findings(rule, ctx_for(tmp_path, _mix_wb(formula)))

    assert [f.severity for f in findings] == [Severity.WARNING], why
    assert "[수량]" in findings[0].message
    assert findings[0].fix


@pytest.mark.parametrize(
    ("formula", "why"),
    [
        ("SUM([매출] + [수량])", "둘 다 집계 인자 안 — 정상"),
        ("SUM([매출]) + SUM([수량])", "바깥에 맨 참조가 없다"),
        ("[매출] + [수량]", "집계가 아예 없다"),
        ("SUM([매출]) + [C_집계]", "맨 참조가 집계 계산필드다"),
        ("MIN([매출], [수량])", "2인자 MIN은 행수준 함수 — 집계가 아니다"),
        ("{FIXED [수량] : SUM([매출])} + [수량]", "LOD는 행수준에서 쓸 수 있다"),
        ("SUM(IF [수량] > 0 THEN [매출] END)", "IF가 통째로 집계 인자 안에 있다"),
    ],
)
def test_unmixed_formulas_are_silent(
    rule: CalcAggregationRule, tmp_path: Path, formula: str, why: str
) -> None:
    """거짓양성 함정 — 정상본 85,316개 수식이 전부 이쪽이다 (AC7)."""
    assert mixed_findings(rule, ctx_for(tmp_path, _mix_wb(formula))) == [], why


def test_parameters_are_not_row_level(rule: CalcAggregationRule, tmp_path: Path) -> None:
    """매개변수는 상수다 — 집계에도 행수준에도 걸지 않는다."""
    ctx = ctx_for(tmp_path, _mix_wb("SUM([매출]) > [Parameters].[P_기준]", with_param=True))

    assert mixed_findings(rule, ctx) == []


def test_unresolvable_reference_is_not_a_violation(
    rule: CalcAggregationRule, tmp_path: Path
) -> None:
    """워크북 어디에도 정의가 없는 참조는 **판정 불가**다 (⑧-a와 같은 안전장치).

    비집계로 단정하면 우리가 못 펼친 것이 남의 정상 파일을 막는다 (02 S1-6).
    """
    ctx = ctx_for(tmp_path, _mix_wb("SUM([매출]) + [어디에도_없는_필드]"))

    assert mixed_findings(rule, ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.PARTIAL]
