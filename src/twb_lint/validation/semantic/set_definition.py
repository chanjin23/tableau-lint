"""L-B rule ⑨: 집합(`<group>`) 정의의 기반 필드.

집합은 **어느 필드의 부분집합인가**가 정의의 전부다. 그 필드를 못 찾으면 집합을 참조하는
계산(`[X] IN [X 집합]`)이 전부 깨진다 — 파일은 열리되 필드가 빨갛게 뜬다.

실측(2026-07-30, docs/05-xsd-spike.md F5-e) — 실파일 61개에 `<group>` 82개, 모양은 둘뿐이다:

```xml
<!-- 사용자가 만든 집합: ui-builder + 기반 필드가 member에 박힌다 -->
<group caption="C_LV1_KEY 집합" name="[C_LV1_KEY 집합]" user:ui-builder="filter-group">
  <groupfilter function="empty-level" member="[C_LV1_KEY]" user:ui-marker="enumerate"/>
</group>

<!-- 집합 액션이 만드는 자동 집합: hidden + 중첩 groupfilter(level-members) -->
<group name="[Action (Accs Nm)]" hidden="true" user:auto-column="sheet_link">
  <groupfilter function="crossjoin">
    <groupfilter function="level-members" level="[accs_nm]"/>
  </groupfilter>
</group>
```

MA_003 매출표는 **제3의 모양**이었다 — `auto-column="sets"`인데 자식이 빈
`<groupfilter function="union"/>` 하나뿐이라 기반 필드가 어디에도 없다.
그 집합을 쓰는 계산 3개(`C_LV1_토글`·`C_LV2_토글`·`C_계정과목_표시여부`)가 전부 깨졌다.

**WARNING이다** (02 S1-6). 파일은 열린다.

⚠️ 모양을 열거하지 않고 **기반 필드의 유무**만 본다. 모양은 릴리스마다 늘 수 있지만
"집합에는 기반 필드가 있어야 한다"는 성질은 바뀌지 않는다. 속성 이름을 열거하면
새 모양이 나올 때마다 거짓양성이 난다.
"""

from __future__ import annotations

from typing import Any

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

BASE_FIELD_ATTRS = ("member", "level", "column")
"""기반 필드가 실릴 수 있는 속성. 실측 82개 group에서 이 셋 밖은 없었다."""


@register
class SetDefinitionRule(RuleBase):
    id = "set.definition"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 집합 정의를 검사하지 못했다")
            return []

        groups = list(ctx.raw_tree.iter("group"))
        if not groups:
            ctx.note_skip(self.id, "집합(`<group>`)이 없어 검사할 것이 없다")
            return []

        out: list[Finding] = []
        for group in groups:
            if _base_field_of(group) is not None:
                continue
            name = (group.get("caption") or group.get("name") or "(이름 없음)").strip("[]")
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(group),
                    line=group.sourceline,
                    message=(
                        f"집합 `{name}`에 기반 필드가 없다 — "
                        "이 집합을 참조하는 계산(`… IN [집합]`)이 전부 깨진다"
                    ),
                    fix=(
                        "`<groupfilter>`에 기반 필드를 넣는다 — 사용자 집합은 "
                        '`function="empty-level" member="[필드]"`, '
                        '집합 액션이 만든 것은 중첩 `function="level-members" level="[필드]"`.'
                    ),
                )
            )
        return out


def _base_field_of(group: Any) -> str | None:
    """이 집합이 어느 필드 위에 서 있는가. 못 찾으면 `None`."""
    for el in group.iter():
        if el is group:
            continue
        for attr in BASE_FIELD_ATTRS:
            value = el.get(attr)
            if value:
                return str(value)
    return None


def _path_of(el: Any) -> str:
    return str(el.getroottree().getpath(el))
