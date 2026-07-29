"""스캐폴딩 스모크 — 부팅·레지스트리·모델·파이프라인 관통.

`@pytest.mark.stub` 표시가 붙은 테스트는 **stub 상태의 사실을 단언**한다.
실로직이 들어오면 반드시 깨져야 하는 테스트다 — 깨지면 고칠 것은 코드가 아니라 이 테스트다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twb_lint.models import (
    CoverageStatus,
    Finding,
    Severity,
    ValidationReport,
    WorkbookModel,
)
from twb_lint.validation import engine
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import all_rules, rules_for
from twb_lint.validation.rule import Stage


def test_registry_auto_collects_mvp_rules() -> None:
    ids = {r.id for r in all_rules()}
    # L-A 1 + L-B MVP 4규칙(①②③⑥)이 자동 등록돼야 한다.
    assert {
        "xsd.schema",
        "calc.functions",
        "calc.field_refs",
        "named.refs",
        "manifest.gates",
    } <= ids


def test_rules_partitioned_by_stage() -> None:
    assert any(r.id == "xsd.schema" for r in rules_for(Stage.SYNTACTIC))
    semantic_ids = {r.id for r in rules_for(Stage.SEMANTIC)}
    assert {"calc.functions", "calc.field_refs", "named.refs", "manifest.gates"} <= semantic_ids


def test_input_stage_owns_no_rule_files() -> None:
    """`Stage.INPUT`에는 규칙이 등록되지 않는다 — 엔진이 직접 소유하는 단계다 (A2).

    누군가 `Stage.INPUT` 규칙 파일을 추가하면, 컨텍스트를 못 만들어서 실패한 상황을
    컨텍스트를 받는 규칙이 판정하는 순환이 생긴다.
    """
    assert rules_for(Stage.INPUT) == []


def test_report_passed_is_gate() -> None:
    ok = ValidationReport(findings=())
    assert ok.passed is True

    warn = ValidationReport(findings=(Finding(Severity.WARNING, "x", "loc", "msg"),))
    assert warn.passed is True  # WARNING은 게이트 통과

    err = ValidationReport(findings=(Finding(Severity.ERROR, "x", "loc", "msg"),))
    assert err.passed is False
    assert len(err.errors) == 1


class _FakeRule:
    """정렬 검증용 규칙. 일부러 뒤섞인 순서로 findings를 낸다."""

    def __init__(
        self,
        rule_id: str,
        stage: Stage,
        locations: tuple[str, ...],
        lines: tuple[int | None, ...] | None = None,
    ) -> None:
        self.id = rule_id
        self.stage = stage
        self._locations = locations
        self._lines = lines or (None,) * len(locations)

    def check(self, ctx: ValidationContext) -> list[Finding]:  # noqa: ARG002
        return [
            Finding(Severity.WARNING, self.id, loc, "msg", line=line)
            for loc, line in zip(self._locations, self._lines, strict=True)
        ]


def _ctx() -> ValidationContext:
    return ValidationContext(model=WorkbookModel(source=Path("fake.twb")))


def test_findings_order_is_deterministic() -> None:
    """findings 순서 = stage → rule_id → line → location 고정 (docs/03-design.md D3).

    규칙 등록 순서(pkgutil = 파일시스템 순서)가 출력에 새면 골든셋 diff에 노이즈가 난다.
    """
    # 일부러 역순으로 넣는다: 시맨틱 먼저, rule_id 역순, location 역순.
    rules = [
        _FakeRule("b.rule", Stage.SEMANTIC, ("z", "a")),
        _FakeRule("a.rule", Stage.SEMANTIC, ("m",)),
        _FakeRule("xsd.schema", Stage.SYNTACTIC, ("line-2", "line-1")),
    ]
    report = engine.validate_model(_ctx(), rules=rules)

    assert [(f.rule_id, f.location) for f in report.findings] == [
        ("xsd.schema", "line-1"),  # SYNTACTIC이 먼저
        ("xsd.schema", "line-2"),
        ("a.rule", "m"),  # 이후 SEMANTIC, rule_id 오름차순
        ("b.rule", "a"),
        ("b.rule", "z"),  # 같은 규칙 안에서는 location 오름차순
    ]


def test_line_numbers_sort_numerically_not_lexically() -> None:
    """줄번호는 정수로 정렬한다 — 문자열이면 `line 10`이 `line 9`보다 앞선다 (A5)."""
    rule = _FakeRule(
        "xsd.schema",
        Stage.SYNTACTIC,
        ("a", "b", "c"),
        lines=(10, 2, 9),
    )
    report = engine.validate_model(_ctx(), rules=[rule])
    assert [f.line for f in report.findings] == [2, 9, 10]


def test_findings_without_line_come_first() -> None:
    """줄번호를 모르는 finding은 앞에 모인다 (결정론 + 읽는 순서 안정)."""
    rule = _FakeRule("r", Stage.SEMANTIC, ("a", "b"), lines=(5, None))
    report = engine.validate_model(_ctx(), rules=[rule])
    assert [f.line for f in report.findings] == [None, 5]


class _SkippingRule:
    """검사하지 못했다고 보고하는 규칙."""

    id = "skips.a.lot"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        ctx.note_skip(self.id, "테스트용 스킵")
        return []


def test_coverage_distinguishes_clean_from_unchecked() -> None:
    """findings가 비었다는 사실만으로 "문제없음"이라고 말하지 않는다 (A4 / 02 S5)."""
    quiet = _FakeRule("quiet.rule", Stage.SEMANTIC, ())
    report = engine.validate_model(_ctx(), rules=[quiet, _SkippingRule()])

    assert report.passed is True  # ERROR는 없다
    assert report.fully_covered is False  # 그러나 전부 검사한 것은 아니다

    by_id = {c.rule_id: c for c in report.coverage}
    assert by_id["quiet.rule"].status is CoverageStatus.RAN
    assert by_id["skips.a.lot"].status is CoverageStatus.SKIPPED
    assert by_id["skips.a.lot"].reason == "테스트용 스킵"


def test_missing_file_is_an_error_finding_not_an_exception() -> None:
    """파일 없음은 예외가 아니라 ERROR finding이다 (02 S5 / A2).

    호출자가 try/except와 게이트 판정을 따로 만들지 않도록 판정 경로를 하나로 유지한다.
    """
    report = engine.validate("does-not-exist.twb")

    assert report.passed is False
    assert [f.rule_id for f in report.errors] == [engine.INPUT_RULE_ID]
    assert "파일이 없다" in report.errors[0].message

    # 입력에서 멈췄으면 나머지 규칙은 "통과"가 아니라 "미실행"으로 남아야 한다.
    assert report.fully_covered is False
    skipped_ids = {c.rule_id for c in report.skipped}
    assert {"xsd.schema", "manifest.gates"} <= skipped_ids


def test_directory_and_bad_suffix_are_input_errors(tmp_path: Path) -> None:
    """디렉토리·엉뚱한 확장자도 같은 경로로 판정된다."""
    assert engine.validate(tmp_path).passed is False

    other = tmp_path / "notes.txt"
    other.write_text("not a workbook", encoding="utf-8")
    report = engine.validate(other)
    assert report.passed is False
    assert any("확장자" in f.message for f in report.errors)


@pytest.mark.stub
def test_stub_rules_report_themselves_as_unimplemented(tmp_path: Path) -> None:
    """**stub 사실을 고정한 테스트다 — 실로직이 들어오면 깨져야 한다.**

    지금은 규칙이 전부 `return []`이라 findings가 없다. 그러나 **조용히 통과하지는 않는다** —
    각 규칙이 "미구현이라 검사하지 못했다"를 coverage로 보고한다.

    구현이 들어오면 해당 규칙의 note가 사라지고 이 단언이 깨진다.
    그때 고칠 것은 **코드가 아니라 이 테스트다** (구현된 규칙을 목록에서 뺀다).
    """
    twb = tmp_path / "empty.twb"
    twb.write_text("<workbook />", encoding="utf-8")

    report = engine.validate(twb)
    unimplemented = {c.rule_id for c in report.skipped if c.reason == "규칙 미구현 (스캐폴딩)"}
    assert unimplemented == {"manifest.gates"}

    # xsd.schema만 **입력이 없어서** 스킵된다 — 미구현과 구분되는 별개의 사유다.
    reasons = {c.rule_id: (c.reason or "") for c in report.skipped}
    assert "미지원 릴리스" in reasons["xsd.schema"]  # source_build가 없어 릴리스 미확정
