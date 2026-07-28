"""스캐폴딩 스모크 — 부팅·레지스트리·모델·파이프라인 관통.

`@pytest.mark.stub` 표시가 붙은 테스트는 **stub 상태의 사실을 단언**한다.
실로직이 들어오면 반드시 깨져야 하는 테스트다 — 깨지면 고칠 것은 코드가 아니라 이 테스트다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twb_lint.models import Finding, Severity, ValidationReport, WorkbookModel
from twb_lint.validation import engine
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


def test_report_passed_is_gate() -> None:
    ok = ValidationReport(findings=())
    assert ok.passed is True

    warn = ValidationReport(
        findings=(Finding(Severity.WARNING, "x", "loc", "msg"),)
    )
    assert warn.passed is True  # WARNING은 게이트 통과

    err = ValidationReport(findings=(Finding(Severity.ERROR, "x", "loc", "msg"),))
    assert err.passed is False
    assert len(err.errors) == 1


class _FakeRule:
    """정렬 검증용 규칙. 일부러 뒤섞인 순서로 findings를 낸다."""

    def __init__(self, rule_id: str, stage: Stage, locations: tuple[str, ...]) -> None:
        self.id = rule_id
        self.stage = stage
        self._locations = locations

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        return [Finding(Severity.WARNING, self.id, loc, "msg") for loc in self._locations]


def test_findings_order_is_deterministic() -> None:
    """findings 순서 = stage → rule_id → location 고정 (docs/03-design.md D3).

    규칙 등록 순서(pkgutil = 파일시스템 순서)가 출력에 새면 골든셋 diff에 노이즈가 난다.
    """
    model = WorkbookModel(source=Path("fake.twb"))
    # 일부러 역순으로 넣는다: 시맨틱 먼저, rule_id 역순, location 역순.
    rules = [
        _FakeRule("b.rule", Stage.SEMANTIC, ("z", "a")),
        _FakeRule("a.rule", Stage.SEMANTIC, ("m",)),
        _FakeRule("xsd.schema", Stage.SYNTACTIC, ("line-2", "line-1")),
    ]
    report = engine.validate_model(model, rules=rules)

    assert [(f.rule_id, f.location) for f in report.findings] == [
        ("xsd.schema", "line-1"),  # SYNTACTIC이 먼저
        ("xsd.schema", "line-2"),
        ("a.rule", "m"),  # 이후 SEMANTIC, rule_id 오름차순
        ("b.rule", "a"),
        ("b.rule", "z"),  # 같은 규칙 안에서는 location 오름차순
    ]


@pytest.mark.stub
def test_stub_pipeline_passes_even_for_missing_file() -> None:
    """**stub 사실을 고정한 테스트다 — 실로직이 들어오면 깨져야 한다.**

    지금은 모든 규칙이 `return []`이고 I/O가 `NotImplementedError`라 파일을 아예 읽지
    않는다. 그래서 존재하지 않는 파일도 PASS가 된다 (docs/07-implementation-guide.md G7).

    구현 시 바뀔 것: 파일 없음·손상 ZIP은 예외가 아니라 **ERROR finding**으로 반환해야
    한다 (docs/02-specification.md S5). 그 책임 주체는 아직 설계 미결이다.
    이 테스트가 깨지면 **코드가 아니라 이 테스트를 ERROR finding 단언으로 교체한다.**
    """
    report = engine.validate("does-not-exist.twb")
    assert isinstance(report, ValidationReport)
    assert report.passed is True
    assert report.findings == ()
