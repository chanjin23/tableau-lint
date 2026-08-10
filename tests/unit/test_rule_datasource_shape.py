"""규칙 ⑭(`datasource.shape`) — 데이터 원본의 객체 모델 골격.

**층 정의 바깥의 실패다.** 파일은 열린다 — 데이터 원본 탭을 클릭할 때
Tableau가 즉시 종료된다 (2026-08-10 분리 실험 V1, 06 R25).

이 규칙만 층 1이 아닌데 ERROR다. 근거는 상관(실파일 113개 반례 0) **더하기**
인과(정본에서 `<object-graph>`만 빼니 종료)다. 같은 실험이 `<columns>` 후보를
죽였다 — 빼도 증상이 없어서 규칙에 넣지 않았고, 그 사실을 아래 테스트가 고정한다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.datasource_shape import DatasourceShapeRule

RELATION_TABLE = (
    "<relation connection='textscan.x' name='d.csv' table='[d#csv]' type='table'>"
    "<columns header='yes' separator=','>"
    "<column datatype='string' name='지역' ordinal='0' />"
    "</columns>"
    "</relation>"
)
OBJECT_GRAPH = (
    "<object-graph><objects><object caption='d.csv' id='d.csv_A'>"
    "<properties context=''>" + RELATION_TABLE + "</properties>"
    "</object></objects></object-graph>"
)


def _datasources(relation: str, *, object_graph: bool) -> str:
    body = f"<connection class='federated'>{relation}</connection>"
    if object_graph:
        body += OBJECT_GRAPH
    return (
        "<datasources>"
        f"<datasource caption='관찰_data' name='federated.x'>{body}</datasource>"
        "</datasources>"
    )


@pytest.fixture
def rule() -> DatasourceShapeRule:
    return DatasourceShapeRule()


def test_canonical_datasource_is_silent(rule: DatasourceShapeRule) -> None:
    """실파일 113개가 전부 이 형태다 — 여기서 finding이 나면 AC7이 깨진다."""
    ctx = make_ctx(make_twb(extra_body=_datasources(RELATION_TABLE, object_graph=True)))

    assert rule.check(ctx) == []


def test_missing_object_graph_is_an_error(rule: DatasourceShapeRule) -> None:
    """인과 실측: 이것만 빼면 데이터 원본 탭에서 Tableau가 종료된다 (V1)."""
    ctx = make_ctx(make_twb(extra_body=_datasources(RELATION_TABLE, object_graph=False)))

    findings = rule.check(ctx)

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "object-graph" in findings[0].message


def test_table_relation_without_columns_is_not_reported(rule: DatasourceShapeRule) -> None:
    """**죽은 후보다.** 상관은 39:0이었지만 빼도 증상이 없었다 (V2).

    여기서 finding이 나기 시작하면 증상 없는 규칙이 부활한 것이다.
    """
    relation = "<relation connection='textscan.x' name='d.csv' table='[d#csv]' type='table' />"
    ctx = make_ctx(make_twb(extra_body=_datasources(relation, object_graph=True)))

    assert rule.check(ctx) == []


def test_custom_sql_relation_is_checked_too(rule: DatasourceShapeRule) -> None:
    """`type='text'`(사용자 지정 SQL)도 `<object-graph>`를 갖는다 — 실파일 74개."""
    relation = (
        "<relation connection='postgres.x' name='사용자 지정 SQL 쿼리' type='text'>"
        "SELECT 1</relation>"
    )
    ctx = make_ctx(make_twb(extra_body=_datasources(relation, object_graph=False)))

    assert [f.severity for f in rule.check(ctx)] == [Severity.ERROR]


def test_worksheet_local_copies_are_not_checked(rule: DatasourceShapeRule) -> None:
    """워크시트 안 `<datasource-dependencies>` 사본에는 연결이 없다 — 대상이 아니다."""
    ctx = make_ctx(
        make_twb(
            extra_body=(
                _datasources(RELATION_TABLE, object_graph=True)
                + "<worksheets><worksheet name='s'><table><view>"
                "<datasource-dependencies datasource='federated.x'>"
                "<column datatype='string' name='[지역]' role='dimension' type='nominal' />"
                "</datasource-dependencies></view></table></worksheet></worksheets>"
            )
        )
    )

    assert rule.check(ctx) == []


def test_workbook_without_connected_datasource_reports_the_skip(
    rule: DatasourceShapeRule,
) -> None:
    """빈 워크북에는 검사할 것이 없다 — 조용히 통과하지 않고 그 사실을 남긴다 (02 S5)."""
    ctx = make_ctx(make_twb())

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]


def test_missing_tree_reports_the_skip(rule: DatasourceShapeRule) -> None:
    ctx = make_ctx(make_twb())
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
