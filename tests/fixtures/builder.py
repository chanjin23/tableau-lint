"""최소 `.twb` 조각 빌더 — 규칙 단위 테스트의 입력을 손으로 만들지 않기 위한 도구.

**왜 필요한가**: 스모크 5개와 골든셋(1MB 실파일 · 느림 · 로컬 종속 · 기밀) 사이가 비어
있었다. 그대로 구현에 들어가면 규칙 하나를 고칠 때마다 1MB XML로 디버깅하게 된다
(docs/TODO C2).

여기서 만드는 XML은 **실파일의 축소판이지 유효한 워크북이 아니다.** L-A(XSD)를 통과하도록
설계되지 않았다 — L-B 규칙은 XSD 유효성과 무관하게 돌아야 하므로 의도된 것이다.
XSD를 태우는 테스트는 골든셋(정상 9개)을 쓴다.

표기는 **실측을 따른다** (docs/03-design.md D3.6):

```
calc 수식 안        [Calculation_1234]        내부 이름 그대로
워크시트 속성       [federated.abc].[usr:Calculation_1234:qk]   역할 접두 + 집계 접미
```

두 표기가 다르다는 사실 자체가 규칙 ②의 최대 함정이라 빌더가 양쪽을 다 낼 수 있어야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

from twb_lint.io import safety
from twb_lint.models import WorkbookModel
from twb_lint.validation.context import ValidationContext

DEFAULT_SOURCE_BUILD = "2026.1.1 (20261.26.0410.0924)"
"""표본 9개의 실제 값 (docs/05-xsd-spike.md 표본)."""

DEFAULT_VERSION = "18.1"
"""Tableau 2026.1이 저장해도 이 값이다 — 최소 호환 버전 (05 F4)."""


@dataclass(frozen=True, slots=True)
class Calc:
    """계산필드 하나."""

    name: str
    formula: str
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class Ds:
    """데이터소스 하나."""

    name: str
    columns: tuple[str, ...] = ()
    """일반 컬럼의 내부 이름. `datatype`은 `string`이 된다."""

    typed_columns: tuple[tuple[str, str], ...] = ()
    """`(내부 이름, datatype)` — `datatype`이 판정에 쓰이는 규칙(⑦-f)용."""

    calcs: tuple[Calc, ...] = ()
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class Dash:
    """대시보드 하나 + 대응 window.

    `viewpoints`를 `None`으로 두면 `zones`와 같은 집합이 자동으로 들어간다 —
    "정상" 상태를 만들기 쉽게 하고, 고장 케이스(R2)는 명시적으로 비운다.
    """

    name: str
    zones: tuple[str, ...] = ()
    viewpoints: tuple[str, ...] | None = None


@dataclass(slots=True)
class _Parts:
    body: list[str] = field(default_factory=list)


def qualified_ref(datasource: str, field_name: str, role: str = "none", kind: str = "nk") -> str:
    """워크시트 속성에 쓰이는 정규화된 필드 참조 표기를 만든다.

    실측 형태: `[federated.xxx].[usr:Calculation_1737798957285376:qk]`
    역할 접두(`none`/`usr`/`sum`/`min`/`yr`/`cnt`/`attr`)와
    종류 접미(`nk`/`qk`/`ok`)가 붙는다 — calc 수식 안의 표기와 다르다.
    """
    return f"[{datasource}].[{role}:{field_name}:{kind}]"


def make_twb(
    *,
    source_build: str | None = DEFAULT_SOURCE_BUILD,
    version: str = DEFAULT_VERSION,
    manifest: tuple[str, ...] = (),
    datasources: tuple[Ds, ...] = (),
    worksheets: tuple[str, ...] = (),
    dashboards: tuple[Dash, ...] = (),
    worksheet_windows: tuple[str, ...] | None = None,
    fcp_elements: tuple[str, ...] = (),
    extra_body: str = "",
) -> str:
    """최소 `.twb` XML 문자열을 만든다.

    Args:
        manifest: `<document-format-change-manifest>` 항목 이름 (원문 그대로).
            fcp 항목은 `_.fcp.X.true...X` 형태로 넣는다.
        fcp_elements: 트리에 심을 fcp 요소의 **기능명**. 각 기능 F에 대해
            `<_.fcp.F.true...format />`이 들어간다 — 규칙 ⑥-a 테스트용.
        worksheet_windows: `<window class='worksheet'>`를 만들 시트.
            None이면 `worksheets`와 같다(정상 상태).
        extra_body: 그대로 삽입할 XML 조각 (특수 케이스용).
    """
    parts = _Parts()

    if manifest:
        items = "".join(f"<{name} />" for name in manifest)
        parts.body.append(f"<document-format-change-manifest>{items}</document-format-change-manifest>")

    if datasources:
        # 실파일은 `workbook/datasources/datasource`다. 래퍼를 빼면 인스펙터의 경로와
        # 어긋나 픽스처만 통과하는 테스트가 된다.
        parts.body.append(
            f"<datasources>{''.join(_datasource_xml(ds) for ds in datasources)}</datasources>"
        )

    if worksheets:
        sheets = "".join(f"<worksheet name={quoteattr(w)} />" for w in worksheets)
        parts.body.append(f"<worksheets>{sheets}</worksheets>")

    if dashboards:
        parts.body.append(_dashboards_xml(dashboards))

    windows = _windows_xml(
        worksheets if worksheet_windows is None else worksheet_windows, dashboards
    )
    if windows:
        parts.body.append(windows)

    for feature in fcp_elements:
        parts.body.append(f"<_.fcp.{feature}.true...format />")

    if extra_body:
        parts.body.append(extra_body)

    build_attr = f" source-build={quoteattr(source_build)}" if source_build else ""
    # `xmlns:user`는 실파일 루트가 항상 선언한다. 빼면 `user:unnamed` 같은 실측 속성을
    # 담은 조각이 파서에서 undeclared prefix로 깨져, 픽스처만 통과하는 테스트가 된다.
    return (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        f"<workbook original-version={quoteattr(version)}{build_attr} "
        f"version={quoteattr(version)} "
        "xmlns:user='http://www.tableausoftware.com/xml/user'>"
        + "".join(parts.body)
        + "</workbook>"
    )


def make_ctx(xml: str, *, model: WorkbookModel | None = None) -> ValidationContext:
    """XML 문자열을 파싱해 규칙에 넘길 컨텍스트를 만든다.

    **안전 파서를 쓴다** (`io.safety.make_parser`). 테스트가 프로덕션과 다른 파서를 쓰면
    엔티티 관련 동작 차이를 테스트가 못 잡는다.
    """
    from lxml import etree

    root = etree.fromstring(xml.encode("utf-8"), safety.make_parser())
    from pathlib import Path

    return ValidationContext(
        model=model or WorkbookModel(source=Path("fixture.twb")),
        raw_tree=root,
    )


def _datasource_xml(ds: Ds) -> str:
    caption = f" caption={quoteattr(ds.caption)}" if ds.caption else ""
    cols = "".join(
        f"<column datatype={quoteattr(dt)} name={quoteattr(f'[{c}]')} role='dimension' />"
        for c, dt in [(c, "string") for c in ds.columns] + list(ds.typed_columns)
    )
    calcs = "".join(
        f"<column datatype='real' name={quoteattr(f'[{c.name}]')} role='measure'"
        + (f" caption={quoteattr(c.caption)}" if c.caption else "")
        + f"><calculation class='tableau' formula={quoteattr(c.formula)} /></column>"
        for c in ds.calcs
    )
    return f"<datasource name={quoteattr(ds.name)}{caption}>{cols}{calcs}</datasource>"


def _dashboards_xml(dashboards: tuple[Dash, ...]) -> str:
    out = []
    for d in dashboards:
        # 시트 존은 `name`만 갖는다 — `type-v2`가 붙은 존은 레이아웃 컨테이너다
        # (실측: 이름 있는 존 90/90이 워크시트, 전부 type-v2 없음). 여기서 type-v2를
        # 달면 인스펙터가 시트 존으로 세지 않아 픽스처가 실파일과 다른 사실을 고정한다.
        zones = "".join(f"<zone name={quoteattr(z)} />" for z in d.zones)
        out.append(
            f"<dashboard name={quoteattr(d.name)}>"
            f"<zones><zone type-v2='layout-basic'>{zones}</zone></zones></dashboard>"
        )
    return f"<dashboards>{''.join(out)}</dashboards>"


def _windows_xml(worksheets: tuple[str, ...], dashboards: tuple[Dash, ...]) -> str:
    out = []
    for w in worksheets:
        out.append(f"<window class='worksheet' name={quoteattr(w)} />")
    for d in dashboards:
        names = d.zones if d.viewpoints is None else d.viewpoints
        vps = "".join(f"<viewpoint name={quoteattr(n)} />" for n in names)
        out.append(
            f"<window class='dashboard' name={quoteattr(d.name)}>"
            f"<viewpoints>{vps}</viewpoints></window>"
        )
    if not out:
        return ""
    return f"<windows>{''.join(out)}</windows>"


def formula_with_entities(raw: str) -> str:
    """수식을 XML 속성값에 넣을 때의 이스케이프를 재현한다.

    실파일의 `groupfilter@expression`은 `&apos;`·`&#13;&#10;`·`//` 주석을 그대로 담고
    있었다 (docs/03-design.md D3.6 실측). 파서가 되돌려 주므로 규칙은 원문을 보지만,
    픽스처가 그 경로를 실제로 통과하게 해 둔다.
    """
    return escape(raw, {"'": "&apos;", '"': "&quot;"})
