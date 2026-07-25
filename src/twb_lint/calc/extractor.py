"""calc 수식에서 함수 호출·필드 참조를 추출한다 (Lark 기반).

rule ①(함수 화이트리스트)·②(필드참조 해소)가 소비한다.
스캐폴딩 단계 = 시그니처 + 결과 타입. 구현 단계에서 grammar.lark로 파싱.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CalcRefs:
    """한 calc 수식에서 뽑아낸 참조들."""

    functions: set[str] = field(default_factory=set)
    """호출된 함수명 (대문자 정규화)."""

    field_refs: set[str] = field(default_factory=set)
    """참조된 필드명 ([Field] / [ds].[Field])."""


def extract(formula: str) -> CalcRefs:
    """calc 수식 문자열에서 함수·필드 참조를 추출한다."""
    raise NotImplementedError("scaffold: calc.extractor.extract")
