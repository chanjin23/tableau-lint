"""규칙 ⑮(`format.fcp_prefix`) — 신기능 서식의 fcp 접두.

⑥과 방향이 반대다: ⑥은 "fcp를 썼는데 매니페스트가 없다", ⑮는 "fcp로 썼어야 하는데
맨 이름으로 썼다". 접두가 없으면 기능이 트리에 나타나지 않아 ⑥이 볼 대상 자체가 없다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.format_fcp_prefix import FormatFcpPrefixRule

FCP_FORMAT = "_.fcp.DashboardRoundedCorners.true...format"

BROKEN_CORNER = (
    "<zone-style>"
    "<format attr='border-width' value='1' />"
    "<format attr='corner-radius-top-left' value='12' />"
    "</zone-style>"
)
GOOD_CORNER = (
    "<zone-style>"
    "<format attr='border-width' value='1' />"
    f"<{FCP_FORMAT} attr='corner-radius-top-left' value='12' />"
    "</zone-style>"
)
# 거짓양성 함정 — 같은 `<zone-style>`, 같은 맨 `<format>`이지만 구기능이다.
# 실파일 254개에서 이 표기가 318,930건이다. 하나라도 잡으면 규칙이 게이트를 무력화한다.
PLAIN_ZONE_STYLE = (
    "<zone-style>"
    "<format attr='margin' value='0' />"
    "<format attr='background-color' value='#ffffff' />"
    "</zone-style>"
)
BROKEN_CTRL = (
    "<style><style-rule element='parameter-ctrl'>"
    "<format attr='font-size' field='[Parameters].[매개 변수 1]' value='11' />"
    "</style-rule></style>"
)
# 함정 2 — `@field`가 붙은 서식이라도 `cell`·`label`은 맨 표기가 정본이다
# (실측 cell 11,555건 · label 10,876건, fcp 0건).
FIELD_SCOPED_CELL = (
    "<style><style-rule element='cell'>"
    "<format attr='text-format' field='[ds].[usr:Calculation_A:qk]' value='n#,##0.0' />"
    "</style-rule></style>"
)


@pytest.fixture
def rule() -> FormatFcpPrefixRule:
    return FormatFcpPrefixRule()


def test_corner_radius_without_the_prefix_is_an_error(rule: FormatFcpPrefixRule) -> None:
    """실측: MA_004가 이 표기 88건으로 로드 거부됐다 (D2E8DA72, 2026-09-07)."""
    findings = rule.check(make_ctx(make_twb(extra_body=BROKEN_CORNER)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "DashboardRoundedCorners" in findings[0].fix
    assert findings[0].line is not None


def test_control_formatting_without_the_prefix_is_a_warning(rule: FormatFcpPrefixRule) -> None:
    """상관(468 : 0)만 확인됐고 로드 거부는 미실측이라 WARNING이다 (02 S1-6)."""
    findings = rule.check(make_ctx(make_twb(extra_body=BROKEN_CTRL)))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "IndividualControlFormatting" in findings[0].fix


@pytest.mark.parametrize("body", [GOOD_CORNER, PLAIN_ZONE_STYLE, FIELD_SCOPED_CELL])
def test_observed_shapes_are_silent(rule: FormatFcpPrefixRule, body: str) -> None:
    """정본 표기 · 구기능 존 스타일 · 필드 한정 셀 서식은 전부 정상이다."""
    assert rule.check(make_ctx(make_twb(extra_body=body))) == []


def test_workbook_without_formats_reports_that_it_checked_nothing(
    rule: FormatFcpPrefixRule,
) -> None:
    """검사할 게 없었다는 사실을 남긴다 — 조용한 통과와 구분되지 않으면 안 된다 (02 S5)."""
    ctx = make_ctx(make_twb())

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
