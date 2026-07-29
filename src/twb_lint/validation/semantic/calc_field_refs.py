"""L-B rule ② [MVP]: 필드 참조 해소.

두 표면을 걷는다 (03 D3.6):

- **수식** `calculation@formula` · `groupfilter@expression` — 규칙 ①과 같은 표면
  (`extractor.formulas_in()`을 공유한다)
- **직접 참조** `format@field` · `filter@column` 등 (`fieldref.REFERENCE_SURFACES`)

두 자리의 **표기가 다르다** — 정규화는 `twb_lint.fieldref`가 한다 (07 G8).

**심각도는 WARNING 고정이다** (03 D3.6.3, v1.7 하향). 정상 파일에도 잔재 dangling이
있다는 것이 실측이다 — 삭제된 계산필드를 가리키는 `format@field` 규칙이 남아 있어도
Tableau는 그 파일을 연다. ERROR로 두면 정상 골든셋 10/10이 게이트에서 막힌다.
ERROR 승격은 라벨링 배치(TODO D1~D4) 이후다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twb_lint import fieldref
from twb_lint.calc.extractor import extract, formulas_in
from twb_lint.models import Finding, Severity, WorkbookModel
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_FINDINGS = 200
"""보고 상한. 넘으면 `note_partial`로 자른 사실을 보고한다 — 조용히 자르면
"이게 전부"로 읽힌다 (02 S5)."""


@dataclass(slots=True)
class _Hit:
    """미해소 참조 1종 (같은 이름은 묶어서 1건으로 낸다)."""

    raw: str
    location: str
    line: int | None
    count: int = 1
    reason: str = "dangling"


@register
class CalcFieldRefsRule(RuleBase):
    id = "calc.field_refs"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 참조 해소를 하지 못했다")
            return []
        if not ctx.model.datasources:
            # 대조할 집합이 없으면 전부 dangling이 된다 — 검사하지 않았다고 말한다.
            ctx.note_skip(self.id, "데이터소스가 없어 대조할 필드 집합이 없다")
            return []

        universe = _universe(ctx.model)
        hits: dict[tuple[str, str], _Hit] = {}
        for el, refs in self._walk(ctx.raw_tree):
            for ref in refs:
                self._judge(ref, el, ctx.model, universe, hits)

        ordered = sorted(hits.values(), key=lambda h: (h.location, h.raw))
        if len(ordered) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"미해소 참조 {len(ordered)}종 중 앞 {MAX_FINDINGS}종만 보고한다",
                scope="field-refs",
            )
            ordered = ordered[:MAX_FINDINGS]

        return [
            Finding(
                severity=Severity.WARNING,
                rule_id=self.id,
                location=hit.location,
                message=_message(hit),
                fix=(
                    "필드가 삭제·개명됐다면 참조를 고치거나 남은 설정을 지운다. "
                    "정상 파일에도 잔재 참조가 남아 있는 경우가 있다 (03 D3.6.3)."
                ),
                line=hit.line,
            )
            for hit in ordered
        ]

    def _walk(self, root: Any) -> Any:
        """검사 대상 `(요소, 참조들)`을 낸다. 표면은 데이터로만 정한다."""
        for el, formula in formulas_in(root):
            yield el, [r for raw in sorted(extract(formula).field_refs)
                       for r in fieldref.find_all(raw)]
        for tag, attr in fieldref.REFERENCE_SURFACES:
            for el in root.iter(tag):
                value = el.get(attr)
                if value and "[" in value:
                    yield el, fieldref.find_all(value)

    def _judge(
        self,
        ref: fieldref.FieldRef,
        el: Any,
        model: WorkbookModel,
        universe: set[str],
        hits: dict[tuple[str, str], _Hit],
    ) -> None:
        if ref.special is not None:
            return
        if ref.datasource is not None and ref.datasource not in model.datasources:
            reason = "unknown-datasource"
            known: set[str] = set()
        elif ref.datasource is not None:
            reason = "dangling"
            known = model.field_names(ref.datasource)
        else:
            # 자격 없는 참조는 **전체 집합**과 대조한다. 소속 데이터소스를 항상
            # 특정할 수 없고(워크시트 안 수식 등), 좁히면 거짓 dangling이 난다.
            # 대가는 동명 필드가 있을 때의 거짓음성이다 — AC7이 앞선다 (07 G5).
            reason = "dangling"
            known = universe
        if reason == "dangling" and any(name in known for name in ref.names):
            return

        key = (ref.datasource or "", ref.names[0])
        hit = hits.get(key)
        if hit is None:
            hits[key] = _Hit(
                raw=ref.raw, location=_path_of(el), line=el.sourceline, reason=reason
            )
        else:
            hit.count += 1


def _universe(model: WorkbookModel) -> set[str]:
    """모든 데이터소스의 필드 이름 합집합."""
    return {name for ds in model.datasources.values() for name in ds.fields}


def _message(hit: _Hit) -> str:
    where = f" (참조 {hit.count}곳)" if hit.count > 1 else ""
    if hit.reason == "unknown-datasource":
        return f"`{hit.raw}`의 데이터소스가 워크북에 없다{where}"
    return f"`{hit.raw}`가 가리키는 필드를 찾지 못했다{where}"


def _path_of(el: Any) -> str:
    """요소의 xpath. L-A finding의 `location`과 같은 표기를 쓴다."""
    return str(el.getroottree().getpath(el))
