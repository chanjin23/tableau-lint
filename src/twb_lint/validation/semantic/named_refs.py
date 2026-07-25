"""L-B rule ③ [MVP]: named-content 참조 무결성.

worksheet↔dashboard↔window 이름/GUID 링크를 트리 순회로 대조 →
끊긴(dangling) 참조를 ERROR로 flag.

스캐폴딩 = 등록 + no-op.
"""

from __future__ import annotations

from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class NamedRefsRule(RuleBase):
    id = "named.refs"
    stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        return []
