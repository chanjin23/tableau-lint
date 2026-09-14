"""규칙 ⑰(`zone.shape`) — 존의 종류가 요구하는 속성.

규칙 ③과 묻는 것이 다르다: ③은 "가리키는 이름이 실재하는가", ⑰은 "그 종류의 존이
갖춰야 할 것을 갖췄는가". ⑬을 ⑩에서 가른 기준과 같다.

**WARNING이다 — 증상 귀속에 실패했다.** CB5AF9D4를 쫓다 나왔고 처음엔 ERROR였는데,
`mode`를 채운 고침본이 **여전히 안 열렸다** (05 F5-n). 남은 것은 모양 불변식 하나뿐이다
— 실파일 238개에서 2,475 : 0. 정상본을 때리지는 않지만 증상을 막는다고 말할 수도 없다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.zone_shape import ZoneShapeRule


@pytest.fixture
def rule() -> ZoneShapeRule:
    return ZoneShapeRule()


def ctx_for(zones_xml: str):
    return make_twb(
        extra_body=(
            "<dashboards><dashboard name='대시보드'><zones>"
            f"<zone type-v2='layout-basic' id='1'>{zones_xml}</zone>"
            "</zones></dashboard></dashboards>"
        )
    )


PARAMCTRL = (
    "<zone type-v2='paramctrl' id='200' param='[Parameters].[P_YEAR]' "
    "x='0' y='0' w='100' h='100'{mode} />"
)


def test_paramctrl_without_mode_is_a_warning(rule: ZoneShapeRule) -> None:
    """정상본 2,475개는 전부 `mode`를 갖는다 — 모양 불변식이다.

    **WARNING이다.** 한때 ERROR였으나 `mode`를 채운 고침본이 여전히 안 열려
    증상 귀속이 깨졌다 (05 F5-n). 상관만으로 게이트를 막지 않는다 (02 S1-6).
    """
    ctx = make_ctx(ctx_for(PARAMCTRL.format(mode="")))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "mode" in findings[0].message
    assert "P_YEAR" in findings[0].message  # 사람이 찾아갈 수 있어야 한다
    assert "compact" in (findings[0].fix or "")
    assert findings[0].line is not None


@pytest.mark.parametrize("mode", ["compact", "type_in"])
def test_paramctrl_with_mode_is_silent(rule: ZoneShapeRule, mode: str) -> None:
    """실측에 나온 두 값 — `compact` 2,473 · `type_in` 2."""
    ctx = make_ctx(ctx_for(PARAMCTRL.format(mode=f" mode='{mode}'")))

    assert rule.check(ctx) == []


@pytest.mark.parametrize("type_v2", ["empty", "text", "layout-flow", "layout-basic"])
def test_other_zone_types_are_not_judged(rule: ZoneShapeRule, type_v2: str) -> None:
    """거짓양성 함정 — 다른 종류의 필수 속성은 **재지 않았다**.

    추측해서 넓히면 그 자리가 통째로 거짓양성이 된다 (02 S1-6 · AC7).
    """
    zone = f"<zone type-v2='{type_v2}' id='9' x='0' y='0' w='1' h='1' />"

    assert rule.check(make_ctx(ctx_for(zone))) == []


def test_sheet_zone_is_not_judged(rule: ZoneShapeRule) -> None:
    """`type-v2`가 없는 존은 워크시트 존이다 — 여기 필수 속성 표가 없다."""
    zone = "<zone name='SEC01_매출' id='9' x='0' y='0' w='1' h='1' />"

    assert rule.check(make_ctx(ctx_for(zone))) == []


def test_workbook_without_zones_reports_the_skip(rule: ZoneShapeRule) -> None:
    ctx = make_ctx(make_twb())

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_zones_of_unknown_types_report_the_skip(rule: ZoneShapeRule) -> None:
    """존은 있는데 아는 종류가 없으면 **검사하지 못했다고 말한다** (02 AC9).

    빈 리스트를 조용히 반환하면 "전부 검사했고 문제없음"으로 기록된다.
    """
    ctx = make_ctx(ctx_for("<zone type-v2='empty' id='9' x='0' y='0' w='1' h='1' />"))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: ZoneShapeRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
