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


def test_roundtrip_preserves_hyper_bytes(tmp_path: Path) -> None:
    """C4 — unpack→pack에서 `.hyper`는 **바이트 단위로 동일**하다 (07 G6)."""
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB, "Data/extract.hyper": HYPER})

    unpacked = twbx.unpack(src, tmp_path / "out")
    repacked = twbx.pack(unpacked.root, tmp_path / "again" / "wb.twbx")

    with zipfile.ZipFile(repacked) as zf:
        assert zf.read("Data/extract.hyper") == HYPER
        assert zf.read("wb.twb") == TWB


def test_pack_is_deterministic(tmp_path: Path) -> None:
    """같은 디렉토리는 항상 같은 바이트로 묶인다 — 골든셋 diff 노이즈 방지 (02 S1-5)."""
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB, "Data/extract.hyper": HYPER})
    root = twbx.unpack(src, tmp_path / "out").root

    first = twbx.pack(root, tmp_path / "a.twbx").read_bytes()
    second = twbx.pack(root, tmp_path / "b.twbx").read_bytes()

    assert first == second


def test_pack_puts_the_twb_first_and_stores_hyper_uncompressed(tmp_path: Path) -> None:
    """`.hyper`는 이미 압축된 포맷이다 — 무압축이 "재압축하지 않는다"를 코드로 보장한다."""
    src = make_twbx(tmp_path / "wb.twbx", {"Data/extract.hyper": HYPER, "wb.twb": TWB})
    root = twbx.unpack(src, tmp_path / "out").root

    with zipfile.ZipFile(twbx.pack(root, tmp_path / "again.twbx")) as zf:
        infos = zf.infolist()

    assert infos[0].filename == "wb.twb"
    assert {i.filename: i.compress_type for i in infos} == {
        "wb.twb": zipfile.ZIP_DEFLATED,
        "Data/extract.hyper": zipfile.ZIP_STORED,
    }


def test_pack_refuses_a_directory_without_a_twb(tmp_path: Path) -> None:
    """`.twb` 없는 `.twbx`는 Tableau가 열지 못한다 — 조용히 만들어 내보내지 않는다."""
    root = tmp_path / "root"
    (root / "Data").mkdir(parents=True)
    (root / "Data" / "extract.hyper").write_bytes(HYPER)

    with pytest.raises(twbx.ArchiveError) as exc:
        twbx.pack(root, tmp_path / "out.twbx")

    assert exc.value.problem.kind is safety.ProblemKind.CORRUPT_ARCHIVE


def test_repacked_archive_can_be_unpacked_again(tmp_path: Path) -> None:
    """pack 결과가 unpack 정책을 다시 통과한다 — 우리 출력이 우리 입력이 된다."""
    src = make_twbx(tmp_path / "wb.twbx", {"wb.twb": TWB, "Data/extract.hyper": HYPER})
    root = twbx.unpack(src, tmp_path / "out").root
    repacked = twbx.pack(root, tmp_path / "again.twbx")

    got = twbx.unpack(repacked, tmp_path / "out2")

    assert got.twb_path.read_bytes() == TWB
    assert (got.root / "Data" / "extract.hyper").read_bytes() == HYPER


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
