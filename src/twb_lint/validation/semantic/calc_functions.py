"""L-B rule ① [MVP]: calc 함수 화이트리스트.

수식에서 함수 호출을 뽑아(`calc.extractor`) 버전별 화이트리스트와 대조한다.

**심각도는 WARNING 고정이다** (02 S1-6 · 07 G3). 목록에 없다는 것은 "그 함수가 없다"가
아니라 "**우리 목록이 불완전하다**"일 수 있다. 목록은 help.tableau.com 스크랩본이고
공식 사양이 아니다 — ERROR로 막으면 우리 데이터의 공백이 남의 정상 파일을 막는다.

근거: 표본 10개 수식 5,270건에서 함수 26종이 나왔고 218종 목록에 **미매칭 0건**이었다
(03 D3.7). 즉 이 규칙은 정상본에서 침묵한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from twb_lint import config
from twb_lint.calc.extractor import extract, formulas_in
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@lru_cache(maxsize=4)
def load_whitelist(functions_path: str) -> frozenset[str]:
    """함수 화이트리스트를 읽는다. **경로 기준으로 캐시** (MCP 상주 프로세스, AC5)."""
    data = json.loads(Path(functions_path).read_text(encoding="utf-8"))
    return frozenset(str(name).upper() for name in data["functions"])


@register
class CalcFunctionsRule(RuleBase):
    id = "calc.functions"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        release = config.release_from_source_build(ctx.model.source_build)
        path = config.functions_path(release)
        if path is None:
            ctx.note_skip(
                self.id,
                f"릴리스 {release or '(판별 불가)'}의 함수 목록이 없어 대조하지 못했다",
            )
            return []

        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 함수 대조를 하지 못했다")
            return []

        whitelist = load_whitelist(str(path))
        # 함수 이름별로 **1건씩만** 낸다. 환각 함수 하나가 calc 100개에 퍼져 있으면
        # 건당 보고는 리포트를 못 읽는 물건으로 만든다 — 첫 자리와 횟수를 함께 준다.
        first_seen: dict[str, tuple[str, int | None]] = {}
        counts: dict[str, int] = {}
        for el, formula in formulas_in(ctx.raw_tree):
            for name in sorted(extract(formula).functions):
                if name in whitelist:
                    continue
                counts[name] = counts.get(name, 0) + 1
                first_seen.setdefault(name, (_path_of(el), el.sourceline))

        return [
            Finding(
                severity=Severity.WARNING,
                rule_id=self.id,
                location=first_seen[name][0],
                message=(
                    f"`{name}`이 {release} 함수 목록에 없다 — 수식 {counts[name]}곳에서 쓰인다"
                ),
                fix=(
                    "함수 이름을 확인한다. 실제로 존재하는 함수라면 목록이 낡은 것이므로 "
                    "tools/scrape_functions.py를 다시 돌린다."
                ),
                line=first_seen[name][1],
            )
            for name in sorted(counts)
        ]


def _path_of(el: Any) -> str:
    """요소의 xpath. L-A finding의 `location`과 같은 표기를 쓴다."""
    return str(el.getroottree().getpath(el))
