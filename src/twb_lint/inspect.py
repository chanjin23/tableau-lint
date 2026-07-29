"""구조 인스펙터 [C2] — .twb를 WorkbookModel + 파싱 트리로 추출.

검증 규칙과 (향후) 편집기가 공유하는 구조 모델을 만든다.

**파싱은 여기서 딱 한 번 일어난다.** 규칙마다 재파싱하면 1MB XML × 규칙 수가 되어
AC5(속도)와 충돌한다 (docs/TODO A1). 그래서 `load_context()`가 트리와 모델을 함께 만들어
`ValidationContext`에 실어 넘긴다.

추출 위치는 **실측을 따른다** (표본 10개, docs/05-xsd-spike.md 표본):

```
workbook@source-build / @version / @original-version
workbook/document-format-change-manifest/*        매니페스트 항목 (원문 그대로)
workbook/datasources/datasource@name              데이터소스
  └ column@name                                   필드 (직계 자식만 — 아래 주석)
      └ calculation@formula                       계산필드 수식
workbook/worksheets/worksheet@name
workbook/dashboards/dashboard//zone@name          배치된 시트
workbook/windows/window@class='worksheet'|'dashboard'
  └ viewpoints/viewpoint@name
```
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from twb_lint import fcp, fieldref
from twb_lint.io import safety, twb, twbx
from twb_lint.models import Dashboard, DataSource, FieldDef, WorkbookModel
from twb_lint.validation.context import ValidationContext


def inspect(source: Path, workdir: Path) -> WorkbookModel:
    """`.twb`/`.twbx`를 구조 모델로 추출한다 (MCP `twb_inspect`의 코어).

    Raises:
        safety.InputError: 파일을 열지 못했을 때. 빈 모델을 반환하면 "데이터소스도
            시트도 없는 워크북"과 구분되지 않는다 — 조용히 통과하지 않는다 (07 G7).
            검증 경로는 이 함수가 아니라 `load_context()`를 쓴다(거기선 finding이 된다).
    """
    ctx, problems = load_context(source, workdir)
    if problems:
        raise safety.InputError(problems[0])
    return ctx.model


def load_context(
    source: Path, workdir: Path
) -> tuple[ValidationContext, list[safety.InputProblem]]:
    """검증 1회분의 컨텍스트를 만든다 — **파싱은 여기서 한 번뿐이다.**

    Returns:
        `(컨텍스트, 입력 문제 목록)`. 문제 목록이 비어 있지 않으면 컨텍스트는 신뢰할 수
        없으며 엔진이 즉시 ERROR finding으로 바꿔 반환한다 (02 S5 — 예외를 던지지 않는다).

    트리를 얻지 못하면 `raw_tree`가 None인 컨텍스트가 나간다. 트리를 요구하는
    규칙(L-A·⑥)은 None을 보고 **검사를 스킵하고 그 사실을 보고**해야 한다.
    """
    problems: list[safety.InputProblem] = []
    twb_path: Path | None = None

    if source.suffix.lower() == ".twbx":
        try:
            twb_path = twbx.unpack(source, workdir).twb_path
        except safety.InputError as exc:
            # 예외를 여기서 멈춘다 — 검증 경로는 예외가 아니라 finding으로 말한다 (02 S5).
            problems.append(exc.problem)
    else:
        twb_path = source

    root: Any | None = None
    if twb_path is not None:
        try:
            root = twb.parse(twb_path)
        except safety.InputError as exc:
            problems.append(exc.problem)

    model = WorkbookModel(source=source, twb_path=twb_path)
    if root is not None:
        _fill(model, root)
    return ValidationContext(model=model, raw_tree=root), problems


def _fill(model: WorkbookModel, root: Any) -> None:
    """파싱된 트리에서 모델을 채운다. 트리는 **정규화 전 원본**이다."""
    model.source_build = root.get("source-build")
    model.twb_version = root.get("version")
    model.original_version = root.get("original-version")
    model.manifest_features = frozenset(fcp.manifest_items(root))

    for el in root.findall("datasources/datasource"):
        ds = _datasource(el)
        model.datasources[ds.name] = ds

    model.worksheets = {
        name for el in root.findall("worksheets/worksheet") if (name := el.get("name"))
    }
    model.worksheet_windows = {
        name
        for el in root.findall("windows/window")
        if el.get("class") == "worksheet" and (name := el.get("name"))
    }
    viewpoints = _viewpoints_by_dashboard(root)
    for el in root.findall("dashboards/dashboard"):
        name = el.get("name")
        if name is None:
            continue
        model.dashboards[name] = Dashboard(
            name=name,
            sheet_zones=_sheet_zones(el),
            viewpoints=viewpoints.get(name, frozenset()),
        )


def _datasource(el: Any) -> DataSource:
    """데이터소스 하나 + 그 필드들.

    `column`은 **직계 자식만** 본다. `.//column`으로 훑으면 `<datasource-dependencies>`
    안의 참조 사본(다른 데이터소스의 필드)까지 이 데이터소스의 필드로 들어와,
    규칙 ②가 남의 필드를 근거로 dangling을 놓친다 (실측: 직계 68 vs 전체 73).
    """
    name = el.get("name") or ""
    ds = DataSource(name=name, caption=el.get("caption"))
    for col in el.findall("column"):
        field_name = _unbracket(col.get("name"))
        if field_name is None:
            continue
        calc = col.find("calculation")
        ds.fields[field_name] = FieldDef(
            name=field_name,
            caption=col.get("caption"),
            datatype=col.get("datatype"),
            formula=None if calc is None else calc.get("formula"),
        )
    return ds


def _sheet_zones(dashboard: Any) -> tuple[str, ...]:
    """대시보드에 배치된 워크시트 이름들.

    시트 존은 `name`이 있고 `type-v2`가 **없다** — 레이아웃 컨테이너·텍스트·이미지 존은
    `type-v2`(`layout-flow`·`empty` 등)를 갖는다 (실측: 이름 있는 존 90/90이 워크시트).
    좁게 잡는 쪽을 택했다. 넓히면 이름 있는 비-시트 존이 규칙 ③에서 거짓 dangling이 되고,
    거짓 ERROR 1건이 게이트를 무력화한다 (02 S1-6).

    `<devicelayouts>`가 같은 존을 한 번 더 담으므로 중복을 제거하되 순서는 유지한다
    (결정론 — 02 S1-5).
    """
    seen: dict[str, None] = {}
    for zone in dashboard.iter("zone"):
        name = zone.get("name")
        if name and zone.get("type-v2") is None:
            seen.setdefault(name, None)
    return tuple(seen)


def _viewpoints_by_dashboard(root: Any) -> dict[str, frozenset[str]]:
    """대시보드 이름 → 그 window의 viewpoint 집합.

    viewpoint는 대시보드가 아니라 대응 `<window class='dashboard'>`가 갖는다.
    배치된 시트에 대응 viewpoint가 없으면 로드 시 내부 오류 2805CF18이 난다 (규칙 ③).
    """
    out: dict[str, frozenset[str]] = {}
    for win in root.findall("windows/window"):
        name = win.get("name")
        if win.get("class") != "dashboard" or name is None:
            continue
        out[name] = frozenset(
            vp_name for vp in win.iter("viewpoint") if (vp_name := vp.get("name"))
        )
    return out


def _unbracket(name: str | None) -> str | None:
    """`[Calculation_1234]` → `Calculation_1234`.

    `column@name`은 대괄호가 붙은 채로 저장된다. `qualified_field_names()`가
    `[ds].[field]`를 조립하므로 여기서 벗겨 두지 않으면 `[[field]]`가 된다.

    안쪽의 `]]`도 되돌린다 — `]`의 이스케이프다. 벗기지 않으면 참조 쪽
    (`fieldref.parse`)과 표기가 어긋나 그 필드가 통째로 dangling이 된다.
    """
    if name is None:
        return None
    if len(name) >= 2 and name.startswith("[") and name.endswith("]"):
        return fieldref.unescape(name[1:-1])
    return name
