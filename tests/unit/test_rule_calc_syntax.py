"""규칙 ⑯(`calc.syntax`) — 수식의 구조 문법.

규칙 ①과 묻는 것이 다르다: ①은 "그 이름의 함수가 있는가", ⑯은 "문법이 성립하는가".
파일은 열리므로 **WARNING**이다 — Tableau가 그 필드를 오류 상태로 표시한다(층 4).

정상본 138개 · 수식 85,316건에서 위반 0건이 AC7 근거다 (03 D3.7 · 06 R30).
검출 근거는 코퍼스가 줄 수 없다 — Tableau 편집기를 통과한 수식만 저장되므로
문법 오류 표본은 **주입 레시피 R30**이 만든다.
"""

from __future__ import annotations

import pytest

from tests.fixtures.builder import Calc, Ds, make_ctx, make_twb
from twb_lint.models import CoverageStatus, Severity
from twb_lint.validation.semantic.calc_syntax import CalcSyntaxRule


@pytest.fixture
def rule() -> CalcSyntaxRule:
    return CalcSyntaxRule()


def ctx_for(formula: str):
    return make_ctx(
        make_twb(datasources=(Ds(name="ds", calcs=(Calc(name="C_1", formula=formula),)),))
    )


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("SUM([매출]) / SUM([수량]", "닫히지 않았다"),
        ("SUM([매출]))", "여는 `(` 없이"),
        ("IF [A] > 0 THEN 1 ELSE 0", "`END`가 모자란다"),
        ("IF [A] > 0 THEN 1 ELSE 0 END END", "`END`가 남는다"),
        ("{FIXED [지역] : SUM([매출])", "LOD"),
        ("IF [A] > 0 1 ELSE 0 END", "`THEN`이 없다"),
        ("CASE [A] ELSE 0 END", "`WHEN`이 없다"),
        ("THEN 1 ELSE 0", "없이 `THEN`이 나온다"),
    ],
)
def test_broken_syntax_is_a_warning(rule: CalcSyntaxRule, formula: str, expected: str) -> None:
    """실측으로 확인한 8종. 파일은 열리므로 ERROR가 아니다."""
    findings = rule.check(ctx_for(formula))

    assert [f.severity for f in findings] == [Severity.WARNING]
    assert expected in findings[0].message
    assert findings[0].fix
    assert findings[0].line is not None


@pytest.mark.parametrize(
    ("formula", "why"),
    [
        ("IF [A] > 0 THEN 1 ELSE 0 END", "평범한 IF"),
        ("IF [A] THEN 1 ELSEIF [B] THEN 2 ELSE 3 END", "ELSEIF는 END를 요구하지 않는다"),
        ("CASE [A] WHEN 1 THEN 2 ELSE 3 END", "평범한 CASE"),
        ("{FIXED [지역], [연도] : SUM([매출])}", "LOD의 콤마·중괄호"),
        ("IF [A] THEN 'END' ELSE \"(\" END", "문자열 안의 키워드·괄호"),
        ("// IF THEN END (\nSUM([매출])", "주석 안의 키워드·괄호"),
        ("/* ( IF */ SUM([매출])", "블록 주석 안"),
        ("SUM([[괄호]](복사본)_123])", "필드 이름 안의 `]]` 이스케이프"),
    ],
)
def test_valid_syntax_is_silent(rule: CalcSyntaxRule, formula: str, why: str) -> None:
    """거짓양성 함정 — 주석·문자열·필드명 안의 글자를 세면 정상본이 통째로 걸린다."""
    assert rule.check(ctx_for(formula)) == [], why


def test_only_the_most_fundamental_problem_is_reported(rule: CalcSyntaxRule) -> None:
    """한 수식에서 여러 개를 뱉지 않는다 — 어디부터 고칠지 알 수 없게 된다.

    아래는 괄호도 깨졌고 `END`도 없지만, 보고는 괄호 하나다.
    """
    findings = rule.check(ctx_for("IF SUM([A] > 0 THEN 1 ELSE 0"))

    assert len(findings) == 1
    assert "닫히지 않았다" in findings[0].message


def test_the_field_name_is_in_the_message(rule: CalcSyntaxRule) -> None:
    """사람이 Tableau에서 찾아갈 수 있어야 한다 — xpath만으로는 못 찾는다."""
    ctx = make_ctx(
        make_twb(
            datasources=(
                Ds(name="ds", calcs=(Calc(name="C_1", caption="영업이익률", formula="SUM([A]"),)),
            )
        )
    )

    findings = rule.check(ctx)

    assert "영업이익률" in findings[0].message


def test_missing_tree_reports_the_skip(rule: CalcSyntaxRule) -> None:
    """검사 못 했으면 말한다 — 빈 리스트는 '전부 검사했고 문제없음'으로 기록된다 (02 AC9)."""
    ctx = ctx_for("SUM([A])")
    ctx.raw_tree = None

    assert rule.check(ctx) == []
    assert [n.status for n in ctx.notes_for(rule.id)] == [CoverageStatus.SKIPPED]
