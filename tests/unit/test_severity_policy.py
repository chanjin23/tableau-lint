"""A3 — L-A 위반의 심각도 정책을 고정한다 (docs/03-design.md D3, 05 F8).

**이 정책이 틀리면 조용히 AC7이 무너진다.** 정상 워크북이 ERROR를 받고, 사용자는 게이트를
끄고, 그 순간 프로젝트 목적이 사라진다. 그런데 정책은 문자열 매칭에 의존한다 — 실측상
거짓양성과 진짜 로드 거부가 **같은 오류코드**(`SCHEMAV_ELEMENT_CONTENT`)를 쓰기 때문이다.

여기 없으면 정책을 뒤집어도 아무 테스트가 깨지지 않는다. 실제로 확인했다:
`Missing child element` 분기를 WARNING → ERROR로 바꿔도 전 게이트가 green이었다.

메시지 원문은 2026-07-29 실측에서 그대로 가져왔다 (lxml 6.x / libxml2).
"""

from __future__ import annotations

import pytest

from twb_lint.models import Severity
from twb_lint.validation.syntactic.xsd import (
    MISSING_CHILD_MARKER,
    NOT_EXPECTED_MARKER,
    severity_for,
)

# 실측 메시지 (docs/05-xsd-spike.md F8). 문자열을 손대면 정책이 조용히 무력화되므로
# 여기 박아 두고 회귀로 잡는다.
MSG_ENUM = (
    "Element 'column', attribute 'param-domain-type': [facet 'enumeration'] "
    "The value 'all' is not an element of the set {'any', 'list', 'range'}."
)
MSG_DATATYPE = (
    "Element 'thumbnail', attribute 'width': 'abc' is not a valid value "
    "of the atomic type 'xs:int'."
)
MSG_NOT_EXPECTED = (
    "Element 'column': This element is not expected. "
    "Expected is one of ( semantic-values, date-options, default-date-format )."
)
MSG_MISSING_CHILD = (
    "Element 'workbook': Missing child element(s). "
    "Expected is one of ( external, referenced-extensions, explain-data )."
)


def test_enum_violation_is_error() -> None:
    """R7 실측 — `param-domain-type='all'`은 D2E8DA72로 로드 거부된다."""
    assert severity_for("SCHEMAV_CVC_ENUMERATION_VALID", MSG_ENUM) is Severity.ERROR


def test_datatype_violation_is_error() -> None:
    assert severity_for("SCHEMAV_CVC_DATATYPE_VALID_1_2_1", MSG_DATATYPE) is Severity.ERROR


def test_element_not_expected_is_error() -> None:
    """R4·R5·R6 실측 — 자식 순서 위반은 실제 로드 거부다."""
    assert severity_for("SCHEMAV_ELEMENT_CONTENT", MSG_NOT_EXPECTED) is Severity.ERROR


def test_missing_child_is_only_a_warning() -> None:
    """**정책의 핵심.** `explain-data`가 정확히 이 클래스의 거짓양성이었다 (05 F3).

    ERROR로 올리면 vendored XSD의 과엄격 패치가 풀리는 순간 정상본 9개가 전부
    ERROR를 받는다 — AC7 붕괴. 같은 오류코드를 쓰는 위 케이스와 **메시지로만** 갈린다.
    """
    assert severity_for("SCHEMAV_ELEMENT_CONTENT", MSG_MISSING_CHILD) is Severity.WARNING


def test_same_error_code_splits_by_message() -> None:
    """거짓양성과 진짜 오류가 같은 코드라는 실측을 테스트로 못 박는다 (05 F8).

    이 단언이 성립하지 않게 되면(예: libxml2가 코드를 분리하면) 정책을 단순화할 수 있다.
    """
    code = "SCHEMAV_ELEMENT_CONTENT"
    assert severity_for(code, MSG_NOT_EXPECTED) is Severity.ERROR
    assert severity_for(code, MSG_MISSING_CHILD) is Severity.WARNING


@pytest.mark.parametrize(
    "type_name",
    ["SCHEMAV_UNKNOWN_FUTURE_CODE", "", "SCHEMAP_SRC_RESOLVE"],
)
def test_unclassified_falls_back_to_warning(type_name: str) -> None:
    """분류하지 못한 오류는 WARNING으로 떨어진다 — 확신 없으면 ERROR를 내지 않는다 (S1-6)."""
    assert severity_for(type_name, "무언가 새로운 오류") is Severity.WARNING


def test_markers_are_the_actual_libxml2_wording() -> None:
    """마커 상수가 실제 메시지와 어긋나면 정책 전체가 침묵한다."""
    assert NOT_EXPECTED_MARKER in MSG_NOT_EXPECTED
    assert MISSING_CHILD_MARKER in MSG_MISSING_CHILD
    # 서로의 메시지에는 걸리지 않아야 한다 (오분류 방지).
    assert NOT_EXPECTED_MARKER not in MSG_MISSING_CHILD
    assert MISSING_CHILD_MARKER not in MSG_NOT_EXPECTED
