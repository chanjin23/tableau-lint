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


@pytest.mark.parametrize(
    ("element", "item"),
    [
        ("computed-sort", "SortTagCleanup"),
        ("edit-parameter-action", "ParameterAction"),
        ("clear-option", "ParameterActionClearSelection"),
    ],
)
def test_gates_measured_on_2026_07_30(rule: ManifestGatesRule, element: str, item: str) -> None:
    """2026-07-30 실측분 — MA_003 매출표가 이 3건으로 로드 거부됐다 (D2E8DA72).

    거부 메시지는 `edit-parameter-action`·`computed-sort`만 지목했지만
    `clear-option`도 같은 계열이라 표에 넣었다 (근거는 manifest_gates.json의 source).
    """
    ctx = make_ctx(make_twb(extra_body=f"<{element} />"))

    findings = [f for f in rule.check(ctx) if f.location == element]

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert item in findings[0].message


def test_simple_id_without_manifest_is_an_error(rule: ManifestGatesRule) -> None:
    """2026-08-10 실측 — 매니페스트 블록이 통째로 없는 저작본이 로드 거부됐다 (D2E8DA72).

    `passed=true`로 통과시켰던 결함이다. 거부 메시지가 요소를 직접 지목했다:
    `element 'simple-id' is not allowed for content model '…,table)'`.
    """
    ctx = make_ctx(make_twb(extra_body="<simple-id uuid='{0B5E7A10-0001-4A00-9000-000000A1}' />"))

    findings = [f for f in rule.check(ctx) if f.location == "simple-id"]

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "SheetIdentifierTracking" in findings[0].message


def test_simple_id_needs_only_sheet_identifier_tracking(rule: ManifestGatesRule) -> None:
    """분리 실험 실측 — `WindowsPersistSimpleIdentifiers`만 빼면 **열린다**.

    최초안은 둘 다 요구했다. 그건 과요구고, 정상 파일을 때린다 (AC7).
    실험: SIT만 뺀 변형은 로드 거부, WPSI만 뺀 변형은 정상 로드 (2026-08-10).
    """
    ctx = make_ctx(
        make_twb(
            manifest=("SheetIdentifierTracking",),
            extra_body="<simple-id uuid='{0B5E7A10-0001-4A00-9000-000000A1}' />",
        )
    )

    assert [f for f in rule.check(ctx) if f.location == "simple-id"] == []


def test_gate_finding_carries_the_first_occurrence_line(rule: ManifestGatesRule) -> None:
    """Tableau 거부 메시지가 줄 기준이라 대조가 되려면 줄번호가 있어야 한다."""
    ctx = make_ctx(make_twb(extra_body="<manual-sort />\n<manual-sort />"))

    findings = [f for f in rule.check(ctx) if f.location == "manual-sort"]

    assert len(findings) == 1, "요소가 여러 번 나와도 고칠 곳은 매니페스트 1군데다"
    assert findings[0].line is not None


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
    """이름만 알고 매핑을 모르는 항목 12종은 **검사할 수 없다** — 그 사실을 보고한다."""
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


# 2026-09-16 실측 — 동적 존 표시(datagraph) 게이트 (05 F5-o · 06 R33)


@pytest.mark.parametrize(
    ("element", "item"),
    [
        ("datagraph", "DatagraphCoreV1"),
        ("single-value-field-node", "DatagraphNodeSingleValueFieldV1"),
        ("dashboard-zone-visibility-node", "DatagraphNodeDashboardZoneVisibilityV1"),
    ],
)
def test_datagraph_gates(rule: ManifestGatesRule, element: str, item: str) -> None:
    """`<datagraph>`는 **동적 존 표시**의 저장 형식이다 (2026-09-16 MA_004 로드 거부).

    거부 메시지가 요소를 직접 지목했다:
    `no declaration found for element 'datagraph'`.
    """
    ctx = make_ctx(make_twb(extra_body=f"<{element} />"))

    findings = [f for f in rule.check(ctx) if f.location == element]

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert item in findings[0].message


def test_datagraph_gates_are_not_lumped_together(rule: ManifestGatesRule) -> None:
    """네 항목이 완전히 동시출현(15:0)해도 **뭉뚱그려 요구하지 않는다**.

    `simple-id`에서 과요구가 드러난 전례가 있다 — 이름이 대응하는 요소에만 건다.
    `<datagraph>`만 쓰는 파일에 노드 항목까지 요구하면 정상 파일을 때릴 수 있다.
    """
    ctx = make_ctx(make_twb(manifest=("DatagraphCoreV1",), extra_body="<datagraph />"))

    assert [f for f in rule.check(ctx) if f.location == "datagraph"] == []


def test_zone_visibility_control_stays_unmapped(rule: ManifestGatesRule) -> None:
    """`ZoneVisibilityControl`은 표에 넣지 않았다 — 대응이 요소가 아니라 속성이다.

    정상본 15:0으로 `zone@hidden-by-user`와 붙어 다니지만, 이 표는 요소 단위라
    담을 자리가 없다. **모른다고 말한다** — `known_items_unmapped`에 남겨
    `note_partial`로 보고된다 (02 AC9).
    """
    ctx = make_ctx(make_twb(extra_body="<zone hidden-by-user='true' id='9' />"))

    assert [f for f in rule.check(ctx) if "ZoneVisibilityControl" in f.message] == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.PARTIAL]
