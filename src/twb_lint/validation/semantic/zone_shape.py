"""L-B rule ⑰: 대시보드 **존의 모양** — 종류가 요구하는 속성.

규칙 ③(`named.refs`)과 묻는 것이 다르다 — ③은 *"존이 가리키는 이름이 실재하는가"*,
⑰은 *"그 종류의 존이 갖춰야 할 것을 갖췄는가"*다. ⑬(`action.shape`)을 ⑩에서 가른
기준과 같다: 참조가 아니라 **모양**이다.

```xml
<zone type-v2='paramctrl' param='[Parameters].[매개 변수 1]'
      mode='compact' … />           <!-- mode가 컨트롤 위젯 종류다 -->
```

`mode`가 없으면 Tableau가 그릴 컨트롤을 정하지 못하고 **내부 오류로 파일을 못 연다**:

```
동작을 완료할 수 없습니다.
내부 오류 - 예기치 않은 오류가 발생하여 작업을 완료할 수 없습니다.
오류 코드: CB5AF9D4
```

**ERROR다.** 파일이 열리지 않는다(층 1). 오늘까지 ERROR는 매니페스트 게이트·XSD·
규칙 ③·⑭·⑮뿐이고, 여기가 여섯째다 — 2805CF18(규칙 ③)과 같은 내부 오류 계열이다.

**XSD는 이것을 잡지 못한다.** `mode`가 선택 속성으로 선언돼 있어 L-A가 통과시킨다.
"XSD 통과 ≠ 열린다"의 또 하나의 실증이다 (05 F5 계열).

실측 (2026-09-14, 실파일 238개): `paramctrl` 존 **2,475개 전부 `mode`를 갖는다**
(`compact` 2,473 · `type_in` 2). 반례 0. 같은 파일의 11:08 판에는 `paramctrl` 존이
0개였고 **열렸다** — 존 6개가 들어온 판에서만 내부 오류가 났다 (05 F5-n).

⚠️ **표로 갖는다.** 지금 근거가 선 것은 `paramctrl`/`mode` 하나뿐이라 그 하나만 넣었다.
다른 존 종류의 필수 속성은 **재기 전에는 추측하지 않는다** — 추측해서 넓히면 그 자리가
통째로 거짓양성이 되고, ERROR라서 정상 파일을 즉시 막는다 (02 S1-6 · AC7).
"""

from __future__ import annotations

from typing import Any

from twb_lint import fcp
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

REQUIRED_BY_ZONE_TYPE: dict[str, tuple[tuple[str, str, str], ...]] = {
    "paramctrl": (
        (
            "mode",
            "compact",
            "매개변수 컨트롤의 위젯 종류. 없으면 Tableau가 그릴 컨트롤을 정하지 못한다",
        ),
    ),
}
"""`type-v2` → 필수 `(속성, 권장값, 사람이 읽는 뜻)`.

**실측으로 반례 0을 확인한 것만 넣는다.** `paramctrl`/`mode`는 실파일 238개에서
2,475 : 0이다. 다른 종류를 넣기 전에 같은 방식으로 센다."""


@register
class ZoneShapeRule(RuleBase):
    id = "zone.shape"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 존의 모양을 검사하지 못했다")
            return []

        zones = [
            el
            for el in ctx.raw_tree.iter()
            if isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == "zone"
        ]
        if not zones:
            ctx.note_skip(self.id, "대시보드 존이 없어 검사할 것이 없다")
            return []

        checked = 0
        out: list[Finding] = []
        for zone in zones:
            requirements = REQUIRED_BY_ZONE_TYPE.get(zone.get("type-v2") or "")
            if requirements is None:
                continue
            checked += 1
            for attr, suggested, meaning in requirements:
                if zone.get(attr) is not None:
                    continue
                out.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_id=self.id,
                        location=_path_of(zone),
                        line=zone.sourceline,
                        message=(
                            f"`{zone.get('type-v2')}` 존({_where(zone)})에 `{attr}`가 없다 — "
                            f"{meaning}. 파일이 **내부 오류로 열리지 않는다**"
                        ),
                        fix=f"`{attr}='{suggested}'`를 더한다 (실파일 238개 중 2,473건이 이 값).",
                    )
                )

        if not checked:
            ctx.note_skip(
                self.id,
                "필수 속성을 아는 종류의 존이 없어 검사할 것이 없다 "
                f"(아는 종류: {', '.join(sorted(REQUIRED_BY_ZONE_TYPE))})",
            )
        return out


def _where(zone: Any) -> str:
    """사람이 대시보드에서 찾아갈 수 있는 표지."""
    for attr in ("param", "name", "id"):
        value = zone.get(attr)
        if value:
            return f"{attr}={value}"
    return "위치 미상"


def _path_of(el: Any) -> str:
    """요소의 xpath. L-A·규칙 ②의 `location`과 같은 표기를 쓴다."""
    return str(el.getroottree().getpath(el))
