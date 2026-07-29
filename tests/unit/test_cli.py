"""CLI — 게이트가 **말을 할 수 있는지**.

CLI에는 테스트가 없었고, 그래서 로컬 실행에서 바로 터지는 결함이 살아남았다:
Windows 기본 콘솔(cp949)에서 finding 메시지의 `—`가 `UnicodeEncodeError`를 내
검증 결과가 통째로 사라졌다. 판정을 내놓고도 말을 못 하는 상태였다.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from tests.fixtures.builder import make_twb
from twb_lint import cli


def test_clean_file_passes_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "wb.twb"
    src.write_text(make_twb(), encoding="utf-8")

    assert cli.main(["validate", str(src)]) == 0
    assert "PASS" in capsys.readouterr().out


def test_missing_file_fails_with_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """게이트 판정은 종료코드다 — 호출자가 이것만 보고 막을 수 있어야 한다."""
    assert cli.main(["validate", str(tmp_path / "nope.twb")]) == 1

    captured = capsys.readouterr()
    assert "FAIL" in captured.err
    assert "input.readable" in captured.err


def test_output_survives_a_non_utf8_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cp949 콘솔에서도 결과가 나와야 한다 — 인코딩 문제로 판정이 사라지면 안 된다."""
    raw = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdout", io.TextIOWrapper(raw, encoding="cp949", errors="strict")
    )
    monkeypatch.setattr(
        sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp949", errors="strict")
    )
    src = tmp_path / "wb.twb"
    src.write_text(make_twb(), encoding="utf-8")

    exit_code = cli.main(["validate", str(src)])
    sys.stdout.flush()

    assert exit_code == 0
    assert b"PASS" in raw.getvalue()
