"""`twb_lint.fieldref` — 표기 정규화 (07 G8 · 03 D3.6).

여기가 틀리면 규칙 ②가 정상본에서 **전량 dangling**을 뱉는다. 실측으로 확인된
형태만 골라 못 박는다.
"""

from __future__ import annotations

from twb_lint import fieldref


def test_calc_notation_stays_as_is() -> None:
    ref = fieldref.parse("[Calculation_2403322100842499]")

    assert ref is not None
    assert ref.datasource is None
    assert ref.names == ("Calculation_2403322100842499",)
    assert ref.special is None


def test_worksheet_notation_strips_role_and_kind() -> None:
    """`[ds].[usr:name:qk]` — 이 정규화가 없으면 규칙 ②가 성립하지 않는다."""
    ref = fieldref.parse("[federated.1wko1xr].[usr:Calculation_1737798957285376:qk]")

    assert ref is not None
    assert ref.datasource == "federated.1wko1xr"
    assert ref.names[0] == "Calculation_1737798957285376"


def test_the_raw_name_stays_a_candidate() -> None:
    """필드 이름 자체가 `a:b:nk`처럼 생겼을 수 있다 — 벗긴 것만 남기면 dangling이 된다."""
    ref = fieldref.parse("[none:scrn_seq:nk]")

    assert ref is not None
    assert ref.names == ("scrn_seq", "none:scrn_seq:nk")


def test_unknown_role_prefixes_are_still_stripped() -> None:
    """역할 접두사를 목록으로 고정하지 않는다 — 하나만 빠져도 그 필드가 dangling이 된다."""
    ref = fieldref.parse("[ds].[zzz:MyField:ok]")

    assert ref is not None
    assert ref.names[0] == "MyField"


def test_instance_index_suffix_is_dropped() -> None:
    """같은 필드를 여러 번 올리면 `:3`이 더 붙는다 (실측). 이름의 일부가 아니다."""
    ref = fieldref.parse("[ds].[usr:Calculation_1476389873000452:qk:3]")

    assert ref is not None
    assert ref.names[0] == "Calculation_1476389873000452"


def test_escaped_brackets_survive() -> None:
    """`]]`는 `]`의 이스케이프다 (실측: `[[P_Year]](복사본)_2403…]`)."""
    ref = fieldref.parse("[Parameters].[[P_Year]](복사본)_2403322090242050]")

    assert ref is not None
    assert ref.datasource == "Parameters"
    assert ref.names == ("[P_Year](복사본)_2403322090242050",)


def test_measure_axis_is_special() -> None:
    """과거 lint가 정확히 여기서 오탐했다 (함정 S9). 실측 1,294회."""
    for text in ("[:Measure Names]", "[:Measure Values]"):
        ref = fieldref.parse(text)
        assert ref is not None
        assert ref.special == "measure-axis"


def test_placeholder_and_internal_namespaces_are_special() -> None:
    placeholder = fieldref.parse("[federated.abc].[Multiple Values]")
    internal = fieldref.parse("[__tableau_internal_object_id__].[x]")

    assert placeholder is not None and placeholder.special == "placeholder"
    assert internal is not None and internal.special == "internal-object-id"


def test_find_all_reads_every_ref_in_a_string() -> None:
    """`computed-sort@using`처럼 속성 하나에 참조가 여러 개 들어가는 자리가 있다."""
    refs = fieldref.find_all("[a].[min:b:qk] + [c] - [:Measure Names]")

    assert [r.names[0] for r in refs] == ["b", "c", ":Measure Names"]
    assert [r.datasource for r in refs] == ["a", None, None]


def test_non_reference_text_yields_nothing() -> None:
    assert fieldref.parse("not a ref") is None
    assert fieldref.find_all("SUM(1 + 2)") == []
