"""규칙 ⑩(`action.refs`) — 동작 배선 무결성.

실측(실파일 84개 중 `<actions>` 보유 33개)이 이 규칙의 형태를 정했다. 표면 9종 중
7종은 반례 0이고 2종(`source-field`·`target-parameter`)에만 반례가 있다 —
그래서 **전부 WARNING**이다. 여기 테스트의 절반은 "정상 배선에서 침묵하는가"를 본다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Dash, Ds, make_twb, qualified_ref
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.semantic.action_refs import ActionRefsRule


@pytest.fixture
def rule() -> ActionRefsRule:
    return ActionRefsRule()


def ctx_for(tmp_path: Path, xml: str) -> ValidationContext:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def workbook(actions: str, *, groups: str = "") -> str:
    """시트 2개 · 대시보드 1개 · 매개변수 1개 · 필드 1개를 가진 워크북 + 주어진 동작."""
    return make_twb(
        datasources=(
            Ds(name="federated.abc", columns=("accs_nm",)),
            Ds(name="Parameters", columns=("P_MONTH",)),
        ),
        worksheets=("S1", "S2"),
        dashboards=(Dash(name="D", zones=("S1", "S2")),),
        extra_body=f"{groups}<actions>{actions}</actions>",
    )


FIELD = qualified_ref("federated.abc", "accs_nm")


def test_a_consistent_wiring_is_silent(tmp_path: Path, rule: ActionRefsRule) -> None:
    xml = workbook(
        "<action caption='필터' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' type='sheet' />"
        "<exclude-sheet name='S2' />"
        f"<param name='source-field' value={_q(FIELD)} />"
        "<param name='target' value='S2' />"
        "<param name='exclude' value='S1,S2' />"
        "</action>"
        "<edit-parameter-action caption='매개변수' name='[Action2]'>"
        "<source dashboard='D' />"
        "<param name='target-parameter' value='[Parameters].[P_MONTH]' />"
        "</edit-parameter-action>"
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_a_workbook_without_actions_says_so(tmp_path: Path, rule: ActionRefsRule) -> None:
    """조용히 빈 리스트를 내면 "동작을 전부 검사했다"로 읽힌다 (02 S5)."""
    ctx = ctx_for(tmp_path, make_twb(worksheets=("S1",)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("action.refs")] == [CoverageStatus.SKIPPED]


def test_the_definition_copies_inside_actions_are_not_treated_as_actions(
    tmp_path: Path, rule: ActionRefsRule
) -> None:
    """`<actions>` 안의 `<datasources>`·`<datasource-dependencies>`는 동작이 아니다.

    동작이 참조하는 필드 정의의 **사본**이라 그 안의 `<column>`을 배선으로 읽으면
    정상 파일이 통째로 뱉어진다 (실측: 84개 중 3개 파일이 이 사본을 갖는다).
    """
    xml = workbook(
        "<datasources><datasource caption='없는것' name='federated.zzz' /></datasources>"
        "<datasource-dependencies datasource='federated.zzz'>"
        "<column datatype='string' name='[유령]' role='dimension' />"
        "</datasource-dependencies>"
    )
    ctx = ctx_for(tmp_path, xml)

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("action.refs")] == [CoverageStatus.SKIPPED]


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        ("<source dashboard='D' worksheet='없는시트' />", "source@worksheet"),
        ("<source dashboard='없는대시' />", "source@dashboard"),
        ("<source dashboard='D' datasource='federated.zzz' />", "source@datasource"),
        ("<source dashboard='D' /><exclude-sheet name='없는시트' />", "exclude-sheet@name"),
        ("<source dashboard='D' /><param name='target' value='없는시트' />", "param target"),
        (
            "<source dashboard='D' /><param name='exclude' value='S1,없는시트' />",
            "param exclude",
        ),
        (
            "<source dashboard='D' />"
            "<param name='source-field' value='[federated.abc].[none:없는필드:nk]' />",
            "param source-field",
        ),
        (
            "<source dashboard='D' />"
            "<param name='target-group' value='[federated.abc].[없는집합]' />",
            "param target-group",
        ),
    ],
)
def test_each_broken_surface_is_reported_as_warning(
    tmp_path: Path, rule: ActionRefsRule, fragment: str, expected: str
) -> None:
    xml = workbook(f"<action caption='A' name='[Action1]'>{fragment}</action>")

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING], (
        "동작 배선이 끊긴 파일이 열리지 않는다는 근거가 없다 — ERROR로 올리려면 라벨이 먼저다"
    )
    assert expected in findings[0].message


def test_an_existing_set_resolves(tmp_path: Path, rule: ActionRefsRule) -> None:
    """집합 동작의 대상은 `<group>`으로 해소된다 (실측 46:0)."""
    xml = workbook(
        "<edit-group-action caption='집합' name='[Action1]'>"
        "<source dashboard='D' />"
        "<param name='target-group' value='[federated.abc].[accs_nm 집합]' />"
        "</edit-group-action>",
        groups="<group name='[accs_nm 집합]' />",
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_a_parameter_without_the_qualifier_is_reported(
    tmp_path: Path, rule: ActionRefsRule
) -> None:
    """매개변수는 항상 `[Parameters].[이름]`이다 (실측 83:0) — ⑦-c와 같은 축.

    한정자가 없으면 그 데이터소스의 컬럼으로 해석된다. 이름 자체는 실재하므로
    대상 검사만으로는 잡히지 않는다.
    """
    xml = workbook(
        "<edit-parameter-action caption='P' name='[Action1]'>"
        "<source dashboard='D' />"
        "<param name='target-parameter' value='[P_MONTH]' />"
        "</edit-parameter-action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "한정자" in findings[0].message


def test_a_missing_parameter_is_reported(tmp_path: Path, rule: ActionRefsRule) -> None:
    xml = workbook(
        "<edit-parameter-action caption='P' name='[Action1]'>"
        "<source dashboard='D' />"
        "<param name='target-parameter' value='[Parameters].[없는매개변수]' />"
        "</edit-parameter-action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "대상 매개변수" in findings[0].message


def test_a_non_reference_param_value_is_not_guessed_at(
    tmp_path: Path, rule: ActionRefsRule
) -> None:
    """참조 표기가 아니면 대조하지 않는다 — 추측하면 그 자리가 거짓양성이 된다."""
    xml = workbook(
        "<edit-group-action caption='집합' name='[Action1]'>"
        "<source dashboard='D' />"
        "<param name='target-group' value='exclude-all' />"
        "</edit-group-action>"
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_the_same_broken_reference_is_reported_once(
    tmp_path: Path, rule: ActionRefsRule
) -> None:
    """`exclude-sheet`는 파일 하나에 수백 번 나온다 (실측 3,016회/33파일).

    합치지 않으면 시트 하나가 없다는 사실이 finding 수백 건이 되어 리포트를 덮는다.
    """
    excludes = "<exclude-sheet name='없는시트' />" * 40
    xml = workbook(
        f"<action caption='A' name='[Action1]'><source dashboard='D' />{excludes}</action>"
        f"<action caption='B' name='[Action2]'><source dashboard='D' />{excludes}</action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "80곳" in findings[0].message


def test_a_sheet_name_with_a_comma_is_not_split(
    tmp_path: Path, rule: ActionRefsRule
) -> None:
    """콤마가 든 시트 이름을 쪼개면 존재하지 않는 이름 두 개가 만들어진다.

    실측 1,460개 이름에 콤마는 없었지만 금지된 것은 아니다 — 통째로 해소되면 쪼개지 않는다.
    """
    xml = make_twb(
        worksheets=("S1,S2",),
        dashboards=(Dash(name="D", zones=("S1,S2",)),),
        extra_body=(
            "<actions><action caption='A' name='[Action1]'>"
            "<source dashboard='D' />"
            "<param name='exclude' value='S1,S2' />"
            "</action></actions>"
        ),
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def _q(value: str) -> str:
    from xml.sax.saxutils import quoteattr

    return quoteattr(value)
