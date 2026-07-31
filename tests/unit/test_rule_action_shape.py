"""규칙 ⑬(`action.shape`) — 동작의 모양.

⑩ `action.refs`가 *가리키는 대상이 실재하는가*를 보는 반면 여기는 *Tableau가 아는
배선 모양인가*를 본다. 실측(실파일 63개 · 동작 140건)이 `<action>`의 모양을 셋으로
확정했다 — 필터(`tsc:tsl-filter`+`<link>` 14) · 하이라이트(`tsc:brush` 17) ·
URL(명령 없이 `<link expression='http…'>` 1). 반례 0.

테스트의 절반은 **정상 모양에서 침묵하는가**다. 목록이 좁아 거짓양성이 나면
게이트가 통째로 무력해진다 (02 AC7).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Dash, Ds, make_twb
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.semantic.action_shape import ActionShapeRule


@pytest.fixture
def rule() -> ActionShapeRule:
    return ActionShapeRule()


def ctx_for(tmp_path: Path, xml: str) -> ValidationContext:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def workbook(actions: str) -> str:
    return make_twb(
        datasources=(
            Ds(name="federated.abc", columns=("accs_nm",)),
            Ds(name="Parameters", columns=("P_MONTH",)),
        ),
        worksheets=("S1", "S2"),
        dashboards=(Dash(name="D", zones=("S1", "S2")),),
        extra_body=f"<actions>{actions}</actions>",
    )


FILTER_LINK = (
    "<link caption='필터' delimiter=',' expression='tsl:D?accs_nm~s0=&lt;accs_nm~na&gt;' "
    "include-null='true' multi-select='true' url-escape='true' />"
)

SHAPES = {
    "필터": (
        "<action caption='필터' name='[Action1]'>"
        "<activation type='on-select' />"
        "<source dashboard='D' type='sheet' worksheet='S1' />"
        f"{FILTER_LINK}"
        "<command command='tsc:tsl-filter'>"
        "<param name='target' value='D' />"
        "<param name='exclude' value='S1' />"
        "</command></action>"
    ),
    "하이라이트": (
        "<action caption='하이라이트' name='[Action2]'>"
        "<activation type='on-select' />"
        "<source dashboard='D' type='sheet' worksheet='S1' />"
        "<command command='tsc:brush'>"
        "<param name='target' value='D' />"
        "<param name='exclude' value='S1' />"
        "<param name='field-captions' value='제품' />"
        "</command></action>"
    ),
    "URL": (
        "<action caption='하이퍼링크1' name='[Action3]'>"
        "<activation type='on-select' />"
        "<source dashboard='D' type='sheet' worksheet='S1' />"
        "<link caption='' expression='http://10.15.12.3/#/home' />"
        "</action>"
    ),
    "매개변수": (
        "<edit-parameter-action caption='P' name='[Action4]'>"
        "<source dashboard='D' />"
        "<param name='target-parameter' value='[Parameters].[P_MONTH]' />"
        "<param name='source-field' value='[federated.abc].[none:accs_nm:nk]' />"
        "</edit-parameter-action>"
    ),
    "집합": (
        "<edit-group-action caption='G' name='[Action5]'>"
        "<source dashboard='D' />"
        "<param name='selection-clear-set-option' value='keep' />"
        "<param name='target-group' value='[federated.abc].[accs_nm 집합]' />"
        "</edit-group-action>"
    ),
}


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_each_measured_shape_is_silent(
    tmp_path: Path, rule: ActionShapeRule, name: str
) -> None:
    """실파일에서 관측된 다섯 모양 전부에서 침묵해야 한다."""
    assert rule.check(ctx_for(tmp_path, workbook(SHAPES[name]))) == []


def test_all_shapes_together_are_silent(tmp_path: Path, rule: ActionShapeRule) -> None:
    assert rule.check(ctx_for(tmp_path, workbook("".join(SHAPES.values())))) == []


def test_an_unknown_command_is_a_warning(tmp_path: Path, rule: ActionShapeRule) -> None:
    """`tsc:filter` — 2026-07-31 저작본이 낸 실제 결함. XSD도 ⑩도 통과한다."""
    xml = workbook(
        "<action caption='제품 필터' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' />"
        "<command command='tsc:filter'>"
        "<param name='target' value='D' />"
        "</command></action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING], (
        "우리 목록이 불완전할 수 있다 — 목록 밖은 '틀렸다'가 아니라 '모른다'다"
    )
    assert "tsc:filter" in findings[0].message


def test_a_filter_action_without_a_link_is_a_warning(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """필드 매핑이 `<link expression>`에 실린다 — 없으면 필드 열이 빈다 (실측 14:0)."""
    xml = workbook(
        "<action caption='필터' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' />"
        "<command command='tsc:tsl-filter'>"
        "<param name='target' value='D' />"
        "</command></action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "link" in findings[0].message


def test_an_action_with_neither_command_nor_link_is_a_warning(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    xml = workbook(
        "<action caption='빈것' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' />"
        "</action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "아무 일도 하지 않는다" in findings[0].message


def test_a_param_name_in_the_wrong_place_is_a_warning(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """`source-field`는 없는 이름이 아니라 **자리가 틀린** 이름이다.

    `edit-parameter-action`에서는 70건 관측된다. `<action>`에 붙으면 0건이다 —
    전역 화이트리스트로는 못 잡고 종류별로 갈라야 잡힌다.
    """
    xml = workbook(
        "<action caption='필터' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' />"
        f"{FILTER_LINK}"
        "<command command='tsc:tsl-filter'>"
        "<param name='source-field' value='[federated.abc].[none:accs_nm:nk]' />"
        "</command></action>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "source-field" in findings[0].message


def test_the_same_name_in_its_own_place_is_silent(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """거짓양성 함정 — 바로 위 테스트와 param 이름이 같고 자리만 다르다."""
    assert rule.check(ctx_for(tmp_path, workbook(SHAPES["매개변수"]))) == []


def test_an_unsampled_action_kind_is_reported_as_partial(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """`<nav-action>`은 실파일 0건이다 — 어휘를 모르면 판정하지 않고 말한다."""
    xml = workbook(
        "<nav-action caption='이동' name='[Action1]'>"
        "<source dashboard='D' worksheet='S1' />"
        "<params><param name='무엇이든' value='x' /></params>"
        "</nav-action>"
    )
    ctx = ctx_for(tmp_path, xml)

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("action.shape")] == [CoverageStatus.PARTIAL]


def test_a_workbook_without_actions_says_so(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """조용히 빈 리스트를 내면 "동작을 전부 검사했다"로 읽힌다 (02 S5)."""
    ctx = ctx_for(tmp_path, make_twb(worksheets=("S1",)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("action.shape")] == [CoverageStatus.SKIPPED]


def test_the_same_unknown_command_is_reported_once(
    tmp_path: Path, rule: ActionShapeRule
) -> None:
    """한 파일에 같은 결함이 여러 번 나와도 finding은 1건이다 (⑩과 같은 원칙)."""
    one = (
        "<action caption='필터{i}' name='[Action{i}]'>"
        "<source dashboard='D' worksheet='S1' />"
        "<command command='tsc:filter' /></action>"
    )
    xml = workbook("".join(one.format(i=i) for i in range(6)))

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "6곳" in findings[0].message
