"""`twb_lint.io.twbx.unpack` — 해제 정책이 실제 ZIP에 적용되는지.

`test_safety.py`는 정책 함수를 **단독으로** 검사한다. 여기서는 그 정책이 unpack
경로에 실제로 배선돼 있는지를 본다 — 정책이 있어도 호출하지 않으면 방어가 없다.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from twb_lint.io import safety, twbx

HYPER = bytes((i * 37) % 251 for i in range(4096))
"""`.hyper` 대역. 압축비 상한(200배)에 걸리지 않을 만큼 패턴이 흩어져 있다."""

TWB = b"<?xml version='1.0'?><workbook version='18.1' />"


def make_twbx(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_twb_input_is_passed_through(tmp_path: Path) -> None:
    """`.twb`는 풀 것이 없다 — 그대로 감싸 반환한다."""
    twb = tmp_path / "plain.twb"
    twb.write_bytes(TWB)

    got = twbx.unpack(twb, tmp_path / "unpacked")

    assert got.twb_path == twb
    assert got.root == tmp_path


def test_twbx_yields_the_twb_and_creates_dest(tmp_path: Path) -> None:
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB, "Data/extract.hyper": HYPER})
    dest = tmp_path / "out" / "nested"  # 아직 없다 — unpack이 만들어야 한다

    got = twbx.unpack(src, dest)

    assert got.root == dest
    assert got.twb_path == dest / "wb.twb"
    assert got.twb_path.read_bytes() == TWB


def test_hyper_is_extracted_byte_for_byte(tmp_path: Path) -> None:
    """C4의 절반 — 해제 쪽. 재압축·재인코딩이 끼면 여기서 깨진다 (07 G6)."""
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB, "Data/extract.hyper": HYPER})

    got = twbx.unpack(src, tmp_path / "out")

    assert (got.root / "Data" / "extract.hyper").read_bytes() == HYPER


def test_top_level_twb_wins_over_a_nested_one(tmp_path: Path) -> None:
    """엉뚱한 워크북을 검증하지 않게 최상위를 우선한다."""
    src = make_twbx(
        tmp_path / "wb.twbx",
        {"deep/dir/inner.twb": b"<workbook />", "outer.twb": TWB},
    )

    got = twbx.unpack(src, tmp_path / "out")

    assert got.twb_path.name == "outer.twb"


def test_zip_slip_entry_is_refused(tmp_path: Path) -> None:
    src = make_twbx(tmp_path / "evil.twbx", {"wb.twb": TWB, "../escape.twb": b"pwned"})

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.UNSAFE_ARCHIVE
    assert not (tmp_path / "escape.twb").exists()


def test_zip_bomb_ratio_is_refused(tmp_path: Path) -> None:
    src = make_twbx(tmp_path / "bomb.twbx", {"wb.twb": TWB, "bomb.bin": b"\x00" * 5_000_000})

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.UNSAFE_ARCHIVE


def test_entry_count_is_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(safety, "MAX_ZIP_ENTRIES", 2)
    src = make_twbx(tmp_path / "many.twbx", {f"f{i}.txt": b"x" for i in range(3)})

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.UNSAFE_ARCHIVE


def test_a_lying_header_is_caught_while_copying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ZIP 헤더의 `file_size`는 아카이브 제작자가 쓰는 값이라 거짓말할 수 있다.

    선언 크기 사전 검사(`check_zip_entry`)가 통과해도 실제 해제량이 상한을 넘으면
    막아야 한다. 헤더를 손으로 위조하는 대신 사전 검사를 무력화해 2선 방어만 남긴다.
    """
    monkeypatch.setattr(safety, "check_zip_entry", lambda *args, **kwargs: None)
    monkeypatch.setattr(safety, "MAX_UNPACKED_BYTES", 16)
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB})

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.UNSAFE_ARCHIVE


def test_corrupt_archive_is_reported_not_crashed(tmp_path: Path) -> None:
    src = tmp_path / "broken.twbx"
    src.write_bytes(b"not a zip at all")

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.CORRUPT_ARCHIVE


def test_archive_without_a_twb_is_reported(tmp_path: Path) -> None:
    src = make_twbx(tmp_path / "nodoc.twbx", {"Data/extract.hyper": HYPER})

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.unpack(src, tmp_path / "out")

    assert exc.value.problem.kind is safety.ProblemKind.CORRUPT_ARCHIVE
