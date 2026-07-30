"""규칙 ⑦(`ref.notation`) — 참조 표기 규약.

규칙 ②와 묻는 것이 다르다: ②는 "필드가 있는가", ⑦은 "그 자리에 쓸 수 있는 표기인가".
필드가 존재해도 표기가 틀리면 Tableau는 **열고 나서 그 설정만 버린다** → WARNING.

근거는 2026-07-30 MA_003 매출표 실측 (docs/05-xsd-spike.md F5-c).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.builder import Calc, Ds, make_ctx, make_twb
from twb_lint import fieldref
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.ref_notation import RefNotationRule

QUOTED = "&quot;[federated.abc].[usr:C_실적:qk]&quot;"
BARE = "[federated.abc].[usr:C_실적:qk]"


@pytest.fixture
def rule() -> RefNotationRule:
    return RefNotationRule()


def ctx_with_model(tmp_path: Path, xml: str) -> Any:
    """모델까지 실제로 추출한 컨텍스트 — ⑦-c는 매개변수 집합이 입력이라 필요하다."""
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def param_findings(rule: RefNotationRule, ctx: Any) -> list[Any]:
    return [f for f in rule.check(ctx) if "매개변수" in f.message]


def test_bare_fieldref_member_is_a_warning(rule: RefNotationRule) -> None:
    """실측: 따옴표 없는 member는 필터가 **무시된다**. 파일은 열리므로 WARNING이다."""
    ctx = make_ctx(
        make_twb(
            extra_body=(
                "<filter class='categorical'>"
                f"<groupfilter function='member' level='[:Measure Names]' member='{BARE}' />"
                "</filter>"
            )
        )
    )

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "따옴표" in findings[0].message
    assert findings[0].line is not None


def test_quoted_member_is_silent(rule: RefNotationRule) -> None:
    ctx = make_ctx(
        make_twb(
            extra_body=(
                "<filter class='categorical'>"
                f"<groupfilter function='member' level='[:Measure Names]' member='{QUOTED}' />"
                "</filter>"
            )
        )
    )

    assert rule.check(ctx) == []


@pytest.mark.parametrize(
    "member",
    ["true", "&quot;SAMT&quot;", "&quot;[federated.abc].[none:x:nk]&quot;"],
)
def test_non_fieldref_members_are_not_touched(rule: RefNotationRule, member: str) -> None:
    """불리언·문자열 값은 대상이 아니다 — 추측해 넓히면 정상본이 전부 걸린다 (S1-6)."""
    ctx = make_ctx(
        make_twb(
            extra_body=(
                "<filter class='categorical'>"
                f"<groupfilter function='member' level='[none:x:nk]' member='{member}' />"
                "</filter>"
            )
        )
    )

    assert rule.check(ctx) == []


@pytest.mark.parametrize(
    "body",
    [
        "<rows>[Multiple Values]</rows>",
        "<cols>[Multiple Values]</cols>",
        "<text column='[Multiple Values]' />",
    ],
)
def test_unqualified_placeholder_is_a_warning(rule: RefNotationRule, body: str) -> None:
    """한정자 없는 `[Multiple Values]`는 워크시트에서 **제거된다** (실측)."""
    ctx = make_ctx(make_twb(extra_body=body))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "한정자" in findings[0].message


def test_qualified_placeholder_is_silent(rule: RefNotationRule) -> None:
    ctx = make_ctx(make_twb(extra_body="<rows>[federated.abc].[Multiple Values]</rows>"))

    assert rule.check(ctx) == []


def _wb(formula: str, *, shared_name: bool = False) -> str:
    name = "연도" if shared_name else "P_YEAR"
    return make_twb(
        datasources=(
            Ds(name="Parameters", columns=(name,)),
            Ds(
                name="federated.abc",
                columns=(("연도",) if shared_name else ("base_ym",)),
                calcs=(Calc(name="C_P", formula=formula),),
            ),
        )
    )


def test_bare_parameter_reference_in_a_formula_is_a_warning(
    rule: RefNotationRule, tmp_path: Path
) -> None:
    """⑦-c — `[P_YEAR]`는 계산필드를 통째로 오류 상태로 만든다 (실측).

    정상본은 3,377건 전부 `[Parameters].[…]`로 한정돼 있다.
    """
    ctx = ctx_with_model(tmp_path, _wb("YEAR([base_ym]) = [P_YEAR]"))

    findings = param_findings(rule, ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "[Parameters].[P_YEAR]" in (findings[0].fix or "")
    assert findings[0].line is not None


def test_qualified_parameter_reference_is_silent(
    rule: RefNotationRule, tmp_path: Path
) -> None:
    ctx = ctx_with_model(tmp_path, _wb("YEAR([base_ym]) = [Parameters].[P_YEAR]"))

    assert param_findings(rule, ctx) == []


def test_name_shared_with_a_data_column_is_not_reported(
    rule: RefNotationRule, tmp_path: Path
) -> None:
    """같은 이름이 데이터 컬럼에도 있으면 매개변수를 가리킨다고 단정할 수 없다 (S1-6)."""
    ctx = ctx_with_model(tmp_path, _wb("SUM([연도])", shared_name=True))

    assert param_findings(rule, ctx) == []


def test_placeholder_stays_excluded_from_field_matching() -> None:
    """규칙 ②는 이 이름을 필드로 대조하지 않는다 — 그 제외가 ⑦이 필요한 이유다.

    제외를 지우면 ②가 정상본 235곳을 dangling으로 뱉는다. 둘은 짝이다.
    """
    assert "Multiple Values" in fieldref.SPECIAL_NAMES


def test_missing_tree_reports_the_skip(rule: RefNotationRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
