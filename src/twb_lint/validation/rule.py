"""검증 규칙 프로토콜 + 베이스.

새 규칙 = `RuleBase` 상속 + `@register`. 코어 수정 불필요.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from twb_lint.models import Finding, WorkbookModel


class Stage(StrEnum):
    """검증 단계. 엔진은 SYNTACTIC → SEMANTIC 순으로 돈다."""

    SYNTACTIC = "syntactic"  # L-A (XSD)
    SEMANTIC = "semantic"  # L-B (calc·참조·메타)


@runtime_checkable
class Rule(Protocol):
    """검증 규칙 인터페이스."""

    id: str
    stage: Stage

    def check(self, model: WorkbookModel) -> list[Finding]:
        """모델을 검사해 findings를 반환한다 (없으면 빈 리스트)."""
        ...


class RuleBase:
    """규칙 베이스 클래스. 하위는 `id`·`stage`를 정의하고 `check`를 구현한다."""

    id: str = "base"
    stage: Stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        return []
