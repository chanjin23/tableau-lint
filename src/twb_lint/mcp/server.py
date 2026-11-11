"""twb-lint MCP 서버 (stdio) — 공식 mcp[cli] FastMCP.

도구 5개를 코어에 얇게 위임한다: twb_unpack · twb_inspect · twb_validate · twb_recipe ·
twb_suggestion_box. 앞 넷은 읽기 전용이고 마지막만 건의함(.twb-lint/)에 쓴다.
코어 로직은 여기 두지 않는다 (호스트 독립 유지).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from twb_lint import __version__, config, recipe_requests, recipes
from twb_lint import inspect as inspector
from twb_lint.io import twbx
from twb_lint.validation import engine

mcp = FastMCP(
    "twb-lint",
    instructions=(
        "시나리오별 도구 선택:\n"
        "- `.twbx`를 다룰 때는 항상 twb_unpack으로 먼저 푼다.\n"
        "- 조회·질문만이면 twb_inspect만 쓴다 — twb_recipe·twb_validate를 부르지 않는다.\n"
        "- 생성·편집이면 XML을 쓰기 전에 twb_recipe를 조회하고, 작업 마지막에\n"
        "  twb_validate로 검증한다. passed=False면 산출물을 내보내지 않는다.\n"
        "- twb_recipe가 found=False이거나 레시피대로 썼는데 검증이 실패하면 twb_suggestion_box로\n"
        "  접수한다. 검증은 통과했는데 Tableau에서 깨졌거나 경고가 틀렸을 때도 접수한다.\n"
        "  접수는 레시피가 아니다 — 그래도 XML을 추측으로 쓰지 않는다."
    ),
)

# FastMCP는 버전을 받지 않고, 저수준 서버는 비어 있으면 **MCP SDK 버전**으로 채운다.
# 그대로 두면 호스트가 "twb-lint 1.28.1"을 보게 되어 어떤 검증기가 붙었는지 알 수 없다
# (실측으로 드러났다). 게이트가 판정을 내리는 도구라 버전 오인은 값이 크다.
mcp._mcp_server.version = __version__


@mcp.tool()
def twb_validate(path: str) -> dict[str, Any]:
    """`.twb`/`.twbx`를 2계층(구문+시맨틱) 검증한다.

    생성·편집 작업의 마지막에 부른다. 조회만 할 때는 부르지 않는다.
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
    """`.twb`/`.twbx`의 구조 모델(데이터소스·필드·시트·대시보드)을 반환한다.

    조회·질문 전용 — 이 경우 twb_recipe·twb_validate는 부르지 않는다.
    """
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
    """`.twbx`를 dest에 풀어 `.twb`와 부속 파일을 얻는다 (.hyper 무손실).

    `.twbx`를 다룰 때는 항상 이 도구로 먼저 푼다.
    """
    unpacked = twbx.unpack(Path(path), Path(dest))
    return {"twb_path": str(unpacked.twb_path), "root": str(unpacked.root)}


@mcp.tool()
def twb_recipe(query: str = "") -> dict[str, Any]:
    """`.twb` XML을 쓰기(생성·편집) 전에 **반드시** 조회하는 저작 레시피.

    레시피 = Tableau UI 조작이 XML을 어떻게 쓰는지의 실측 정답지.
    레시피 없이 XML을 추측으로 쓰지 않는다. 매핑표에 없는 작업은 지어내지 말고
    미관찰로 보고한다.

    인자는 `query` **하나뿐**이다 (다른 이름은 오류로 거부된다).
    query 없음 → 전체 매핑표(작업 → 레시피 인덱스).
    query가 레시피 식별자(예: '18', '18-datasource-folders-palette', 파일명 `.md`)
    → 그 레시피 본문.
    query가 그 밖의 말(예: '계산 필드 추가') → 키워드로 가장 맞는 레시피 본문.
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
    hit = recipes.get(query) or recipes.find(query)
    if hit is None:
        return {
            "found": False,
            "message": f"'{query}'에 맞는 레시피가 없다 — 미관찰 작업이면 지어내지 말 것. "
            "필요한 작업이면 twb_suggestion_box(kind='missing')로 접수하라.",
            "index": index,
        }
    name, content = hit
    return {"found": True, "name": name, "content": content}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
def twb_suggestion_box(
    kind: Annotated[
        recipe_requests.Kind,
        Field(
            description=(
                "missing: 레시피가 없다(twb_recipe found=False) · "
                "defective: 레시피대로 썼는데 twb_validate가 실패했다(recipe 필수) · "
                "lint_missed: 검사는 통과했는데 Tableau에서 깨졌다(symptom·layer 필수) · "
                "lint_false_alarm: 검사가 경고·오류를 냈는데 Tableau에서는 정상이다(rule_ids 필수)"
            )
        ),
    ],
    task: Annotated[
        str,
        Field(description="하려던 작업 또는 문제가 난 기능을 한 줄로 (200자 이하)"),
    ],
    recipe: Annotated[
        str, Field(description="따른 레시피 번호·파일명 (defective 필수, 그 외 선택)")
    ] = "",
    rule_ids: Annotated[
        list[str] | None,
        Field(
            description=(
                "관련 규칙 id (예: calc.aggregation). lint_false_alarm은 울린 규칙 필수, "
                "lint_missed는 잡았어야 할 규칙(선택), defective는 실패한 finding의 규칙"
            )
        ),
    ] = None,
    symptom: Annotated[
        str,
        Field(
            description=(
                "Tableau에서 본 것 — 오류 문구를 그대로, 또는 '정상 렌더링' (300자 이하). "
                "lint_missed 필수"
            )
        ),
    ] = "",
    layer: Annotated[
        recipe_requests.Layer | None,
        Field(
            description=(
                "lint_missed의 실패 층 — load_refused: 파일이 안 열린다 · "
                "setting_dropped: 열리는데 설정이 버려졌다 · no_data: 데이터가 안 나온다 · "
                "field_error: 빨간 알약·느낌표. 다른 종류에는 쓰지 않는다"
            )
        ),
    ] = None,
    note: Annotated[
        str, Field(description="참고 메모 — 어느 파일·시트에서 봤는지 등 (300자 이하)")
    ] = "",
) -> dict[str, Any]:
    """레시피·검사기 문제를 **건의함에 접수**한다 (나중에 빈도순으로 모아 본다).

    레시피를 만들거나 규칙을 고치지는 않는다 — 부족한 목록을 남길 뿐이다. 접수한 뒤에도
    XML을 추측으로 쓰지 않는다.

    종류(kind)마다 필수 항목이 다르다 — 각 인자 설명을 본다. 빠지면 접수를 거절하고
    이유를 돌려준다.

    워크북 XML·데이터 값은 넣지 않는다 (XML 조각은 거부된다). 같은 요청은 합쳐져
    count가 오른다.
    """
    try:
        req = recipe_requests.submit(
            kind, task, recipe=recipe, rule_ids=rule_ids, note=note,
            symptom=symptom, layer=layer,
        )
    except recipe_requests.RequestError as exc:
        return {"accepted": False, "message": str(exc)}
    return {"accepted": True, "id": req.id, "count": req.count}


def _reject_unknown_arguments() -> None:
    """도구 호출의 **모르는 인자를 오류로 돌려준다.**

    FastMCP가 만드는 인자 모델은 기본이 `extra='ignore'`라서 `twb_recipe(name='18')`처럼
    틀린 인자 이름이 **조용히 버려지고** 인자 없는 호출로 처리된다 — 호출자는 인덱스를
    받고도 왜 본문이 안 오는지 알 수 없다 (2026-10-13 MA_028 제보).
    """
    for tool in mcp._tool_manager.list_tools():
        model = tool.fn_metadata.arg_model
        model.model_config["extra"] = "forbid"
        model.model_rebuild(force=True)


_reject_unknown_arguments()


def main() -> None:
    """stdio 트랜스포트로 서버 실행 (entry point: twb-lint-mcp)."""
    mcp.run()


if __name__ == "__main__":
    main()
