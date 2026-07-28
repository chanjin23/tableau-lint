"""L-B rule ⑥ [MVP]: 매니페스트 게이트 일관성.

유효 문법 = `<workbook version>` 선언 × `<document-format-change-manifest>` 항목 집합.
기능 요소를 쓰면서 대응 매니페스트 항목을 선언하지 않으면
`no declaration found for element '<요소>'`로 **로드 거부**된다.

**공식 XSD가 원리적으로 못 잡는 실패 클래스다** — XSD는 `manual-sort`를 무조건 허용하므로
매니페스트 없이 쓴 파일은 L-A를 통과하고 Tableau에서 열리지 않는다.
AC3(무거짓통과) 위반의 실증 사례이자 이 규칙의 존재 이유
(docs/05-xsd-spike.md F5, docs/06-rule-candidates.md R1).

대응표는 `data/manifest_gates.json`에 데이터로 둔다 (`config.manifest_gates_path()`).
현재 실측 확보분은 2쌍뿐이다 — **표에 있는 기능만 ERROR**, 표에 없는 요소를 추측해
ERROR를 내지 않는다 (docs/02-specification.md S1-6). 대응표 확장 경로는 03-design D8.

스캐폴딩 = 등록 + no-op. 구현하려면 트리에서 게이팅 대상 요소의 실사용 여부를 봐야 하는데,
현재 `check(model)`은 파싱된 트리를 받지 못한다 (미해결 설계 항목).
"""

from __future__ import annotations

from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class ManifestGatesRule(RuleBase):
    id = "manifest.gates"
    stage = Stage.SEMANTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        # 구현: config.manifest_gates_path() 로드 → 트리에서 gates[].element 사용 여부 탐색
        #       → 사용 중인데 requires 항목이 model.manifest_features에 없으면 ERROR.
        #       표에 없는 요소는 검사하지 않는다(침묵) — 추측 ERROR 금지.
        return []
