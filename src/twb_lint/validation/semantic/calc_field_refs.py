"""L-B rule ② [MVP]: calc 필드참조 해소.

calc 수식의 [Field]/[ds].[Field] 참조를 추출 → `model.field_names(ds)` 존재 확인 →
dangling 참조를 ERROR로 flag.

주의 (docs/06-rule-candidates.md R9 비고, 함정 S9 실측):
- 참조 해소는 **데이터소스별 네임스페이스**로 한다. 플랫 집합으로 대조하면 동명 필드가
  있는 워크북에서 오통과 또는 거짓 dangling이 난다.
- caption이 아니라 **내부 name**으로 대조한다 (계산필드는 `[Calculation_...]`).
- **특수 네임스페이스 예외 필수**: `[:Measure Names]`·`[:Measure Values]`·
  `[Parameters].[…]`·집합/그룹/bin/계층. 과거 lint가 `[:Measure Names]`에서 오탐했다.
  예외 목록 밖이면 ERROR, 예외 후보가 의심되면 WARNING (S1-6).

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
