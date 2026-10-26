"""레시피 건의함 — 접수·합치기·거절·해결, 그리고 MCP·CLI 어댑터.

저장 파일은 환경변수로 tmp에 돌린다 — 실제 `.twb-lint/`를 건드리면 안 된다.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from twb_lint import cli, recipe_requests
from twb_lint.mcp import server


@pytest.fixture(autouse=True)
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "requests.jsonl"
    monkeypatch.setenv("TWB_LINT_REQUESTS", str(path))
    return path


def test_same_request_is_merged_and_counted() -> None:
    recipe_requests.submit("missing", "밴드 차트 만들기")
    req = recipe_requests.submit("missing", "  밴드  차트 만들기!! ")

    assert req.count == 2
    assert len(recipe_requests.load()) == 1


def test_different_kind_or_recipe_is_not_merged() -> None:
    recipe_requests.submit("missing", "색 팔레트")
    recipe_requests.submit("defective", "색 팔레트", recipe="18")

    assert len(recipe_requests.load()) == 2


def test_defective_needs_an_existing_recipe() -> None:
    with pytest.raises(recipe_requests.RequestError, match="레시피"):
        recipe_requests.submit("defective", "색 팔레트")
    with pytest.raises(recipe_requests.RequestError, match="레시피"):
        recipe_requests.submit("defective", "색 팔레트", recipe="9999")


def test_defective_stores_the_canonical_recipe_name_and_rule_ids() -> None:
    recipe_requests.submit(
        "defective", "색 팔레트", recipe="018", rule_ids=["palette.instance_declared"]
    )
    req = recipe_requests.submit("defective", "색 팔레트", recipe="18", rule_ids=["fcp.prefix"])

    assert req.recipe == "18-datasource-folders-palette"
    assert req.rule_ids == ["palette.instance_declared", "fcp.prefix"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task", ""),
        ("task", "x" * 201),
        ("task", '<worksheet name="Sheet 1"><table/></worksheet>'),
        ("note", "y" * 301),
        ("note", "<datasource name='federated.1'>"),
    ],
)
def test_bad_text_is_rejected_and_nothing_is_written(field: str, value: str, store: Path) -> None:
    task, note = ("정상 작업", value) if field == "note" else (value, "")

    with pytest.raises(recipe_requests.RequestError):
        recipe_requests.submit("missing", task, note=note)
    assert not store.exists()


def test_a_comparison_operator_is_not_mistaken_for_xml() -> None:
    req = recipe_requests.submit("missing", "[Sales] < 100 인 행만 색칠")

    assert req.count == 1


def test_unknown_kind_and_bad_rule_id_are_rejected() -> None:
    with pytest.raises(recipe_requests.RequestError, match="kind"):
        recipe_requests.submit("other", "x")
    with pytest.raises(recipe_requests.RequestError, match="rule_id"):
        recipe_requests.submit("missing", "x", rule_ids=["not a rule id"])


def test_load_orders_open_before_resolved_then_by_count() -> None:
    recipe_requests.submit("missing", "드문 것")
    for _ in range(3):
        recipe_requests.submit("missing", "자주 오는 것")
    done = recipe_requests.submit("missing", "닫힐 것")
    for _ in range(5):
        recipe_requests.submit("missing", "닫힐 것")
    recipe_requests.resolve(done.id)

    assert [r.task for r in recipe_requests.load()] == ["자주 오는 것", "드문 것", "닫힐 것"]


def test_resolved_request_reopens_when_submitted_again() -> None:
    req = recipe_requests.submit("missing", "다시 오는 것")
    recipe_requests.resolve(req.id, recipe="01")
    assert recipe_requests.load()[0].resolved_by == "01-calc-field-create"

    again = recipe_requests.submit("missing", "다시 오는 것")

    assert again.resolved_by is None
    assert again.count == 2


def test_resolve_unknown_id_or_recipe_is_an_error() -> None:
    req = recipe_requests.submit("missing", "x")

    with pytest.raises(recipe_requests.RequestError):
        recipe_requests.resolve("deadbeef")
    with pytest.raises(recipe_requests.RequestError):
        recipe_requests.resolve(req.id, recipe="9999")


def test_a_corrupt_line_does_not_hide_the_rest(store: Path) -> None:
    recipe_requests.submit("missing", "정상")
    with store.open("a", encoding="utf-8") as fh:
        fh.write("{깨진 줄\n")
    recipe_requests.submit("missing", "정상")

    assert recipe_requests.load()[0].count == 2


def test_empty_store_loads_as_empty() -> None:
    assert recipe_requests.load() == []


# --- MCP 어댑터 ---------------------------------------------------------


def test_tool_accepts_and_reports_the_merged_count() -> None:
    first = server.twb_recipe_request("missing", "밴드 차트")
    second = server.twb_recipe_request("missing", "밴드 차트")

    assert first["accepted"] is True
    assert second["id"] == first["id"]
    assert second["count"] == 2


def test_tool_returns_a_refusal_instead_of_raising() -> None:
    result = server.twb_recipe_request("defective", "색 팔레트")

    assert result["accepted"] is False
    assert "레시피" in result["message"]


def test_recipe_miss_points_to_the_request_tool() -> None:
    result = server.twb_recipe("qqqqzzzz")

    assert "twb_recipe_request" in result["message"]


def test_request_tool_is_not_marked_read_only() -> None:
    """읽기 전용 도구들과 달리 파일에 쓴다 — 호스트가 권한을 다르게 물을 수 있어야 한다."""
    tool = next(t for t in server.mcp._tool_manager.list_tools() if t.name == "twb_recipe_request")

    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is False


def test_request_tool_rejects_an_unknown_argument() -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="Extra inputs are not permitted"):
        asyncio.run(
            server.mcp.call_tool(
                "twb_recipe_request", {"kind": "missing", "task": "x", "name": "y"}
            )
        )


# --- CLI ---------------------------------------------------------------


def test_cli_lists_open_requests_by_frequency(capsys: pytest.CaptureFixture[str]) -> None:
    recipe_requests.submit("missing", "드문 것")
    recipe_requests.submit("missing", "자주 오는 것")
    recipe_requests.submit("missing", "자주 오는 것", note="메모 하나")

    assert cli.main(["recipe-requests"]) == 0

    out = capsys.readouterr().out.splitlines()
    assert "x2" in out[0] and "자주 오는 것" in out[0]
    assert "메모 하나" in out[1]
    assert "드문 것" in out[2]


def test_cli_resolve_closes_a_request_and_hides_it(capsys: pytest.CaptureFixture[str]) -> None:
    req = recipe_requests.submit("missing", "닫을 것")

    assert cli.main(["recipe-requests", "--resolve", req.id, "--recipe", "01"]) == 0
    capsys.readouterr()
    assert cli.main(["recipe-requests"]) == 0
    assert "열린 건의가 없다" in capsys.readouterr().out
    assert cli.main(["recipe-requests", "--all"]) == 0
    assert "닫힘" in capsys.readouterr().out


def test_cli_resolve_unknown_id_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["recipe-requests", "--resolve", "deadbeef"]) == 1
    assert "deadbeef" in capsys.readouterr().err
