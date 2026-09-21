"""L-B rule ⑥ [MVP]: 매니페스트 게이트 일관성.

유효 문법 = `<workbook version>` 선언 × `<document-format-change-manifest>` 항목 집합.
기능 요소를 쓰면서 대응 매니페스트 항목을 선언하지 않으면
`no declaration found for element '<요소>'`로 **로드 거부**된다.

**공식 XSD가 원리적으로 못 잡는 실패 클래스다** — XSD는 `manual-sort`를 무조건 허용하므로
매니페스트 없이 쓴 파일은 L-A를 통과하고 Tableau에서 열리지 않는다
(docs/05-xsd-spike.md F5, docs/06-rule-candidates.md R1).

규칙은 세 갈래이고 **전부 ERROR다** (⑥-a는 2026-09-21 실험 A로 인과가 확정됐다):

| | 대응표 | 무엇을 보는가 | 왜 ERROR |
|---|---|---|---|
| ⑥-a fcp | 불필요 (구조에서 도출) | `_.fcp.<F>…` 요소 | 항목만 지운 A/B 쌍이 거부됐다 (F5-p) |
| ⑥-b 일반 | `gates` | 요소 이름 | 로드 거부 메시지가 실측으로 확인됨 |
| ⑥-c 속성 | `attribute_gates` | **요소의 속성** | 〃 — 메시지가 속성을 지목한다 (F5-p) |

**매니페스트가 여는 것은 요소만이 아니다** (2026-09-21, schema 3). 거부 메시지가
요소가 아니라 속성을 지목하는 자리가 있다:

```
Error(40,69): attribute 'enable-sort-zone-taborder' is not declared for element 'dashboard'
```

`manifest_gates.json`의 `known_items_unmapped` 주석이 *"속성 게이트가 필요해지면
그때 스키마를 넓힌다"*고 예고했던 자리다.

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
def load_attribute_gates(
    gates_path: str,
) -> tuple[tuple[str, str, tuple[str, ...], str], ...]:
    """⑥-c 대응표를 `(요소, 속성, 필요 항목들, 증상)`으로 읽는다.

    표가 없는 구버전 데이터 파일과도 맞물리도록 키가 없으면 빈 튜플이다 — 데이터가
    낡았을 때 예외를 던지면 검사 전체가 멈춘다.
    """
    data = json.loads(Path(gates_path).read_text(encoding="utf-8"))
    return tuple(
        (
            str(g["element"]),
            str(g["attribute"]),
            tuple(str(r) for r in g["requires"]),
            str(g.get("symptom", "")),
        )
        for g in data.get("attribute_gates", ())
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
        findings += self._attribute_findings(ctx.raw_tree, declared, str(gates_path))

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

        **ERROR다 — 2026-09-21에 실험 A가 실행됐다** (05 F5-p, 06 R1-a).
        사용자가 한 줄만 다른 파일 두 개를 만들어 열었다:

        | 파일 | `_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners` | Tableau |
        |---|---|---|
        | 실패01 | **없음** | 오류 대화상자 `동작을 완료할 수 없습니다.` — 로드 거부 |
        | 실패02 | 있음 | 그 대화상자가 **사라진다** |

        나머지 바이트가 전부 같으므로 대화상자의 원인은 이 한 항목이다. 06 R1-a가
        *"인과 확정(실험 A) 전까지 WARNING. 확정되면 ERROR"*라고 예고한 자리다.

        상관도 다시 쟀다 — 실파일 253개에서 쓴 fcp 기능 **732쌍 전부** 대응 항목이
        선언돼 있다(반례 0). 두 관문(상관 N:0 + 인과 실험)을 다 통과했다 (impl 29의 교훈).
        """
        out: list[Finding] = []
        for feature in sorted(fcp.features_in_tree(root)):
            expected = fcp.expected_manifest_item(feature)
            if expected in declared:
                continue
            out.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=self.id,
                    location=f"fcp:{feature}",
                    message=(
                        f"fcp 기능 '{feature}'를 쓰면서 매니페스트 항목 "
                        f"`{expected}`를 선언하지 않았다 — 로드 거부: "
                        "오류 대화상자 `동작을 완료할 수 없습니다.`"
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
        (02 S1-6). 나머지는 `known_items_unmapped`로 보고한다.

        요소당 finding 1건이다 — 같은 요소가 수십 번 나와도 고칠 곳은 매니페스트 1군데다.
        대신 **첫 출현 줄번호**를 싣는다: Tableau의 거부 메시지가 줄 기준이라 대조가 된다.
        """
        first_line: dict[str, int | None] = {}
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            tag = fcp.strip_prefix(el.tag)
            if tag not in first_line:
                first_line[tag] = getattr(el, "sourceline", None)
        out: list[Finding] = []
        for element, requires, symptom in load_gates(gates_path):
            if element not in first_line:
                continue
            missing = [item for item in requires if item not in declared]
            if not missing:
                continue
            out.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=self.id,
                    location=element,
                    line=first_line[element],
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

    def _attribute_findings(
        self, root: Any, declared: set[str], gates_path: str
    ) -> list[Finding]:
        """⑥-c — 게이팅된 **속성**을 쓰면서 필요한 항목을 빠뜨렸는가.

        `_table_findings`와 정책이 같다 — 표에 있는 쌍만 판정하고, 쌍당 finding 1건에
        첫 출현 줄번호를 싣는다. 다른 것은 **무엇을 세는가**뿐이다: 요소의 존재가
        아니라 `요소@속성`의 존재를 센다.

        거부 메시지가 줄·열을 준다(`Error(40,69)`)는 점에서 줄번호가 특히 값지다.
        """
        out: list[Finding] = []
        for element, attribute, requires, symptom in load_attribute_gates(gates_path):
            line = _first_line_with_attribute(root, element, attribute)
            if line is False:
                continue
            missing = [item for item in requires if item not in declared]
            if not missing:
                continue
            out.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=self.id,
                    location=f"{element}@{attribute}",
                    line=line or None,
                    message=(
                        f"`<{element}>`에 속성 `{attribute}`를 쓰면서 매니페스트 항목 "
                        f"{', '.join(missing)}을(를) 선언하지 않았다 — 로드 거부: {symptom}"
                    ),
                    fix=(
                        "`<document-format-change-manifest>`에 "
                        + " · ".join(f"`<{item} />`" for item in missing)
                        + f"를 넣는다 (속성 `{attribute}`를 지워도 거부는 사라지지만 "
                        "그 설정을 잃는다)."
                    ),
                )
            )
        return out


def _first_line_with_attribute(root: Any, element: str, attribute: str) -> int | None | bool:
    """`<element attribute=…>`의 첫 출현 줄. 하나도 없으면 `False`.

    "없다"와 "있는데 줄번호를 모른다"를 갈라야 해서 `None`을 쓸 수 없다 —
    `None`을 '없음'으로 쓰면 줄번호 없는 트리(픽스처)에서 검사가 통째로 침묵한다.
    """
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if fcp.strip_prefix(el.tag) != element:
            continue
        if el.get(attribute) is not None:
            return getattr(el, "sourceline", None)
    return False
