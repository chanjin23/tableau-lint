"""스캐폴딩 스모크 — 부팅·레지스트리·모델·파이프라인 관통."""

from __future__ import annotations

from twb_lint.models import Finding, Severity, ValidationReport
from twb_lint.validation import engine
from twb_lint.validation.registry import all_rules, rules_for
from twb_lint.validation.rule import Stage


def test_registry_auto_collects_mvp_rules() -> None:
    ids = {r.id for r in all_rules()}
    # L-A 1 + L-B MVP 3규칙이 자동 등록돼야 한다.
    assert {"xsd.schema", "calc.functions", "calc.field_refs", "named.refs"} <= ids


def test_rules_partitioned_by_stage() -> None:
    assert any(r.id == "xsd.schema" for r in rules_for(Stage.SYNTACTIC))
    semantic_ids = {r.id for r in rules_for(Stage.SEMANTIC)}
    assert {"calc.functions", "calc.field_refs", "named.refs"} <= semantic_ids


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


def test_validate_pipeline_runs_on_twb(tmp_path: object) -> None:
    # stub 파이프라인이 관통해 빈 통과 리포트를 낸다 (파일 미존재여도 stub은 미접근).
    fake = "workbook.twb"
    report = engine.validate(fake)
    assert isinstance(report, ValidationReport)
    assert report.passed is True
