"""twb-lint MCP 서버 (stdio) — 공식 mcp[cli] FastMCP.

도구 4개를 코어에 얇게 위임한다: twb_unpack · twb_inspect · twb_validate · twb_recipe.
코어 로직은 여기 두지 않는다 (호스트 독립 유지).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from twb_lint import __version__, config, recipes
from twb_lint import inspect as inspector
from twb_lint.io import twbx
from twb_lint.validation import engine

mcp = FastMCP("twb-lint")

# FastMCP는 버전을 받지 않고, 저수준 서버는 비어 있으면 **MCP SDK 버전**으로 채운다.
# 그대로 두면 호스트가 "twb-lint 1.28.1"을 보게 되어 어떤 검증기가 붙었는지 알 수 없다
# (실측으로 드러났다). 게이트가 판정을 내리는 도구라 버전 오인은 값이 크다.
mcp._mcp_server.version = __version__


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
    """`.twb`/`.twbx`의 구조 모델(데이터소스·필드·시트·대시보드)을 반환한다."""
    with tempfile.TemporaryDirectory(prefix="twb_lint_") as tmp:
        model = inspector.inspect(Path(path), Path(tmp))
        return {
            "source": str(model.source),
            "source_build": model.source_build,
            "release": config.release_from_source_build(model.source_build),
            "twb_version": model.twb_version,
            "manifest_features": sorted(model.manifest_features),
            "datasources": {
                name: {
                    "caption": ds.caption,
                    "fields": sorted(ds.fields),
                    "calcs": sorted(n for n, f in ds.fields.items() if f.is_calc),
                }
                for name, ds in model.datasources.items()
            },
            "worksheets": sorted(model.worksheets),
            "dashboards": {
                name: {
                    "sheet_zones": list(dash.sheet_zones),
                    "viewpoints": sorted(dash.viewpoints),
                }
                for name, dash in model.dashboards.items()
            },
        }


@mcp.tool()
def twb_unpack(path: str, dest: str) -> dict[str, Any]:
    """`.twbx`를 dest에 풀어 `.twb`와 부속 파일을 얻는다 (.hyper 무손실)."""
    unpacked = twbx.unpack(Path(path), Path(dest))
    return {"twb_path": str(unpacked.twb_path), "root": str(unpacked.root)}


@mcp.tool()
def twb_recipe(query: str = "") -> dict[str, Any]:
    """`.twb` XML을 쓰기(생성·편집) 전에 **반드시** 조회하는 저작 레시피.

    레시피 = Tableau UI 조작이 XML을 어떻게 쓰는지의 실측 정답지.
    레시피 없이 XML을 추측으로 쓰지 않는다. 매핑표에 없는 작업은 지어내지 말고
    미관찰로 보고한다.

    query 없음 → 전체 매핑표(작업 → 레시피 인덱스).
    query 있음(예: '계산 필드 추가') → 가장 맞는 레시피 본문.
    """
    index = recipes.load_index()
    if index is None:
        return {
            "found": False,
            "message": "레시피 디렉토리(docs/recipes/)가 없다 — 저장소 체크아웃에서 "
            "설치했는지 확인하라. 레시피 없이 XML을 쓰지 말 것.",
        }
    if not query.strip():
        return {"found": True, "index": index, "recipes": sorted(recipes.load_all())}
    hit = recipes.find(query)
    if hit is None:
        return {
            "found": False,
            "message": f"'{query}'에 맞는 레시피가 없다 — 미관찰 작업이면 지어내지 말 것.",
            "index": index,
        }
    name, content = hit
    return {"found": True, "name": name, "content": content}


def main() -> None:
    """stdio 트랜스포트로 서버 실행 (entry point: twb-lint-mcp)."""
    mcp.run()


if __name__ == "__main__":
    main()
