"""규칙 ⑲(`palette.instance_declared`) — 팔레트 키는 데이터 원본 직속에도 선언돼 있어야 한다.

**증상이 조용하다.** 파일은 열리고 오류 대화상자도 없다. 색만 기본 색으로 나오고,
저장하면 팔레트 항목이 사라진다 (2026-10-13 MA_028 제보, 05 F5-q).

함정은 둘이다.

1. **워크시트의 `<datasource-dependencies>` 선언은 대신하지 못한다** — 제보 파일이 정확히
   그 모양이었다. 규칙이 "어디서든 선언돼 있으면 통과"로 느슨해지면 이 파일을 못 잡는다
2. **파생이 아닌 키(`[:Measure Names]`)를 걸면 안 된다** — 키 인스턴스 자체가 없는 내장
   필드다. 실파일 782건이 이 모양이고 전부 정상이다
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.palette_instances import PaletteInstancesRule

_KEY = "[usr:Calculation_9028000000000022:nk]"

_INSTANCE = (
    "<column-instance column='[Calculation_9028000000000022]' derivation='User' "
    f"name='{_KEY}' pivot='key' type='nominal' />"
)


def _ds(*, instance: str = "", field: str = _KEY, enc_type: str = "palette") -> str:
    return (
        "<datasources><datasource caption='MA_028' name='federated.x'>"
        "<column datatype='string' name='[Calculation_9028000000000022]' "
        "role='measure' type='nominal' />"
        f"{instance}"
        "<style><style-rule element='mark'>"
        f"<encoding attr='color' field='{field}' type='{enc_type}'>"
        "<map to='#2563eb'><bucket>&quot;달성&quot;</bucket></map>"
        "</encoding></style-rule></style>"
        "</datasource></datasources>"
    )


@pytest.fixture
def rule() -> PaletteInstancesRule:
    return PaletteInstancesRule()


def test_declared_palette_key_is_silent(rule: PaletteInstancesRule) -> None:
    ctx = make_ctx(make_twb(extra_body=_ds(instance=_INSTANCE)))

    assert rule.check(ctx) == []


def test_undeclared_palette_key_is_a_warning(rule: PaletteInstancesRule) -> None:
    """제보의 모양 — 팔레트는 있는데 데이터 원본 직속 인스턴스가 없다.

    파일은 열리므로 층 2(설정이 버려진다) → WARNING이다. `passed`를 막지 않는다.
    """
    ctx = make_ctx(make_twb(extra_body=_ds()))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert _KEY in findings[0].message
    assert findings[0].line is not None
    # fix 가 그대로 붙여 넣을 수 있는 모양이어야 한다
    assert f"name='{_KEY}'" in findings[0].fix
    assert "derivation='User'" in findings[0].fix
    assert "type='nominal'" in findings[0].fix


def test_worksheet_dependency_does_not_stand_in(rule: PaletteInstancesRule) -> None:
    """**제보 파일의 모양** — 인스턴스가 워크시트 `<datasource-dependencies>`에만 있다.

    이 선언은 데이터 원본 직속을 대신하지 못한다. 규칙이 문서 전체에서 선언을 찾도록
    느슨해지면 이 테스트가 깨진다.
    """
    sheet = (
        "<worksheets><worksheet name='시트'><table><view>"
        "<datasource-dependencies datasource='federated.x'>"
        f"{_INSTANCE}</datasource-dependencies></view></table></worksheet></worksheets>"
    )
    ctx = make_ctx(make_twb(extra_body=_ds() + sheet))

    assert len(rule.check(ctx)) == 1


def test_non_derived_key_is_not_judged(rule: PaletteInstancesRule) -> None:
    """`[:Measure Names]`는 내장 필드라 키 인스턴스가 없다 — 정상본 782건이 이 모양이다."""
    ctx = make_ctx(make_twb(extra_body=_ds(field="[:Measure Names]")))

    assert rule.check(ctx) == []


def test_only_palette_encodings_are_judged(rule: PaletteInstancesRule) -> None:
    """`type='palette'`가 아닌 encoding(예: 필드 단위 색 범위)은 대상이 아니다."""
    ctx = make_ctx(make_twb(extra_body=_ds(enc_type="interpolated")))

    assert rule.check(ctx) == []


def test_each_undeclared_key_gets_its_own_finding(rule: PaletteInstancesRule) -> None:
    second = (
        "<encoding attr='color' field='[none:Calculation_9028000000000038:nk]' type='palette'>"
        "<map to='#f7474a'><bucket>&quot;미달&quot;</bucket></map></encoding>"
    )
    body = _ds(instance=_INSTANCE).replace("</style-rule>", f"{second}</style-rule>")
    ctx = make_ctx(make_twb(extra_body=body))

    findings = rule.check(ctx)

    assert len(findings) == 1
    assert "none:Calculation_9028000000000038:nk" in findings[0].message


def test_no_palette_is_reported_as_not_checked(rule: PaletteInstancesRule) -> None:
    """침묵과 **판정 대상 아님**은 다르다 (02 S5)."""
    ctx = make_ctx(make_twb(worksheets=("매출",)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: PaletteInstancesRule) -> None:
    ctx = make_ctx(make_twb(extra_body=_ds()))
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
