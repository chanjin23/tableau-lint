"""`twb_lint.io.twb` — 파싱·직렬화가 안전 파서를 실제로 쓰는지.

`test_safety.py`는 `make_parser()`를 단독으로 검사한다. 여기서는 `parse()`가 그 파서를
**실제로 통과시키는지**를 본다 — 파서가 있어도 `etree.parse(path)`를 그냥 부르면
기본 파서(엔티티 해석 활성)가 쓰인다 (07 G10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Calc, Ds, make_twb
from twb_lint.io import safety, twb

SECRET = "TOP-SECRET-CONTENTS"


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_returns_the_root_element(tmp_path: Path) -> None:
    src = write(tmp_path / "wb.twb", make_twb(worksheets=("Sheet 1",)))

    root = twb.parse(src)

    assert root.tag == "workbook"
    assert root.get("source-build", "").startswith("2026.1")


def test_parse_does_not_resolve_external_entities(tmp_path: Path) -> None:
    """XXE — `parse()`가 안전 파서를 쓰지 않으면 여기서 비밀이 새어 나온다."""
    secret = write(tmp_path / "secret.txt", SECRET)
    src = write(
        tmp_path / "evil.twb",
        f'<?xml version="1.0"?>\n'
        f'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///{secret.as_posix()}">]>\n'
        f"<workbook>&xxe;</workbook>",
    )

    root = twb.parse(src)

    assert SECRET not in (root.text or "")


def test_malformed_xml_is_reported_with_a_line_number(tmp_path: Path) -> None:
    src = write(tmp_path / "broken.twb", "<workbook>\n  <worksheets>\n</workbook>")

    with pytest.raises(twb.MalformedXmlError) as exc:
        twb.parse(src)

    assert exc.value.problem.kind is safety.ProblemKind.MALFORMED_XML
    assert "line 3" in exc.value.problem.detail


def test_missing_file_raises_input_error_not_oserror(tmp_path: Path) -> None:
    """호출자가 io의 실패를 한 종류로 잡을 수 있어야 한다 (03 D9.1)."""
    with pytest.raises(safety.InputError) as exc:
        twb.parse(tmp_path / "nope.twb")

    assert exc.value.problem.kind is safety.ProblemKind.UNREADABLE


def test_read_version_returns_the_min_compatible_version(tmp_path: Path) -> None:
    """`18.1`이 나온다 — 저작 버전이 아니라 최소 호환 버전이다 (07 G1)."""
    src = write(tmp_path / "wb.twb", make_twb())

    assert twb.read_version(src) == "18.1"


def test_read_version_is_none_when_absent(tmp_path: Path) -> None:
    src = write(tmp_path / "wb.twb", "<workbook />")

    assert twb.read_version(src) is None


def test_serialize_roundtrips_structure_and_non_ascii(tmp_path: Path) -> None:
    """한글 caption이 이스케이프되면 골든셋 diff가 통째로 뒤집힌다."""
    xml = make_twb(
        datasources=(
            Ds(
                name="federated.abc",
                caption="현금흐름",
                calcs=(Calc(name="Calculation_1", formula="SUM([매출])", caption="매출계"),),
            ),
        ),
        worksheets=("시트 1",),
    )
    root = twb.parse(write(tmp_path / "in.twb", xml))

    out = twb.serialize(root, tmp_path / "deep" / "out.twb")

    text = out.read_text(encoding="utf-8")
    assert "현금흐름" in text
    reparsed = twb.parse(out)
    assert reparsed.find("datasource").get("caption") == "현금흐름"
    assert [w.get("name") for w in reparsed.iter("worksheet")] == ["시트 1"]


def test_serialize_keeps_the_xml_declaration(tmp_path: Path) -> None:
    """선언이 없는 `.twb`는 Tableau가 열지 않는다."""
    root = twb.parse(write(tmp_path / "in.twb", make_twb()))

    out = twb.serialize(root, tmp_path / "out.twb")

    assert out.read_bytes().startswith(b"<?xml")
