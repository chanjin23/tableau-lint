"""핵심 데이터 모델 — 모든 검증 단계가 공유하는 통합 타입.

`Finding` 하나로 L-A(구문)·L-B(시맨틱)·향후 E2E 결과를 균일하게 표현한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    """결과 심각도. ERROR 하나라도 있으면 게이트 실패."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Finding:
    """단일 검증 결과.

    Attributes:
        severity: 심각도.
        rule_id: 규칙 식별자 (예: "calc.functions").
        location: 위치 (xpath, 라인, 필드명 등 사람이 짚을 수 있는 표시).
        message: 무엇이 잘못됐는지.
        fix: 제안 수정 (없으면 None).
    """

    severity: Severity
    rule_id: str
    location: str
    message: str
    fix: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """한 파일에 대한 전체 검증 결과 = mandatory gate 판정."""

    findings: tuple[Finding, ...] = ()

    @property
    def passed(self) -> bool:
        """ERROR 심각도 finding이 하나도 없으면 통과."""
        return not any(f.severity is Severity.ERROR for f in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)


@dataclass(slots=True)
class WorkbookModel:
    """검증 규칙에 넘기는 워크북 구조 모델 (C2 인스펙터 산출물).

    스캐폴딩 단계에서는 최소 필드만. 구현 단계에서 datasources/fields/calc/
    sheets/dashboards/참조 그래프로 확장한다.
    """

    source: Path
    """원본 .twb 또는 .twbx 경로."""

    twb_path: Path | None = None
    """unpack된 .twb 경로 (.twbx면 임시추출, .twb면 source와 동일)."""

    twb_version: str | None = None
    """<workbook version> 값 (예: "26.1"). XSD 버전 매칭에 사용."""

    field_names: set[str] = field(default_factory=set)
    """데이터소스 필드 + calc 이름 집합 (rule ② 참조 해소용)."""

    sheet_names: set[str] = field(default_factory=set)
    """worksheet/dashboard/window 이름 집합 (rule ③ 참조 무결성용)."""
