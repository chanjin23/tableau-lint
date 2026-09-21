"""L-B rule ⑱: 워크북 골격 — 워크시트가 최소 1개 있어야 한다.

**증상이 조용하다.** 로드 거부 대화상자가 뜨지 않는다 — Tableau는 아무 말 없이
빈 워크북(`문서1`)을 대신 띄운다. 창 제목이 `Tableau - <파일명>`이 되지 않고
`Tableau - 문서1`에 머무는 것이 유일한 표시다. 저작 루프에서 가장 놓치기 쉬운 층이다.

```xml
<worksheets />          <!-- 실패02: 요소는 있는데 비었다 -->
<dashboards>…</dashboards>   <!-- 대시보드는 145개 존을 갖고 있다 -->
```

2026-09-21 실측 (05 F5-p) — **층이 벗겨지는 것으로 인과가 확정됐다**:

| 파일 | `<worksheets>` | Tableau |
|---|---|---|
| 실패02 | 비어 있음 | 조용히 `문서1`로 대체 |
| 실패03 (= 실패02 + 시트 1개) | 시트 1개 | **증상이 바뀐다** — 대체 대신 로드 거부(D2E8DA72) |

증상이 사라진 게 아니라 **다음 층**(⑥ 속성 게이트)이 드러났다. 한 층을 고치면
다음 층이 보인다는 이 프로젝트의 전제 그대로다 (01 v2.0 · 05 F5).

**ERROR다.** 층 1(파일이 안 열린다)이고, 인과가 A/B로 확정됐다.

상관 — 실파일 253개 중 워크시트 0개는 **1개**뿐이다(`MA_015…/old/…템플릿_260702.twbx`).
그 1개는 이 파일과 **같은 모양**이다: 대시보드만 있고 워크시트가 없다. 정상본이라는
라벨이 붙은 적 없는 `old/` 폴더의 템플릿이라, 반례가 아니라 **같은 결함의 두 번째
표본**으로 본다 (규칙 ⑥ 30번 반복의 '골든셋 라벨 오염'과 같은 판단). 골든셋 회귀
테스트(`test_inspector_extracts_a_non_empty_model_from_every_workbook`)는 이미
`assert model.worksheets`로 이 불변식을 정상본에 걸고 있었다 — 규칙이 그 단언을
따라잡은 것이다.

⚠️ **L-A는 절반만 잡고, 그마저 WARNING이다.** `<worksheets />`가 비면 XSD가
`Missing child element(s)`를 내지만 그 클래스는 `explain-data` 거짓양성과 같은
오류코드를 써서 WARNING으로 떨어진다 (05 F3·F8, A3 정책). 게다가 `<worksheets>`
요소가 **통째로 없으면** XSD는 아예 침묵한다 — 선택 요소이기 때문이다. 두 모양 모두
워크시트 0개라는 같은 결함이므로 여기서 함께 잡는다.
"""

from __future__ import annotations

from typing import Any

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class WorkbookShapeRule(RuleBase):
    id = "workbook.shape"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 워크북 골격을 검사하지 못했다")
            return []

        if _worksheet_count(ctx.raw_tree):
            return []

        return [
            Finding(
                severity=Severity.ERROR,
                rule_id=self.id,
                location="workbook/worksheets",
                line=_worksheets_line(ctx.raw_tree),
                message=(
                    "워크북에 워크시트가 하나도 없다 — Tableau가 이 파일 대신 "
                    "빈 워크북(`문서1`)을 띄운다. 오류 대화상자가 뜨지 않아 "
                    "성공으로 오인하기 쉽다"
                ),
                fix=(
                    "`<worksheets>` 아래에 워크시트를 최소 1개 넣는다. 대시보드만 "
                    "필요하더라도 자리표시 시트가 있어야 하며, 그 시트는 "
                    "`<windows>`에 `<window class='worksheet'>`로도 나타나야 한다 "
                    "(규칙 ③)."
                ),
            )
        ]


def _worksheet_count(root: Any) -> int:
    """`<workbook>/<worksheets>/<worksheet>` 개수. 요소가 없으면 0이다."""
    return len(root.findall("worksheets/worksheet"))


def _worksheets_line(root: Any) -> int | None:
    """`<worksheets>`가 있으면 그 줄. 통째로 없으면 None (짚을 자리가 없다)."""
    block = root.find("worksheets")
    return None if block is None else block.sourceline
