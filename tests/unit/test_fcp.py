"""`twb_lint.fcp` — 정규화 전/후 트리 분리의 근거가 되는 실로직.

여기가 깨지면 L-A는 정상 파일을 전부 거부하고(오류의 98%가 fcp였다),
규칙 ⑥-a는 아무것도 못 잡는다.
"""

from __future__ import annotations

from lxml import etree

from tests.fixtures import make_twb
from twb_lint import fcp

SAMPLE_ELEMENT = "_.fcp.DashboardRoundedCorners.true...format"
SAMPLE_ATTR = "_.fcp.VConnDownstreamExtractsWithWarnings.true...user-specific"


def test_feature_of_reads_the_feature_name() -> None:
    assert fcp.feature_of(SAMPLE_ELEMENT) == "DashboardRoundedCorners"
    assert fcp.feature_of(SAMPLE_ATTR) == "VConnDownstreamExtractsWithWarnings"
    assert fcp.feature_of("format") is None


def test_strip_removes_only_the_prefix() -> None:
    assert fcp.strip_prefix(SAMPLE_ELEMENT) == "format"
    assert fcp.strip_prefix("format") == "format"
    # false 변형도 같은 문법이다
    assert fcp.strip_prefix("_.fcp.Foo.false...bar") == "bar"


def test_expected_manifest_item_is_derived_not_looked_up() -> None:
    """규칙 ⑥-a가 대응표 없이 성립하는 이유 (docs/05-xsd-spike.md F7)."""
    assert (
        fcp.expected_manifest_item("DashboardRoundedCorners")
        == "_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners"
    )


def test_features_in_tree_covers_attributes_too() -> None:
    """속성 키에도 접두사가 붙는다 — 요소만 훑으면 놓친다 (05 F2)."""
    xml = make_twb(
        fcp_elements=("DashboardRoundedCorners",),
        extra_body=f"<extract {SAMPLE_ATTR}='yes' />",
    )
    root = etree.fromstring(xml.encode("utf-8"))
    assert fcp.features_in_tree(root) == {
        "DashboardRoundedCorners",
        "VConnDownstreamExtractsWithWarnings",
    }


def test_manifest_items_are_not_counted_as_usage() -> None:
    """매니페스트 항목은 **선언**이지 사용이 아니다.

    포함해 버리면 규칙 ⑥-a가 자기 자신을 근거로 항상 통과한다 — 규칙이 무의미해진다.
    """
    xml = make_twb(
        manifest=("_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners",),
    )
    root = etree.fromstring(xml.encode("utf-8"))
    assert fcp.features_in_tree(root) == set()
    assert fcp.manifest_items(root) == {
        "_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners"
    }


def test_manifest_items_keep_the_prefix() -> None:
    """벗겨서 담으면 `.true...`와 `.false...`가 구분되지 않는다."""
    xml = make_twb(manifest=("_.fcp.Foo.false...Foo", "SortTagCleanup"))
    root = etree.fromstring(xml.encode("utf-8"))
    assert fcp.manifest_items(root) == {"_.fcp.Foo.false...Foo", "SortTagCleanup"}


def test_normalize_tree_does_not_touch_the_original() -> None:
    """원본 불변 — 규칙 ⑥-a가 원본을 필요로 한다 (05 F7 함의 2)."""
    xml = make_twb(fcp_elements=("DashboardRoundedCorners",))
    root = etree.fromstring(xml.encode("utf-8"))

    normalized = fcp.normalize_tree(root)

    assert fcp.features_in_tree(root) == {"DashboardRoundedCorners"}  # 원본 그대로
    assert fcp.features_in_tree(normalized) == set()  # 사본에서는 정보가 지워졌다
    assert any(el.tag == "format" for el in normalized.iter())


def test_normalize_tree_strips_attribute_keys() -> None:
    xml = make_twb(extra_body=f"<extract {SAMPLE_ATTR}='yes' />")
    root = etree.fromstring(xml.encode("utf-8"))
    normalized = fcp.normalize_tree(root)

    extract = next(el for el in normalized.iter() if el.tag == "extract")
    assert extract.attrib == {"user-specific": "yes"}
