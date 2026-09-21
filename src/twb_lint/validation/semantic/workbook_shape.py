"""L-B rule ⑱: 워크북 골격 — `<worksheets>`가 **있는데 비어 있으면** 안 된다.

**증상이 조용하다.** 로드 거부 대화상자가 뜨지 않는다 — Tableau는 아무 말 없이
빈 워크북(`문서1`)을 대신 띄운다. 창 제목이 `Tableau - <파일명>`이 되지 않고
`Tableau - 문서1`에 머무는 것이 유일한 표시다. 저작 루프에서 가장 놓치기 쉬운 층이다.

## 이 규칙의 핵심은 **워크시트 개수가 아니다**

최초안은 *"워크시트가 0개면 ERROR"*였고, **틀렸다.** 실파일 303개를 두 모양으로
가르면 반대 방향으로 깨끗하게 갈린다 (2026-09-21 실측):

| 모양 | 실파일 | Tableau |
|---|---|---|
| `<worksheets><worksheet …/></worksheets>` | 285 | 정상 |
| **`<worksheets />`** (요소는 있는데 비었다) | **2** — 실패01·실패02뿐 | **안 열린다** |
| `<worksheets>` 요소 자체가 없다 | **16** — 전부 KPMG 템플릿 | **열린다** ✅ 사용자 확인 |

워크시트 0개인 파일이 18개인데 그중 16개가 **정상적으로 열린다.** 개수로 걸었으면
그 16개가 전부 거짓 ERROR였다 — AC7 붕괴다.

가르는 것은 **스키마다.** `<worksheets>`는 선택 요소지만(minOccurs=0), *있으면*
`<worksheet>`를 최소 1개 요구한다. 그래서 `<worksheets />`는 구문 위반이고 요소
생략은 유효하다. 로더가 그 차이를 그대로 반영한다.

## 인과

- 실패02(`<worksheets />`)를 열면 조용히 `문서1`로 대체된다
- 여기에 워크시트 1개를 넣은 실패03은 **증상이 바뀐다** — 대체가 사라지고 다음 층
  (⑥-c 속성 게이트)의 로드 거부가 뜬다. 그 층까지 고치자 **열렸다**

한 층을 고치면 다음 층이 보인다는 이 프로젝트의 전제 그대로다 (01 v2.0 · 05 F5-p).

## 왜 L-A에 맡기지 않는가

`<worksheets />`는 XSD가 `Missing child element(s)`로 잡기는 한다. 하지만 그 클래스는
`explain-data` 거짓양성과 **같은 오류코드·같은 문구**를 써서 A3 정책이 통째로
WARNING으로 떨어뜨린다 (05 F3·F8). 정책을 흔들면 정상본이 무너지므로
(`tests/unit/test_severity_policy.py`가 그 한 줄을 지킨다), **`worksheets` 자리
하나만** 실측 근거로 ERROR를 내는 좁은 규칙을 따로 둔다.
"""

from __future__ import annotations

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

        block = ctx.raw_tree.find("worksheets")
        if block is None:
            # 요소 생략은 유효하다 — 실파일 16개(KPMG 템플릿)가 이 모양으로 **열린다**.
            # 여기서 ERROR를 내면 그 16개가 전부 거짓양성이 된다 (AC7).
            ctx.note_skip(
                self.id,
                "`<worksheets>` 요소가 없다 — 선택 요소이고 실측 16개가 이 모양으로 "
                "정상 로드되므로 판정 대상이 아니다",
                scope="worksheets",
            )
            return []

        if len(block.findall("worksheet")):
            return []

        return [
            Finding(
                severity=Severity.ERROR,
                rule_id=self.id,
                location="workbook/worksheets",
                line=block.sourceline,
                message=(
                    "`<worksheets>`가 비어 있다 — Tableau가 이 파일 대신 빈 "
                    "워크북(`문서1`)을 띄운다. 오류 대화상자가 뜨지 않아 성공으로 "
                    "오인하기 쉽다"
                ),
                fix=(
                    "`<worksheets>` 아래에 워크시트를 최소 1개 넣는다 — 그 시트는 "
                    "`<windows>`에 `<window class='worksheet'>`로도 나타나야 한다 "
                    "(규칙 ③). 대시보드 레이아웃만 담는 템플릿이라면 `<worksheets>` "
                    "요소 자체를 **빼는** 것도 유효하다 (실측 16개가 그 모양이다)."
                ),
            )
        ]
