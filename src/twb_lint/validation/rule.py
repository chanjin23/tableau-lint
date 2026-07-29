"""검증 규칙 프로토콜 + 베이스.

새 규칙 = `RuleBase` 상속 + `@register`. 코어 수정 불필요.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from twb_lint.models import Finding
from twb_lint.validation.context import ValidationContext


class Stage(StrEnum):
    """검증 단계. 엔진은 INPUT → SYNTACTIC → SEMANTIC 순으로 돈다."""

    INPUT = "input"
    """파일을 읽을 수 있는가. **엔진이 직접 소유하며 규칙이 살지 않는 단계다.**

    파일 없음·손상 ZIP·`.twb` 아님은 예외가 아니라 ERROR finding이어야 하는데(02 S5),
    이 판정은 모델 생성 **전**에 나므로 `ValidationContext`조차 만들 수 없다.
    규칙에 맡기면 "컨텍스트를 못 만들어서 실패한 상황을 컨텍스트 받는 규칙이 판정한다"는
    순환이 된다. 그래서 엔진이 소유하되, 결과는 이 단계 이름을 달고 나간다 —
    호출자 입장에서 게이트 판정 경로가 하나로 유지된다 (docs/TODO A2)."""

    SYNTACTIC = "syntactic"  # L-A (XSD)
    SEMANTIC = "semantic"  # L-B (calc·참조·메타)


@runtime_checkable
class Rule(Protocol):
    """검증 규칙 인터페이스."""

    id: str
    stage: Stage

    def check(self, ctx: ValidationContext) -> list[Finding]:
        """컨텍스트를 검사해 findings를 반환한다 (없으면 빈 리스트).

        반환 **순서는 신경 쓰지 않아도 된다** — `engine.validate_model`이
        `stage → rule_id → line → location`으로 정렬해서 내보낸다.

        검사하지 못한 것이 있으면 `ctx.note_skip()`/`note_partial()`로 보고한다.
        빈 리스트를 반환하면서 아무 말도 하지 않으면 "전부 검사했고 문제없음"으로 기록된다.
        """
        ...


class RuleBase:
    """규칙 베이스 클래스. 하위는 `id`·`stage`를 정의하고 `check`를 구현한다."""

    id: str = "base"
    stage: Stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:  # noqa: ARG002
        return []
