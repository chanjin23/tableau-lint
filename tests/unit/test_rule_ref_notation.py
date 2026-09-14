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


def _filter(level: str, member: str = "&quot;고액&quot;") -> str:
    return (
        "<filter class='categorical' column='[federated.abc].[none:C_등급:nk]'>"
        f"<groupfilter function='member' level='{level}' member='{member}' />"
        "</filter>"
    )


def test_qualified_filter_level_is_a_warning(rule: RefNotationRule) -> None:
    """실측 3,484 : 0. 한정자를 붙이면 Tableau가 필터를 버린다 (05 F5-f)."""
    ctx = make_ctx(make_twb(extra_body=_filter("[federated.abc].[none:C_등급:nk]")))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "한정자가 붙었다" in findings[0].message
    assert "level='[none:C_등급:nk]'" in findings[0].fix
    assert findings[0].line is not None


def test_unqualified_filter_level_is_silent(rule: RefNotationRule) -> None:
    """정상 모양. 3,484건이 전부 이것이다."""
    assert rule.check(make_ctx(make_twb(extra_body=_filter("[none:C_등급:nk]")))) == []


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "<filter class='categorical'>"
            "<groupfilter function='union'>"
            f"<groupfilter function='member' level='[:Measure Names]' member='{QUOTED}' />"
            "</groupfilter></filter>",
            id="level 없는 묶음 노드 + 한정된 member는 ⑦-a의 자리다",
        ),
        pytest.param(
            _filter("[:Measure Names]", member="&quot;SAMT&quot;"),
            id="내장 자리표시자 level은 한정되지 않는다",
        ),
        pytest.param(
            "<filter class='categorical' column='[federated.abc].[none:팀명:nk]'>"
            "<groupfilter function='level-members' level='[팀명(복사본)_0435408457822213]' />"
            "</filter>",
            id="level이 column의 기저 이름과 달라도 정상이다 (실측 반례)",
        ),
    ],
)
def test_lookalike_levels_are_not_reported(rule: RefNotationRule, body: str) -> None:
    """거짓양성 함정 — 비슷하지만 정상인 모양들. 여기서 뱉으면 AC7이 무너진다."""
    findings = rule.check(make_ctx(make_twb(extra_body=body)))

    assert [f for f in findings if "level" in f.message] == []


@pytest.mark.parametrize(
    ("body", "role"),
    [
        pytest.param(
            "<computed-sort column='[none:C_구분:nk]' direction='ASC' "
            "using='[federated.abc].[min:scrn_seq:qk]' />",
            "정렬 대상",
            id="computed-sort@column",
        ),
        pytest.param(
            "<computed-sort column='[federated.abc].[none:C_구분:nk]' direction='ASC' "
            "using='[min:scrn_seq:qk]' />",
            "정렬 기준",
            id="computed-sort@using",
        ),
        pytest.param(
            "<manual-sort column='[:Measure Names]' direction='ASC'><dictionary />"
            "</manual-sort>",
            "정렬 대상",
            id="manual-sort@column",
        ),
    ],
)
def test_unqualified_sort_reference_is_a_warning(
    rule: RefNotationRule, body: str, role: str
) -> None:
    """⑦-e — 한정자를 빼면 Tableau가 **정렬 지정을 무시한다** (2026-08-12 MA_011 실측).

    실측 503 : 503 : 432 대 비한정 0건.
    """
    findings = [f for f in rule.check(make_ctx(make_twb(extra_body=body))) if "정렬" in f.message]

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert findings[0].message.startswith(role)
    assert findings[0].line is not None


def test_qualified_sort_reference_is_silent(rule: RefNotationRule) -> None:
    """정본 모양. 코퍼스 47개가 전부 이것이다."""
    body = (
        "<computed-sort column='[federated.abc].[none:C_구분:nk]' direction='ASC' "
        "using='[federated.abc].[min:scrn_seq:qk]' />"
        "<manual-sort column='[federated.abc].[:Measure Names]' direction='ASC'>"
        "<dictionary><bucket>&quot;[federated.abc].[usr:C_실적:qk]&quot;</bucket></dictionary>"
        "</manual-sort>"
    )

    assert rule.check(make_ctx(make_twb(extra_body=body))) == []


def test_sort_bucket_text_is_not_a_sort_reference(rule: RefNotationRule) -> None:
    """`<bucket>`은 **값** 목록이다 — 한정 여부를 여기서 묻지 않는다 (⑪도 같은 이유로 뺐다)."""
    body = (
        "<manual-sort column='[federated.abc].[:Measure Names]' direction='ASC'>"
        "<dictionary><bucket>&quot;[usr:C_실적:qk]&quot;</bucket></dictionary>"
        "</manual-sort>"
    )

    assert rule.check(make_ctx(make_twb(extra_body=body))) == []


def test_missing_tree_reports_the_skip(rule: RefNotationRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


# ⑦-f — 불리언 필드의 member 리터럴 (2026-09-14 MA_004 손익계산서 실측, 05 F5-k)


def _member_wb(datatype: str, member: str, *, second_ds: bool = False) -> str:
    """`C_레벨1`을 `datatype`으로 선언하고 그 필드를 걸러내는 필터 하나를 단다."""
    extra = (
        (Ds(name="federated.zzz", typed_columns=(("C_레벨1", "string"),)),) if second_ds else ()
    )
    return make_twb(
        datasources=(Ds(name="federated.abc", typed_columns=(("C_레벨1", datatype),)), *extra),
        extra_body=(
            "<filter class='categorical' column='[federated.abc].[none:C_레벨1:nk]'>"
            f"<groupfilter function='member' level='[none:C_레벨1:nk]' member='{member}' />"
            "</filter>"
        ),
    )


def boolean_findings(rule: RefNotationRule, ctx: Any) -> list[Any]:
    return [f for f in rule.check(ctx) if "불리언 필드" in f.message]


def test_quoted_boolean_member_is_a_warning(rule: RefNotationRule, tmp_path: Path) -> None:
    """실측: 불리언을 감싸면 *'필터를 구문 분석하는 동안 오류'*로 필터가 버려진다.

    파일은 열린다 — 대신 걸러져야 할 행이 남아 **틀린 숫자**가 나온다. 그래서 WARNING.
    """
    ctx = ctx_with_model(tmp_path, _member_wb("boolean", "&quot;true&quot;"))

    findings = boolean_findings(rule, ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "member='true'" in (findings[0].fix or "")
    assert findings[0].line is not None


def test_bare_boolean_member_is_silent(rule: RefNotationRule, tmp_path: Path) -> None:
    """정상본 5,923건이 전부 이 모양이다."""
    ctx = ctx_with_model(tmp_path, _member_wb("boolean", "true"))

    assert boolean_findings(rule, ctx) == []


def test_quoted_string_member_is_silent(rule: RefNotationRule, tmp_path: Path) -> None:
    """거짓양성 함정 — 겉모습은 같지만 문자열 필드는 감싸는 것이 **정상**이다.

    정상본 5,569건이 이 모양이고 맨값은 0건이다. datatype을 안 보고 따옴표만 세면
    여기가 통째로 걸린다 (AC7 붕괴).
    """
    ctx = ctx_with_model(tmp_path, _member_wb("string", "&quot;영업이익&quot;"))

    assert boolean_findings(rule, ctx) == []


def test_ambiguous_datatype_is_not_judged(rule: RefNotationRule, tmp_path: Path) -> None:
    """동명 필드의 datatype이 데이터소스마다 다르면 판정하지 않는다 (S1-6).

    `level`에는 데이터소스 한정자가 없어(⑦-d) 어느 쪽을 가리키는지 표기만으로는
    정할 수 없다. 판정 불가를 위반으로 세면 우리 지식의 공백이 남의 파일을 막는다.
    """
    ctx = ctx_with_model(tmp_path, _member_wb("boolean", "&quot;true&quot;", second_ds=True))

    assert boolean_findings(rule, ctx) == []


def test_unresolvable_level_reports_the_partial(rule: RefNotationRule) -> None:
    """컬럼을 못 찾았으면 조용히 넘기지 않고 **검사 못 했다고 말한다** (02 AC9)."""
    ctx = make_ctx(
        make_twb(
            extra_body=(
                "<filter class='categorical'>"
                "<groupfilter function='member' level='[none:C_레벨1:nk]' "
                "member='&quot;true&quot;' />"
                "</filter>"
            )
        )
    )

    assert boolean_findings(rule, ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.PARTIAL]
