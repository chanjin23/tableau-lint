"""`twb_lint.inspect` — 트리에서 모델로의 추출.

여기서 틀리면 **모든 L-B 규칙이 조용히 틀린다.** 규칙은 모델만 보므로, 필드를 하나
빠뜨리면 규칙 ②가 거짓 dangling을, 하나 더 담으면 진짜 dangling을 놓친다.
추출 경로의 근거는 실파일 실측이다 (`inspect.py` 상단 표).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.builder import Calc, Dash, Ds, make_twb
from twb_lint import inspect as inspector
from twb_lint.io import safety
from twb_lint.models import WorkbookModel


def model_of(tmp_path: Path, xml: str) -> WorkbookModel:
    src = tmp_path / "wb.twb"
    src.write_text(xml, encoding="utf-8")
    ctx, problems = inspector.load_context(src, tmp_path / "work")
    assert problems == []
    return ctx.model


def test_versions_are_taken_from_the_root(tmp_path: Path) -> None:
    """`source-build`가 스키마 선택 키다 — `version`은 최소 호환 버전이다 (07 G1)."""
    m = model_of(tmp_path, make_twb())

    assert m.source_build == "2026.1.1 (20261.26.0410.0924)"
    assert m.twb_version == "18.1"
    assert m.original_version == "18.1"


def test_manifest_items_keep_the_fcp_prefix(tmp_path: Path) -> None:
    """벗기면 `.true...`와 `.false...`가 구분되지 않는다 (05 F7)."""
    m = model_of(
        tmp_path,
        make_twb(manifest=("SortTagCleanup", "_.fcp.RoundedCorners.true...RoundedCorners")),
    )

    assert m.manifest_features == frozenset(
        {"SortTagCleanup", "_.fcp.RoundedCorners.true...RoundedCorners"}
    )


def test_fields_are_collected_without_brackets(tmp_path: Path) -> None:
    """`column@name`은 `[x]`로 저장된다. 벗기지 않으면 `[[x]]`가 조립된다."""
    m = model_of(
        tmp_path,
        make_twb(
            datasources=(
                Ds(
                    name="federated.abc",
                    caption="매출",
                    columns=("accs_code",),
                    calcs=(Calc(name="Calculation_1", formula="SUM([accs_code])"),),
                ),
            )
        ),
    )

    ds = m.datasources["federated.abc"]
    assert ds.caption == "매출"
    assert set(ds.fields) == {"accs_code", "Calculation_1"}
    assert ds.fields["Calculation_1"].formula == "SUM([accs_code])"
    assert ds.fields["Calculation_1"].is_calc
    assert not ds.fields["accs_code"].is_calc
    assert m.qualified_field_names() == {
        "[federated.abc].[accs_code]",
        "[federated.abc].[Calculation_1]",
    }


def test_the_field_universe_is_not_just_column_elements(tmp_path: Path) -> None:
    """Tableau는 **커스터마이즈된 필드만** `<column>`으로 적는다 (03 D3.6.2).

    손대지 않은 DB 컬럼은 `<metadata-record>`에만 있다. `<column>`만 모으면 실사용
    참조의 약 4%가 dangling으로 잡힌다 — 전부 거짓양성이다 (실측 687/16,754).
    """
    xml = make_twb(
        extra_body=(
            "<datasources><datasource name='federated.abc'>"
            "<column datatype='real' name='[Calculation_1]'>"
            "<calculation class='tableau' formula='1' /></column>"
            "<group name='[Grp]' caption='그룹' />"
            "<column-instance column='[accs_code]' name='[min:accs_code:qk]' />"
            "<connection><metadata-records>"
            "<metadata-record class='column'><local-name>[accs_code]</local-name></metadata-record>"
            "<metadata-record class='capability'><local-name>[nope]</local-name></metadata-record>"
            "</metadata-records></connection>"
            "</datasource></datasources>"
        )
    )

    ds = model_of(tmp_path, xml).datasources["federated.abc"]

    assert {n: f.origin for n, f in ds.fields.items()} == {
        "Calculation_1": "column",
        "Grp": "group",
        "min:accs_code:qk": "instance",
        "accs_code": "metadata",
    }
    assert ds.fields["Grp"].caption == "그룹"


def test_column_elements_win_over_the_other_origins(tmp_path: Path) -> None:
    """`<column>`이 수식·caption을 갖는다 — 다른 출처가 덮어쓰면 그 정보가 사라진다."""
    xml = make_twb(
        extra_body=(
            "<datasources><datasource name='ds'>"
            "<column datatype='real' name='[x]' caption='진짜'>"
            "<calculation class='tableau' formula='SUM([y])' /></column>"
            "<connection><metadata-records>"
            "<metadata-record class='column'><local-name>[x]</local-name></metadata-record>"
            "</metadata-records></connection>"
            "</datasource></datasources>"
        )
    )

    field = model_of(tmp_path, xml).datasources["ds"].fields["x"]

    assert field.origin == "column"
    assert field.formula == "SUM([y])"


def test_escaped_brackets_in_column_names_are_unescaped(tmp_path: Path) -> None:
    """`]]`는 `]`의 이스케이프다 — 벗기지 않으면 참조 쪽과 표기가 어긋난다 (D3.6.1)."""
    xml = make_twb(
        extra_body=(
            "<datasources><datasource name='Parameters'>"
            "<column datatype='integer' name='[[P_Year]](복사본)_2403]' />"
            "</datasource></datasources>"
        )
    )

    ds = model_of(tmp_path, xml).datasources["Parameters"]

    assert set(ds.fields) == {"[P_Year](복사본)_2403"}


def test_nested_dependency_columns_are_not_this_datasources_fields(tmp_path: Path) -> None:
    """`<datasource-dependencies>`는 **남의 필드**다.

    `.//column`으로 훑으면 여기까지 들어와 규칙 ②가 진짜 dangling을 놓친다
    (실측: 직계 68 vs 전체 73).
    """
    xml = make_twb(
        extra_body=(
            "<datasources><datasource name='federated.abc'>"
            "<column datatype='string' name='[mine]' />"
            "<datasource-dependencies datasource='Parameters'>"
            "<column datatype='string' name='[theirs]' />"
            "</datasource-dependencies>"
            "</datasource></datasources>"
        )
    )

    m = model_of(tmp_path, xml)

    assert set(m.datasources["federated.abc"].fields) == {"mine"}


def test_worksheets_dashboards_and_windows_are_separated(tmp_path: Path) -> None:
    """규칙 ③은 셋을 **3자 대조**한다 — 하나로 합치면 대조가 사라진다."""
    m = model_of(
        tmp_path,
        make_twb(
            worksheets=("Sheet 1", "Sheet 2"),
            dashboards=(Dash(name="Dash", zones=("Sheet 1",)),),
            worksheet_windows=("Sheet 1",),  # Sheet 2는 window가 없다
        ),
    )

    assert m.worksheets == {"Sheet 1", "Sheet 2"}
    assert m.worksheet_windows == {"Sheet 1"}
    dash = m.dashboards["Dash"]
    assert dash.sheet_zones == ("Sheet 1",)
    assert dash.viewpoints == frozenset({"Sheet 1"})


def test_layout_zones_are_not_counted_as_sheets(tmp_path: Path) -> None:
    """`type-v2`가 있는 존은 레이아웃 컨테이너다. 시트로 세면 거짓 dangling이 난다."""
    xml = make_twb(
        worksheets=("Sheet 1",),
        extra_body=(
            "<dashboards><dashboard name='Dash'><zones>"
            "<zone type-v2='layout-flow' name='Container'>"
            "<zone name='Sheet 1' />"
            "</zone></zones></dashboard></dashboards>"
        ),
    )

    m = model_of(tmp_path, xml)

    assert m.dashboards["Dash"].sheet_zones == ("Sheet 1",)


def test_device_layout_duplicates_are_collapsed(tmp_path: Path) -> None:
    """`<devicelayouts>`가 같은 존을 한 번 더 담는다 — 중복 없이, 순서는 유지."""
    xml = make_twb(
        extra_body=(
            "<dashboards><dashboard name='Dash'>"
            "<zones><zone name='A' /><zone name='B' /></zones>"
            "<devicelayouts><devicelayout name='phone'><zones>"
            "<zone name='A' /><zone name='B' />"
            "</zones></devicelayout></devicelayouts>"
            "</dashboard></dashboards>"
        )
    )

    m = model_of(tmp_path, xml)

    assert m.dashboards["Dash"].sheet_zones == ("A", "B")


def test_a_broken_file_yields_problems_and_a_none_tree(tmp_path: Path) -> None:
    """트리를 얻지 못해도 예외가 아니라 문제 목록이다 (02 S5)."""
    src = tmp_path / "broken.twb"
    src.write_text("<workbook>", encoding="utf-8")

    ctx, problems = inspector.load_context(src, tmp_path / "work")

    assert [p.kind for p in problems] == [safety.ProblemKind.MALFORMED_XML]
    assert ctx.raw_tree is None
    assert ctx.normalized_tree() is None


def test_inspect_raises_instead_of_returning_an_empty_model(tmp_path: Path) -> None:
    """빈 모델은 "데이터소스도 시트도 없는 워크북"과 구분되지 않는다 (07 G7)."""
    src = tmp_path / "broken.twb"
    src.write_text("<workbook>", encoding="utf-8")

    with pytest.raises(safety.InputError):
        inspector.inspect(src, tmp_path / "work")
