"""규칙 ⑪(`shelf.refs`) — 선반 배치 참조 무결성 (T4-a).

실측(실파일 84개 전수)이 표면 목록과 심각도를 정했다. 반례 28건이 전부 골든셋 파일
하나에서 나왔고 그 파일은 열린다 → **WARNING**. 여기 테스트의 절반은
"정상 배치에서 침묵하는가"를 본다 — AC7이 먼저다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Ds, make_twb, qualified_ref
from twb_lint import inspect as inspector
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.semantic.shelf_refs import ShelfRefsRule

GOOD = qualified_ref("federated.abc", "매출")
GONE = qualified_ref("federated.abc", "사라진필드")


@pytest.fixture
def rule() -> ShelfRefsRule:
    return ShelfRefsRule()


def ctx_for(tmp_path: Path, xml: str) -> ValidationContext:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx


def workbook(sheet_body: str) -> str:
    """필드 `매출` 하나를 가진 데이터소스 + 워크시트 1개."""
    return make_twb(
        datasources=(Ds(name="federated.abc", columns=("매출", "지역")),),
        extra_body=(
            f"<worksheets><worksheet name='S1'><table>{sheet_body}</table></worksheet></worksheets>"
        ),
    )


def test_a_consistent_placement_is_silent(tmp_path: Path, rule: ShelfRefsRule) -> None:
    xml = workbook(
        f"<rows>{GOOD}</rows><cols>{GOOD}</cols>"
        f"<panes><pane><encodings><color column='{GOOD}' /></encodings></pane></panes>"
        f"<view><slices><column>{GOOD}</column></slices></view>"
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_a_workbook_without_worksheets_says_so(tmp_path: Path, rule: ShelfRefsRule) -> None:
    ctx = ctx_for(tmp_path, make_twb(datasources=(Ds(name="federated.abc", columns=("매출",)),)))

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("shelf.refs")] == [CoverageStatus.SKIPPED]


def test_no_fields_means_we_could_not_compare(tmp_path: Path, rule: ShelfRefsRule) -> None:
    """필드를 하나도 못 모았으면 전 참조가 dangling으로 보인다.

    그때 보고할 것은 위반이 아니라 **대조하지 못했다**는 사실이다 (02 S5).
    """
    xml = make_twb(
        extra_body=(
            "<worksheets><worksheet name='S1'>"
            f"<table><rows>{GOOD}</rows></table>"
            "</worksheet></worksheets>"
        )
    )
    ctx = ctx_for(tmp_path, xml)

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for("shelf.refs")] == [CoverageStatus.SKIPPED]


@pytest.mark.parametrize(
    ("body", "shelf"),
    [
        (f"<rows>{GONE}</rows>", "행 선반"),
        (f"<cols>{GONE}</cols>", "열 선반"),
        (f"<pages><column>{GONE}</column></pages>", "페이지 선반"),
        (f"<view><slices><column>{GONE}</column></slices></view>", "필터 선반"),
        (
            f"<panes><pane><encodings><color column='{GONE}' /></encodings></pane></panes>",
            "마크(색상)",
        ),
        (
            f"<panes><pane><encodings><tooltip column='{GONE}' /></encodings></pane></panes>",
            "마크(도구 설명)",
        ),
        (f"<view><filter><groupfilter level='{GONE}' /></filter></view>", "필터"),
        (f"<view><computed-sort column='{GONE}' /></view>", "정렬(계산됨)"),
        (f"<panes><pane x-axis-name='{GONE}' /></panes>", "X축"),
    ],
)
def test_each_broken_shelf_is_reported_as_warning(
    tmp_path: Path, rule: ShelfRefsRule, body: str, shelf: str
) -> None:
    findings = rule.check(ctx_for(tmp_path, workbook(body)))

    assert [f.severity for f in findings] == [Severity.WARNING], (
        "선반 참조가 끊긴 파일이 열리지 않는다는 근거가 없다 — 골든셋 파일에 반례가 있다"
    )
    assert shelf in findings[0].location


def test_the_pages_shelf_comes_from_the_official_xsd(
    tmp_path: Path, rule: ShelfRefsRule
) -> None:
    """`<pages>`는 실측 0회다. 근거는 추측이 아니라 XSD다.

    내용 모델이 `<column>` 자식 목록이고 타입이 `QualifiedName-ST`로,
    실측 2,462:0인 `<slices>/<column>`과 같은 구조다 (`twb_2026.1.0.xsd:5497`).
    이 테스트가 깨지면 그 근거를 다시 확인해야 한다.
    """
    xml = workbook(f"<pages><column>{GOOD}</column><column>{GONE}</column></pages>")

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "페이지 선반" in findings[0].location


def test_an_expression_on_a_shelf_is_fully_scanned(
    tmp_path: Path, rule: ShelfRefsRule
) -> None:
    """행·열은 참조 하나가 아니라 **수식**일 수 있다 (실측 `([a] / [b])`)."""
    xml = workbook(f"<rows>({GOOD} / {GONE})</rows>")

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 1
    assert "사라진필드" in findings[0].message


def test_the_measure_names_placeholder_is_not_a_field(
    tmp_path: Path, rule: ShelfRefsRule
) -> None:
    """`[:Measure Names]`는 필드가 아니라 Tableau 내장 축이다 (실측 1,294회)."""
    xml = workbook("<cols>[federated.abc].[:Measure Names]</cols><rows>[:Measure Values]</rows>")
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_definition_copies_are_not_placements(tmp_path: Path, rule: ShelfRefsRule) -> None:
    """`<datasource-dependencies>`는 워크시트가 쓰는 필드 **정의의 사본**이다.

    선반으로 읽으면 정상 파일이 통째로 뱉어진다.
    """
    xml = workbook(
        "<view><datasource-dependencies datasource='federated.abc'>"
        f"<column datatype='real' name='[유령]' role='measure'>"
        f"<calculation class='tableau' formula='1' /></column>"
        f"<groupfilter level='{GONE}' />"
        "</datasource-dependencies></view>"
    )
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_an_adhoc_calc_on_a_shelf_is_silent(tmp_path: Path, rule: ShelfRefsRule) -> None:
    """선반에서 만든 임시 계산은 `<datasources>`에 없다 — 그래도 정상이다 (03 D3.6.4)."""
    adhoc = qualified_ref("federated.abc", "Calculation_9")
    xml = workbook(
        "<view><datasource-dependencies datasource='federated.abc'>"
        "<column caption='&quot;계획&quot;' datatype='string' name='[Calculation_9]'"
        " user:unnamed='S1'><calculation class='tableau' formula='&quot;계획&quot;' /></column>"
        "</datasource-dependencies></view>"
        f"<cols>{adhoc}</cols>"
    )

    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_the_formatted_text_body_is_not_a_shelf(tmp_path: Path, rule: ShelfRefsRule) -> None:
    """`<run>`은 텍스트 서식의 본문이다 — 선반이 아니다 (반례 34건)."""
    xml = workbook(f"<formatted-text><run>&lt;{GONE}&gt;</run></formatted-text>")
    assert rule.check(ctx_for(tmp_path, xml)) == []


def test_the_same_broken_placement_is_reported_once(
    tmp_path: Path, rule: ShelfRefsRule
) -> None:
    """같은 필드가 여러 선반에 올라 있어도 선반별로 한 번씩만 센다."""
    xml = workbook(
        f"<rows>{GONE}</rows><rows>{GONE}</rows><rows>{GONE}</rows>"
        f"<cols>{GONE}</cols>"
    )

    findings = rule.check(ctx_for(tmp_path, xml))

    assert len(findings) == 2  # 행 선반 1 + 열 선반 1
    rows = next(f for f in findings if "행 선반" in f.location)
    assert "3곳" in rows.message
