"""L-B rule ⑥ [MVP]: 매니페스트 게이트 일관성.

유효 문법 = `<workbook version>` 선언 × `<document-format-change-manifest>` 항목 집합.
기능 요소를 쓰면서 대응 매니페스트 항목을 선언하지 않으면
`no declaration found for element '<요소>'`로 **로드 거부**된다.

**공식 XSD가 원리적으로 못 잡는 실패 클래스다** — XSD는 `manual-sort`를 무조건 허용하므로
매니페스트 없이 쓴 파일은 L-A를 통과하고 Tableau에서 열리지 않는다
(docs/05-xsd-spike.md F5, docs/06-rule-candidates.md R1).

규칙은 두 갈래이고 **심각도가 다르다** (05 F7 실측):

| | 대응표 | 심각도 | 왜 |
|---|---|---|---|
| ⑥-a fcp 계열 | 불필요 (구조에서 도출) | **WARNING** | 항목 삭제 → 로드 거부의 인과가 미검증 |
| ⑥-b 일반 계열 | `manifest_gates.json` | **ERROR** | 로드 거부 메시지가 실측으로 확인됨 |

⚠️ **입력이 L-A와 다르다**: fcp 정규화는 요소의 소속 기능을 지운다
(`_.fcp.X.true...format` → `format`). ⑥-a는 **정규화 전 원본 트리**를 봐야 한다.
`ctx.normalized_tree()`를 쓰면 항상 통과하는 규칙이 된다 (계약 테스트가 감시한다).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from twb_lint import config, fcp
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@lru_cache(maxsize=2)
def load_gates(gates_path: str) -> tuple[tuple[str, tuple[str, ...], str], ...]:
    """대응표를 `(요소, 필요 항목들, 증상)`으로 읽는다. 경로 기준 캐시 (AC5)."""
    data = json.loads(Path(gates_path).read_text(encoding="utf-8"))
    return tuple(
        (str(g["element"]), tuple(str(r) for r in g["requires"]), str(g.get("symptom", "")))
        for g in data.get("gates", ())
    )


@lru_cache(maxsize=2)
def load_unmapped(gates_path: str) -> tuple[str, ...]:
    """요소 매핑을 모르는 매니페스트 항목들. **검사할 수 없다는 사실**을 보고하는 데 쓴다."""
    data = json.loads(Path(gates_path).read_text(encoding="utf-8"))
    return tuple(str(i) for i in data.get("known_items_unmapped", {}).get("items", ()))


@register
class ManifestGatesRule(RuleBase):
    id = "manifest.gates"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        # ⑥-a는 정규화 **전** 원본 트리가 유일한 유효 입력이다 (05 F7 함의 2).
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "원본 트리가 없어 매니페스트 게이트를 검사하지 못했다")
            return []

        gates_path = config.manifest_gates_path()
        if gates_path is None:
            ctx.note_skip(self.id, "매니페스트 대응표(manifest_gates.json)가 없다")
            return []

        declared = fcp.manifest_items(ctx.raw_tree)
        findings = self._fcp_findings(ctx.raw_tree, declared)
        findings += self._table_findings(ctx.raw_tree, declared, str(gates_path))

        unmapped = load_unmapped(str(gates_path))
        if unmapped:
            # 항목 이름은 알지만 어떤 요소가 그것을 요구하는지 모른다 → 검사 자체가 불가능하다.
            # 조용히 넘기면 "매니페스트를 전부 검사했다"로 읽힌다 (02 S5).
            ctx.note_partial(
                self.id,
                f"요소 매핑을 모르는 매니페스트 항목 {len(unmapped)}종은 검사하지 못했다 "
                "(확보 경로 = 주입 실험 B, 06 §D.1)",
                scope="manifest-unmapped",
            )
        return findings

    def _fcp_findings(self, root: Any, declared: set[str]) -> list[Finding]:
        """⑥-a — 쓴 fcp 기능마다 대응 항목이 선언돼 있는가.

        **WARNING이다.** 표본 10/10에서 관계가 성립한다는 것은 확인했지만, 항목을
        지우면 실제로 로드가 거부되는지(인과)는 확인하지 못했다. 확인 전에 ERROR로
        올리면 우리 추론이 남의 정상 파일을 막는다 (02 S1-6).
        """
        out: list[Finding] = []
        for feature in sorted(fcp.features_in_tree(root)):
            expected = fcp.expected_manifest_item(feature)
            if expected in declared:
                continue
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=f"fcp:{feature}",
                    message=(
                        f"fcp 기능 '{feature}'를 쓰면서 매니페스트 항목 "
                        f"`{expected}`를 선언하지 않았다"
                    ),
                    fix=(
                        f"`<document-format-change-manifest>`에 `<{expected} />`를 넣는다."
                    ),
                )
            )
        return out

    def _table_findings(self, root: Any, declared: set[str], gates_path: str) -> list[Finding]:
        """⑥-b — 대응표에 있는 요소를 쓰면서 필요한 항목을 빠뜨렸는가.

        **표에 있는 기능만 판정한다.** 표에 없는 요소를 추측해 ERROR를 내지 않는다
        (02 S1-6). 확보분은 2쌍뿐이고, 나머지는 `known_items_unmapped`로 보고한다.
        """
        used = {fcp.strip_prefix(el.tag) for el in root.iter() if isinstance(el.tag, str)}
        out: list[Finding] = []
        for element, requires, symptom in load_gates(gates_path):
            if element not in used:
                continue
            missing = [item for item in requires if item not in declared]
            if not missing:
                continue
            out.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=self.id,
                    location=element,
                    message=(
                        f"`<{element}>`를 쓰면서 매니페스트 항목 {', '.join(missing)}을(를) "
                        f"선언하지 않았다 — 로드 거부: {symptom}"
                    ),
                    fix=(
                        "`<document-format-change-manifest>`에 "
                        + " · ".join(f"`<{item} />`" for item in missing)
                        + "를 넣는다."
                    ),
                )
            )
        return out
