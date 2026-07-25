"""twb-lint MCP 서버 (stdio) — 공식 mcp[cli] FastMCP.

도구 3개를 코어에 얇게 위임한다: twb_unpack · twb_inspect · twb_validate.
코어 로직은 여기 두지 않는다 (호스트 독립 유지).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from twb_lint import inspect as inspector
from twb_lint.io import twbx
from twb_lint.validation import engine

mcp = FastMCP("twb-lint")


@mcp.tool()
def twb_validate(path: str) -> dict[str, Any]:
    """`.twb`/`.twbx`를 2계층(구문+시맨틱) 검증한다.

    반환: {passed, findings:[{severity, rule_id, location, message, fix}]}.
    passed=False면 산출물을 내보내면 안 된다 (mandatory gate).
    """
    report = engine.validate(path)
    return {
        "passed": report.passed,
        "findings": [
            {
                "severity": f.severity.value,
                "rule_id": f.rule_id,
                "location": f.location,
                "message": f.message,
                "fix": f.fix,
            }
            for f in report.findings
        ],
    }


@mcp.tool()
def twb_inspect(path: str) -> dict[str, Any]:
    """`.twb`/`.twbx`의 구조 모델(필드·시트 등)을 반환한다."""
    with tempfile.TemporaryDirectory(prefix="twb_lint_") as tmp:
        model = inspector.inspect(Path(path), Path(tmp))
        return {
            "source": str(model.source),
            "twb_version": model.twb_version,
            "field_names": sorted(model.field_names),
            "sheet_names": sorted(model.sheet_names),
        }


@mcp.tool()
def twb_unpack(path: str, dest: str) -> dict[str, Any]:
    """`.twbx`를 dest에 풀어 `.twb`와 부속 파일을 얻는다 (.hyper 무손실)."""
    unpacked = twbx.unpack(Path(path), Path(dest))
    return {"twb_path": str(unpacked.twb_path), "root": str(unpacked.root)}


def main() -> None:
    """stdio 트랜스포트로 서버 실행 (entry point: twb-lint-mcp)."""
    mcp.run()


if __name__ == "__main__":
    main()
