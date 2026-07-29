"""규칙 ⑥(`manifest.gates`) — 매니페스트 게이트 일관성.

두 갈래의 **심각도가 다르다는 것**이 이 규칙의 핵심이다. ⑥-b는 로드 거부 메시지를
실측했으므로 ERROR, ⑥-a는 관계만 확인하고 인과는 미검증이라 WARNING이다.

입력 트리 선택(⑥-a는 정규화 **전**)은 `test_rules_contract.py`가 호출 감시로 잡는다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.manifest_gates import ManifestGatesRule


@pytest.fixture
def rule() -> ManifestGatesRule:
    return ManifestGatesRule()


def test_declared_fcp_feature_is_silent(rule: ManifestGatesRule) -> None:
    ctx = make_ctx(
        make_twb(
            manifest=("_.fcp.RoundedCorners.true...RoundedCorners",),
            fcp_elements=("RoundedCorners",),
        )
    )

    assert [f for f in rule.check(ctx) if f.location.startswith("fcp:")] == []


def test_undeclared_fcp_feature_is_a_warning(rule: ManifestGatesRule) -> None:
    """관계는 표본 10/10에서 확인했지만 **인과는 미검증**이다 — ERROR로 올리지 않는다."""
    ctx = make_ctx(make_twb(fcp_elements=("RoundedCorners",)))

    findings = [f for f in rule.check(ctx) if f.location.startswith("fcp:")]

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert "_.fcp.RoundedCorners.true...RoundedCorners" in findings[0].message


def test_table_gate_violation_is_an_error(rule: ManifestGatesRule) -> None:
    """⑥-b — 로드 거부 메시지를 실측한 쌍이라 ERROR다 (05 F5)."""
    ctx = make_ctx(make_twb(extra_body="<manual-sort />"))

    findings = [f for f in rule.check(ctx) if f.location == "manual-sort"]

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "SortTagCleanup" in findings[0].message


def test_table_gate_satisfied_is_silent(rule: ManifestGatesRule) -> None:
    ctx = make_ctx(make_twb(manifest=("SortTagCleanup",), extra_body="<manual-sort />"))

    assert [f for f in rule.check(ctx) if f.location == "manual-sort"] == []


def test_partially_satisfied_gate_names_only_the_missing_items(rule: ManifestGatesRule) -> None:
    """`edit-group-action`은 항목 2개를 요구한다 — 있는 것까지 요구하면 메시지가 틀린다."""
    ctx = make_ctx(make_twb(manifest=("GroupAction",), extra_body="<edit-group-action />"))

    findings = [f for f in rule.check(ctx) if f.location == "edit-group-action"]

    assert len(findings) == 1
    assert "GroupActionAddRemove" in findings[0].message
    assert "GroupAction," not in findings[0].message


def test_elements_outside_the_table_are_not_guessed(rule: ManifestGatesRule) -> None:
    """표에 없는 요소를 추측해 ERROR를 내지 않는다 (02 S1-6)."""
    ctx = make_ctx(make_twb(extra_body="<some-unknown-feature />"))

    assert [f.severity for f in rule.check(ctx)] == []


def test_unmapped_items_are_reported_as_partial_coverage(rule: ManifestGatesRule) -> None:
    """이름만 알고 매핑을 모르는 항목 16종은 **검사할 수 없다** — 그 사실을 보고한다."""
    ctx = make_ctx(make_twb())

    rule.check(ctx)

    notes = ctx.notes_for(rule.id)
    assert [n.status for n in notes] == [CoverageStatus.PARTIAL]
    assert "검사하지 못했다" in (notes[0].reason or "")


def test_missing_tree_reports_the_skip(rule: ManifestGatesRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
