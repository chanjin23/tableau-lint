"""`twb_lint.io.safety` — 신뢰할 수 없는 입력 방어 (docs/TODO A7).

이 도구는 AI가 만든 파일을 먹는다. 방어가 없으면 검증기가 공격 표면이 된다.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from twb_lint.io import safety

BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<workbook>&lol3;</workbook>
"""

XXE = """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<workbook>&xxe;</workbook>
"""


def test_parser_does_not_expand_entities() -> None:
    """billion laughs — 엔티티를 확장하지 않으면 폭발하지 않는다."""
    root = etree.fromstring(BILLION_LAUGHS.encode("utf-8"), safety.make_parser())
    # 확장됐다면 텍스트가 1000자를 넘는다.
    assert len(root.text or "") < 100


def test_parser_does_not_resolve_external_entities() -> None:
    """XXE — 외부 엔티티가 파일 내용으로 치환되면 안 된다."""
    root = etree.fromstring(XXE.encode("utf-8"), safety.make_parser())
    assert "root:" not in (root.text or "")


def test_missing_file_is_reported_not_raised(tmp_path: Path) -> None:
    problems = safety.check_source(tmp_path / "nope.twb")
    assert [p.kind for p in problems] == [safety.ProblemKind.MISSING]


def test_directory_is_rejected(tmp_path: Path) -> None:
    assert [p.kind for p in safety.check_source(tmp_path)] == [safety.ProblemKind.NOT_A_FILE]


def test_bad_suffix_is_rejected(tmp_path: Path) -> None:
    f = tmp_path / "x.xml"
    f.write_text("<workbook />", encoding="utf-8")
    assert safety.ProblemKind.BAD_SUFFIX in {p.kind for p in safety.check_source(f)}


def test_normal_sized_twb_passes(tmp_path: Path) -> None:
    """정상 파일을 막으면 AC7이 깨진다 — 상한은 실측의 수십 배로 잡혀 있다."""
    f = tmp_path / "ok.twb"
    f.write_text("<workbook />", encoding="utf-8")
    assert safety.check_source(f) == []


def test_zip_slip_paths_are_refused(tmp_path: Path) -> None:
    assert safety.safe_extract_path(tmp_path, "../escape.twb") is None
    assert safety.safe_extract_path(tmp_path, "/abs/escape.twb") is None
    assert safety.safe_extract_path(tmp_path, "a/../../escape.twb") is None


def test_normal_zip_entry_paths_are_allowed(tmp_path: Path) -> None:
    got = safety.safe_extract_path(tmp_path, "Data/extract.hyper")
    assert got is not None
    assert got.name == "extract.hyper"


def test_zip_bomb_ratio_is_caught() -> None:
    problem = safety.check_zip_entry(
        "bomb", compressed_size=1_000, file_size=10_000_000, running_total=0
    )
    assert problem is not None
    assert problem.kind is safety.ProblemKind.UNSAFE_ARCHIVE


def test_total_unpacked_size_is_capped() -> None:
    problem = safety.check_zip_entry(
        "big",
        compressed_size=safety.MAX_UNPACKED_BYTES,
        file_size=safety.MAX_UNPACKED_BYTES,
        running_total=1,
    )
    assert problem is not None


def test_realistic_hyper_entry_passes() -> None:
    """`.hyper`는 크지만 압축이 잘 되지 않는다 — 정상 엔트리가 걸리면 안 된다."""
    assert safety.check_zip_entry("x.hyper", 40_000_000, 60_000_000, 0) is None
