"""L-B rule ⑥ [MVP]: 매니페스트 게이트 일관성.

유효 문법 = `<workbook version>` 선언 × `<document-format-change-manifest>` 항목 집합.
기능 요소를 쓰면서 대응 매니페스트 항목을 선언하지 않으면
`no declaration found for element '<요소>'`로 **로드 거부**된다.

**공식 XSD가 원리적으로 못 잡는 실패 클래스다** — XSD는 `manual-sort`를 무조건 허용하므로
매니페스트 없이 쓴 파일은 L-A를 통과하고 Tableau에서 열리지 않는다.
AC3(무거짓통과) 위반의 실증 사례이자 이 규칙의 존재 이유
(docs/05-xsd-spike.md F5, docs/06-rule-candidates.md R1).

규칙은 두 갈래다 (docs/05-xsd-spike.md F7 실측):

**⑥-a fcp 계열 — 대응표 불필요.** 매니페스트 항목 이름에도 fcp 접두사가 붙으며,
접두사를 벗기면 트리의 fcp 기능명과 표본 10/10에서 완전 일치한다.
`_.fcp.<F>....`를 쓰면 매니페스트에 `_.fcp.<F>.true...<F>`가 있어야 한다 —
기능명이 이름 안에 박혀 있어 조회표 없이 자기 자신에서 도출된다.

⚠️ **입력이 L-A와 다르다**: fcp 정규화는 요소의 소속 기능을 지운다
(`_.fcp.X.true...format` → `format`). ⑥-a는 **정규화 전 원본 트리**를 봐야 한다.

**⑥-b 일반 계열 — 대응표 필요.** 이름이 요소명과 다르다(`manual-sort`↔`SortTagCleanup`).
`data/manifest_gates.json`의 `gates` 대조 (`config.manifest_gates_path()`).
확보분은 2쌍뿐 — **표에 있는 기능만 ERROR**, 표에 없는 요소를 추측해 ERROR를 내지
않는다 (docs/02-specification.md S1-6). 항목 이름 19종은 확보됐으나 요소 매핑을 몰라
`known_items_unmapped`에 대기 중이다. 확보 경로 = 주입 실험 B (06-rule-candidates §D.1).

스캐폴딩 = 등록 + 입력 확인. `ctx.raw_tree`(정규화 전 원본)를 받게 됐으므로 설계 제약은
해소됐고, 남은 것은 로직뿐이다. 트리가 없으면 **조용히 통과시키지 않고 스킵을 보고**한다.
"""

from __future__ import annotations

from twb_lint.models import Finding
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class ManifestGatesRule(RuleBase):
    id = "manifest.gates"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        # ⑥-a는 정규화 **전** 원본 트리가 유일한 유효 입력이다 (05 F7 함의 2).
        # ctx.normalized_tree()를 쓰면 소속 기능이 지워져 항상 통과하는 규칙이 된다.
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "원본 트리가 없어 매니페스트 게이트를 검사하지 못했다")
            return []
        # 구현 ⑥-a: fcp.features_in_tree(ctx.raw_tree) 각각에 대해
        #           fcp.expected_manifest_item(f) ∈ fcp.manifest_items(ctx.raw_tree) 확인.
        #           인과 미검증이므로 WARNING (실험 A로 확정되면 ERROR).
        # 구현 ⑥-b: config.manifest_gates_path()의 gates[].element 사용 여부 탐색 →
        #           requires 항목 누락이면 ERROR. 표에 없는 요소는 침묵 — 추측 ERROR 금지.
        ctx.note_skip(self.id, "규칙 미구현 (스캐폴딩)")
        return []
