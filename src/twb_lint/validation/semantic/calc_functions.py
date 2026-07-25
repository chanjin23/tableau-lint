"""L-B rule ① [MVP]: calc 함수 화이트리스트.

calc 수식에서 함수 호출을 추출(calc.extractor) → 버전별 함수 화이트리스트
(config.functions_path)와 대조 → 미지원/환각 함수를 ERROR로 flag.

스캐폴딩 = 등록 + no-op.
"""

from __future__ import annotations

from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class CalcFunctionsRule(RuleBase):
    id = "calc.functions"
    stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        return []
