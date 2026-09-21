"""MCP 어댑터 — 코어를 얇게 감싸기만 하는지.

서버를 실제로 띄워 보기 전까지 이 파일에는 테스트가 없었고, 그래서 두 결함이
살아남았다: 서버 버전이 MCP SDK 버전으로 보고되던 것과, 없는 `.twbx`에서 raw
`OSError`가 새던 것.

stdio 왕복은 여기서 재현하지 않는다 — 어댑터가 코어에 위임하는지만 본다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import make_twb
from twb_lint import __version__
from twb_lint.io import safety
from twb_lint.mcp import server


def test_server_reports_its_own_version() -> None:
    """비워 두면 MCP SDK 버전이 나간다 — 어떤 검증기가 붙었는지 알 수 없게 된다."""
    assert server.mcp._mcp_server.version == __version__
    assert server.mcp.name == "twb-lint"


def test_server_instructions_route_all_four_tools() -> None:
    """시나리오 라우팅(열기→unpack, 편집→recipe+validate, 조회→inspect만)은
    서버 instructions가 유일한 전달 경로다 — 비면 호스트는 docstring만 본다."""
    instructions = server.mcp.instructions
    assert instructions
    for tool in ("twb_unpack", "twb_inspect", "twb_recipe", "twb_validate"):
        assert tool in instructions


def test_validate_returns_the_gate_verdict(tmp_path: Path) -> None:
    # 워크시트 1개는 "통과하는 워크북"의 최소 조건이다 — 0개는 규칙 ⑱이 막는다.
    src = tmp_path / "wb.twb"
    src.write_text(make_twb(worksheets=("Sheet1",)), encoding="utf-8")

    result = server.twb_validate(str(src))

    assert result["passed"] is True
    assert isinstance(result["findings"], list)


def test_validate_reports_a_missing_file_instead_of_raising() -> None:
    """게이트 판정 경로는 하나다 — 입력 오류도 finding이다 (02 S5)."""
    result = server.twb_validate("does-not-exist.twbx")

    assert result["passed"] is False
    assert result["findings"][0]["rule_id"] == "input.readable"


def test_unpack_raises_the_io_contract_error_for_a_missing_file(tmp_path: Path) -> None:
    """`zipfile`은 없는 파일에 BadZipFile이 아니라 OSError를 던진다.

    그대로 흘려보내면 호출자가 `safety.InputError` 하나로 잡던 계약(03 D9.1)이 깨진다.
    """
    with pytest.raises(safety.InputError) as exc:
        server.twb_unpack("does-not-exist.twbx", str(tmp_path))

    assert exc.value.problem.kind is safety.ProblemKind.UNREADABLE


def test_inspect_returns_the_structure_model(tmp_path: Path) -> None:
    src = tmp_path / "wb.twb"
    src.write_text(make_twb(worksheets=("S1",)), encoding="utf-8")

    model = server.twb_inspect(str(src))

    assert model["release"] == "2026.1"
    assert model["worksheets"] == ["S1"]


def test_recipe_without_query_returns_the_index() -> None:
    result = server.twb_recipe()

    assert result["found"] is True
    assert "레시피" in result["index"]
    assert "01-calc-field-create.md" in result["recipes"]


def test_recipe_with_query_returns_one_recipe_body() -> None:
    result = server.twb_recipe("계산 필드 추가")

    assert result["found"] is True
    assert result["name"] == "01-calc-field-create.md"
    assert "calculation" in result["content"]


def test_recipe_miss_says_so_instead_of_guessing() -> None:
    """맞는 레시피가 없으면 지어내지 않고 없다고 말한다 — 인덱스를 함께 준다."""
    result = server.twb_recipe("qqqqzzzz")

    assert result["found"] is False
    assert "index" in result
