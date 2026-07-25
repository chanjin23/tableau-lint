"""L-B rule ② [MVP]: calc 필드참조 해소.

calc 수식의 [Field]/[ds].[Field] 참조를 추출 → model.field_names 존재 확인 →
dangling 참조를 ERROR로 flag.

스캐폴딩 = 등록 + no-op.
"""

from __future__ import annotations

from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class CalcFieldRefsRule(RuleBase):
    id = "calc.field_refs"
    stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        return []
