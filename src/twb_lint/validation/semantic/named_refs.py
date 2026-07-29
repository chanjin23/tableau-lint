"""L-B rule ③ [MVP]: named-content 참조 무결성.

worksheet↔dashboard↔window 이름/GUID 링크를 트리 순회로 대조 →
끊긴(dangling) 참조를 ERROR로 flag.

스캐폴딩 = 등록 + no-op.
"""

from __future__ import annotations

from twb_lint.models import Finding
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class NamedRefsRule(RuleBase):
    id = "named.refs"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        # 구현: R2·R3 3자 대조 — dashboards[*].sheet_zones ↔ worksheets ↔
        #       dashboards[*].viewpoints ↔ worksheet_windows.
        #       dangling = ERROR / 고아 = WARNING (docs/06-rule-candidates.md R2·R3).
        ctx.note_skip(self.id, "규칙 미구현 (스캐폴딩)")
        return []
