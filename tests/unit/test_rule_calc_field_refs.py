"""규칙 ②(`calc.field_refs`) — 참조 해소.

두 가지가 이 규칙의 전부다: **표기 정규화**(G8)와 **WARNING 고정**(03 D3.6.3).
정규화가 빠지면 정상본이 전량 dangling이 되고, ERROR면 정상본 10/10이 막힌다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.builder import Calc, Ds, make_ctx, make_twb, qualified_ref
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.calc_field_refs import CalcFieldRefsRule


@pytest.fixture
def rule() -> CalcFieldRefsRule:
    return CalcFieldRefsRule()


def ctx_for(tmp_path: Path, xml: str) -> Any:
    """모델까지 실제로 추출한 컨텍스트 — 필드 유니버스가 규칙의 입력이다."""
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


DS = Ds(
    name="federated.abc",
    columns=("accs_code",),
    calcs=(Calc(name="Calculation_1", formula="SUM([accs_code])"),),
)


def test_resolved_references_are_silent(tmp_path: Path, rule: CalcFieldRefsRule) -> None:
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table><style><style-rule>'
            f'<format field="{qualified_ref("federated.abc", "Calculation_1", "usr", "qk")}" />'
            "</style-rule></style></table></worksheet></worksheets>"
        ),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_worksheet_notation_resolves_against_calc_notation(
    tmp_path: Path, rule: CalcFieldRefsRule
) -> None:
    """**규칙 ②의 최대 함정** — 정규화가 없으면 이 참조가 dangling이 된다 (07 G8)."""
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table>'
            '<filter column="[federated.abc].[usr:Calculation_1:qk]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_an_adhoc_calc_is_not_dangling(tmp_path: Path, rule: CalcFieldRefsRule) -> None:
    """임시 계산의 정의 자리는 `<datasource-dependencies>` 하나뿐이다 (03 D3.6.4)."""
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table><view>'
            "<datasource-dependencies datasource='federated.abc'>"
            "<column datatype='string' name='[Calculation_9]' user:unnamed='S'>"
            "<calculation class='tableau' formula='&quot;계획&quot;' /></column>"
            "<column-instance column='[Calculation_9]' derivation='None'"
            " name='[none:Calculation_9:nk]' pivot='key' type='nominal' />"
            "</datasource-dependencies></view>"
            '<filter column="[federated.abc].[none:Calculation_9:nk]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_dangling_reference_is_a_warning_not_an_error(
    tmp_path: Path, rule: CalcFieldRefsRule
) -> None:
    """정상 파일에도 잔재 참조가 있다 — ERROR면 골든셋 10/10이 막힌다 (03 D3.6.3)."""
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table>'
            '<filter column="[federated.abc].[none:GhostField:nk]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "GhostField" in findings[0].message
    assert findings[0].line is not None


def test_special_namespaces_are_never_flagged(tmp_path: Path, rule: CalcFieldRefsRule) -> None:
    """과거 lint가 `[:Measure Names]`에서 오탐했다 (함정 S9, 실측 544회)."""
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table>'
            '<encoding field="[:Measure Names]" />'
            '<text column="[federated.abc].[Multiple Values]" />'
            '<lod column="[__tableau_internal_object_id__].[whatever]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_same_reference_in_many_places_is_one_finding(
    tmp_path: Path, rule: CalcFieldRefsRule
) -> None:
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table>'
            '<filter column="[federated.abc].[none:Ghost:nk]" />'
            '<text column="[federated.abc].[usr:Ghost:qk]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "참조 2곳" in findings[0].message


def test_unknown_datasource_is_reported_distinctly(
    tmp_path: Path, rule: CalcFieldRefsRule
) -> None:
    xml = make_twb(
        datasources=(DS,),
        extra_body=(
            '<worksheets><worksheet name="S"><table>'
            '<filter column="[federated.gone].[none:x:nk]" />'
            "</table></worksheet></worksheets>"
        ),
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "데이터소스가 워크북에 없다" in findings[0].message


def test_formula_surface_is_covered(tmp_path: Path, rule: CalcFieldRefsRule) -> None:
    """수식 표면도 규칙 ①과 같은 곳을 본다 (03 D3.6)."""
    xml = make_twb(
        datasources=(Ds(name="ds", calcs=(Calc(name="c", formula="SUM([NoSuchField])"),)),)
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "NoSuchField" in findings[0].message


def test_no_datasources_reports_the_skip(tmp_path: Path, rule: CalcFieldRefsRule) -> None:
    """대조 집합이 없으면 전부 dangling이 된다 — 검사하지 않았다고 말한다 (02 S5)."""
    ctx = ctx_for(tmp_path, make_twb(worksheets=("S",)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: CalcFieldRefsRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
