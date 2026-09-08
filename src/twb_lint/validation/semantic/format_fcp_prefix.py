"""L-B rule ⑮: 신기능 서식은 fcp 접두 요소로 써야 한다.

규칙 ⑥과 방향이 반대다. ⑥은 *"fcp 요소를 썼는데 매니페스트 항목이 없다"*를 잡고,
⑮는 *"fcp 요소로 썼어야 하는데 맨 `<format>`으로 썼다"*를 잡는다. 접두사가 없으면
쓰인 기능이 트리에 나타나지 않으므로 **⑥은 원리적으로 못 본다** — 볼 대상이 없다.

2026-09-07 실측 (MA_004 손익계산서 로드 거부 D2E8DA72):

```
Error(770,70): value 'corner-radius-top-left' not in enumeration      × 88건
```

린터는 이 파일에 `passed=True · findings=0`을 냈다. 공식 XSD가 `corner-radius-*`를
`StyleAttribute-ST`에 **열거하고 있어서**(`twb_2026.1.0.xsd` 4688~4692행) L-A가
통과시킨다. 유효 문법은 XSD가 아니라 매니페스트가 게이팅한다 (05 F5).

실파일 254개 대조 — 표기는 하나뿐이다:

| 표기 | 건수 |
|---|---|
| `<_.fcp.DashboardRoundedCorners.true...format attr='corner-radius…'>` | **11,033** |
| `<format attr='corner-radius…'>` | **88** — 거부된 그 파일 하나 |

```xml
<zone-style>
  <format attr='border-width' value='0' />                    <!-- 구기능: 맨 이름 -->
  <_.fcp.DashboardRoundedCorners.true...format
      attr='corner-radius-top-left' value='16' />             <!-- 신기능: fcp 접두 -->
</zone-style>
```

⚠️ **입력은 정규화 전 원본이다.** fcp 정규화가 접두사를 지우므로
(`_.fcp.X.true...format` → `format`) 정규화된 트리에서는 **정상 파일이 전부 위반으로
보인다** — 11,033건이 통째로 거짓양성이 된다 (05 F7 함의 2).

접두사를 붙이면 그다음 층(매니페스트 항목 누락)은 규칙 ⑥-a가 잡는다. ⑮는 자기 층만 본다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from twb_lint import fcp
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@dataclass(frozen=True)
class Surface:
    """fcp 접두가 요구되는 서식 표면 1종. 근거 수치를 항목마다 들고 있는다."""

    feature: str
    parent: str
    """부모 요소의 (접두사를 벗긴) 이름."""
    parent_element: str | None
    """부모의 `@element` 값. None이면 부모 이름만 본다."""
    predicate: Callable[[Any], bool]
    """이 `<format>`이 그 기능에 속하는가."""
    severity: Severity
    what: str
    symptom: str
    evidence: str


SURFACES = (
    Surface(
        feature="DashboardRoundedCorners",
        parent="zone-style",
        parent_element=None,
        predicate=lambda el: (el.get("attr") or "").startswith("corner-radius"),
        # 거부 메시지를 실측했다 (MA_004, 2026-09-07). ⑥-a와 달리 인과가 확인됐다.
        severity=Severity.ERROR,
        what="모서리 반경",
        symptom="value 'corner-radius-top-left' not in enumeration",
        evidence="실파일 254개: fcp 표기 11,033건 : 맨 표기 0건",
    ),
    Surface(
        feature="IndividualControlFormatting",
        parent="style-rule",
        parent_element="parameter-ctrl",
        predicate=lambda el: el.get("field") is not None,
        # 상관만 있고 거부는 미실측이다. 확인 전에 ERROR로 올리면 우리 추론이
        # 남의 정상 파일을 막는다 (02 S1-6).
        severity=Severity.WARNING,
        what="매개변수 컨트롤의 필드별 서식",
        symptom="로드 거부 미실측 — 상관만 확인됐다",
        evidence="실파일 254개: fcp 표기 468건 : 맨 표기 0건",
    ),
)
"""접두가 요구되는 표면. **측정한 것만 싣는다** — `legend` 계열은 맨 표기 238건 :
fcp 21건으로 혼재라 뺐다 (반례를 이해하기 전에는 규칙화하지 않는다)."""


@register
class FormatFcpPrefixRule(RuleBase):
    id = "format.fcp_prefix"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "원본 트리가 없어 서식 표기를 검사하지 못했다")
            return []

        # 표면별로 (건수, 첫 줄번호)를 모은다. 고칠 곳은 여럿이지만 원인은 하나다.
        counts: dict[int, int] = {}
        first_line: dict[int, int | None] = {}
        seen_format = False

        for el in ctx.raw_tree.iter():
            if not isinstance(el.tag, str) or fcp.strip_prefix(el.tag) != "format":
                continue
            seen_format = True
            if fcp.feature_of(el.tag) is not None:
                continue  # 이미 접두가 붙었다. 어느 기능인지는 ⑥-a의 몫이다
            parent = el.getparent()
            if parent is None or not isinstance(parent.tag, str):
                continue
            for i, surface in enumerate(SURFACES):
                if fcp.strip_prefix(parent.tag) != surface.parent:
                    continue
                if surface.parent_element and parent.get("element") != surface.parent_element:
                    continue
                if not surface.predicate(el):
                    continue
                counts[i] = counts.get(i, 0) + 1
                first_line.setdefault(i, getattr(el, "sourceline", None))

        if not seen_format:
            ctx.note_skip(self.id, "서식(`<format>`)이 없어 검사할 것이 없다")
            return []

        out: list[Finding] = []
        for i, count in sorted(counts.items()):
            surface = SURFACES[i]
            prefixed = f"_.fcp.{surface.feature}.true...format"
            out.append(
                Finding(
                    severity=surface.severity,
                    rule_id=self.id,
                    location=f"fcp:{surface.feature}",
                    line=first_line[i],
                    message=(
                        f"{surface.what}을(를) fcp 접두 없이 `<format>`으로 썼다 "
                        f"({count}곳) — {surface.symptom}"
                    ),
                    fix=(
                        f"요소 이름을 `<{prefixed}>`로 바꾼다. 매니페스트 항목은 규칙 ⑥-a가 "
                        f"이어서 잡는다 ({surface.evidence})"
                    ),
                )
            )
        return out
