"""규칙 계약 — 로직이 아니라 **모든 규칙이 지켜야 하는 약속**을 검사한다.

스모크(부팅)와 골든셋(실파일) 사이의 빈 층이다 (docs/TODO C2). 규칙을 구현할 때
여기가 먼저 깨지면 로직이 아니라 계약을 어긴 것이다.

계약:
1. `check(ctx)`를 받는다 — 모델만 받던 시절의 시그니처가 남아 있으면 안 된다
2. 조용히 통과하지 않는다 — 검사하지 못했으면 coverage에 남긴다 (02 S5)
3. 원본 트리를 변경하지 않는다 — 규칙 순서가 결과를 바꾸면 결정론이 깨진다 (02 S1-5)
4. 규칙 ⑥-a는 **정규화 전** 트리를 본다 — 정규화 후를 보면 항상 통과한다 (05 F7)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from tests.fixtures import Calc, Dash, Ds, make_ctx, make_twb
from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation import engine
from twb_lint.validation.registry import all_rules
from twb_lint.validation.rule import Rule


@pytest.fixture
def sample_xml() -> str:
    """작지만 규칙 4개가 볼 것을 다 담은 워크북."""
    return make_twb(
        manifest=("SortTagCleanup", "_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners"),
        datasources=(
            Ds(
                name="federated.abc",
                columns=("연차년월",),
                calcs=(Calc(name="Calculation_1", formula="SUM([연차년월])"),),
            ),
        ),
        worksheets=("매출",),
        dashboards=(Dash(name="대시보드", zones=("매출",)),),
        fcp_elements=("DashboardRoundedCorners",),
    )


@pytest.mark.parametrize("rule", all_rules(), ids=lambda r: r.id)
def test_rule_accepts_context_and_returns_findings(rule: Rule, sample_xml: str) -> None:
    """계약 1 — 모든 규칙은 `ValidationContext`를 받고 `list[Finding]`을 낸다."""
    result = rule.check(make_ctx(sample_xml))
    assert isinstance(result, list)
    assert all(isinstance(f, Finding) for f in result)


@pytest.mark.parametrize("rule", all_rules(), ids=lambda r: r.id)
def test_rule_does_not_mutate_the_tree(rule: Rule, sample_xml: str) -> None:
    """계약 3 — 규칙이 원본 트리를 건드리면 뒤에 도는 규칙의 입력이 달라진다."""
    ctx = make_ctx(sample_xml)
    before = etree.tostring(ctx.raw_tree)
    rule.check(ctx)
    assert etree.tostring(ctx.raw_tree) == before


@pytest.mark.parametrize("rule", all_rules(), ids=lambda r: r.id)
def test_rule_reports_when_it_cannot_check(rule: Rule) -> None:
    """계약 2 — 트리도 모델도 없는 상황에서 **조용히** 빈 리스트를 내면 안 된다.

    findings가 비었는데 coverage도 비면 "전부 검사했고 문제없음"으로 기록된다.
    입력이 없는데 그렇게 보고하는 규칙은 게이트를 거짓으로 통과시킨다.
    """
    from twb_lint.validation.context import ValidationContext

    ctx = ValidationContext(model=WorkbookModel(source=Path("nothing.twb")), raw_tree=None)
    findings = rule.check(ctx)
    assert findings or ctx.notes_for(rule.id), (
        f"규칙 {rule.id}가 입력 없이도 조용히 통과했다 — note_skip을 남겨야 한다"
    )


def test_manifest_rule_reads_the_raw_tree_not_the_normalized_one(sample_xml: str) -> None:
    """계약 4 — ⑥-a의 입력은 정규화 **전** 트리다 (05 F7 함의 2).

    정규화 사본에서는 fcp 기능명이 지워져 있어, 그걸 보는 구현은 어떤 파일에서도
    위반을 찾지 못한다. 규칙이 침묵하는 것과 구분되지 않으므로 **트리 쪽에서** 못 박는다.
    """
    ctx = make_ctx(sample_xml)
    from twb_lint import fcp

    assert fcp.features_in_tree(ctx.raw_tree) == {"DashboardRoundedCorners"}
    assert fcp.features_in_tree(ctx.normalized_tree()) == set()


def test_normalized_tree_is_cached(sample_xml: str) -> None:
    """1MB XML 사본을 규칙마다 다시 만들면 AC5(속도)와 충돌한다."""
    ctx = make_ctx(sample_xml)
    assert ctx.normalized_tree() is ctx.normalized_tree()


def test_engine_runs_every_registered_rule_and_records_coverage(sample_xml: str) -> None:
    """등록된 규칙은 하나도 빠짐없이 coverage에 나타난다."""
    ctx = make_ctx(sample_xml)
    report = engine.validate_model(ctx)
    assert {c.rule_id for c in report.coverage} == {r.id for r in all_rules()}


def test_unsupported_release_is_warned_not_silently_passed() -> None:
    """미지원 릴리스를 조용히 통과시키지 않는다 (02 S5)."""
    from twb_lint.validation.syntactic.xsd import XsdRule

    model = WorkbookModel(source=Path("x.twb"), source_build="2099.9.9 (x)")
    ctx = make_ctx(make_twb(), model=model)
    findings = XsdRule().check(ctx)

    assert [f.severity.value for f in findings] == ["warning"]
    assert ctx.notes_for("xsd.schema")


def test_supported_release_is_recognised() -> None:
    """표본의 실제 `source-build`가 지원 릴리스로 판정돼야 한다 (05 F4)."""
    from tests.fixtures.builder import DEFAULT_SOURCE_BUILD
    from twb_lint import config

    assert config.release_from_source_build(DEFAULT_SOURCE_BUILD) == "2026.1"
    assert config.is_supported("2026.1")
