"""L-B rule ③ [MVP]: named-content 참조 무결성.

대시보드에 배치된 시트 하나가 성립하려면 **세 곳이 맞아야 한다** (03 D3 · 06 R2·R3):

```
<dashboard>/<zone name='S'>            배치
<worksheets>/<worksheet name='S'>      정의
<windows>/<window class='dashboard'>/<viewpoints>/<viewpoint name='S'>
<windows>/<window class='worksheet' name='S'>
```

하나라도 없으면 Tableau가 열지 못한다 — viewpoint 누락은 내부 오류 2805CF18이다.
**XSD는 이걸 원리적으로 못 잡는다**(이름 대조는 문법이 아니다). AC3 무거짓통과의
실증 사례이자 이 규칙의 존재 이유다.

**이 규칙만 ERROR를 낸다.** 근거는 실측이다 — 표본 10개 전부에서
`zone ⊆ worksheets`이고 `zone ⊆ viewpoints`이며 `worksheets == worksheet_windows`다.
즉 정상 파일에서 이 규칙은 침묵한다 (AC7). 규칙 ①②가 WARNING인 것과 대비된다:
저쪽은 정상 파일에도 잔재가 있다는 실측이 있었다 (03 D3.6.3).

**배치되지 않은 시트는 보고하지 않는다.** 대시보드에 없는 워크시트는 정상이며
(표본 10개 중 1개가 그렇다) 파일이 열리는 데 아무 영향이 없다.
"""

from __future__ import annotations

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class NamedRefsRule(RuleBase):
    id = "named.refs"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        model = ctx.model
        if not model.dashboards:
            # 대시보드가 없으면 3자 대조 자체가 성립하지 않는다. "문제없음"이 아니라
            # "검사할 것이 없었다"이므로 그렇게 말한다 (02 S5).
            ctx.note_skip(self.id, "대시보드가 없어 3자 대조를 하지 않았다")
            return []

        findings: list[Finding] = []
        for dash in sorted(model.dashboards.values(), key=lambda d: d.name):
            for sheet in dash.sheet_zones:
                where = f"dashboard '{dash.name}' / zone '{sheet}'"
                if sheet not in model.worksheets:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_id=self.id,
                            location=where,
                            message=f"배치된 시트 '{sheet}'의 정의가 `<worksheets>`에 없다",
                            fix="존을 지우거나 해당 워크시트 정의를 되살린다.",
                        )
                    )
                    continue  # 정의가 없으면 아래 둘은 당연히 없다 — 같은 사실을 3번 말하지 않는다
                if sheet not in dash.viewpoints:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_id=self.id,
                            location=where,
                            message=(
                                f"시트 '{sheet}'에 대응하는 viewpoint가 대시보드 window에 없다 "
                                "— 로드 시 내부 오류 2805CF18"
                            ),
                            fix=(
                                f"`<window class='dashboard' name='{dash.name}'>`의 "
                                f"`<viewpoints>`에 `<viewpoint name='{sheet}' />`를 넣는다."
                            ),
                        )
                    )
                if sheet not in model.worksheet_windows:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_id=self.id,
                            location=where,
                            message=f"시트 '{sheet}'의 `<window class='worksheet'>`가 없다",
                            fix=(
                                "`<windows>`에 "
                                f"`<window class='worksheet' name='{sheet}'>`를 넣는다."
                            ),
                        )
                    )
        return findings
