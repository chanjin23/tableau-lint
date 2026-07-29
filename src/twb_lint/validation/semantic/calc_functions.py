"""L-B rule ① [MVP]: calc 함수 화이트리스트.

calc 수식에서 함수 호출을 추출(calc.extractor) → 버전별 함수 화이트리스트
(config.functions_path)와 대조 → 미지원/환각 함수를 ERROR로 flag.

스캐폴딩 = 등록 + no-op.
"""

from __future__ import annotations

from twb_lint.models import Finding
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class CalcFunctionsRule(RuleBase):
    id = "calc.functions"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        # 구현: ctx.model의 각 데이터소스 calc + groupfilter@expression을 extractor로 파싱
        #       → 함수 토큰을 config.functions_path(release) 목록과 대조.
        #       목록에 없음 = WARNING (우리 목록의 공백일 수 있다 — 02 S1-6).
        #       파싱 실패한 calc는 ctx.note_partial()로 보고하고 하위 검사를 건너뛴다.
        ctx.note_skip(self.id, "규칙 미구현 (스캐폴딩)")
        return []
