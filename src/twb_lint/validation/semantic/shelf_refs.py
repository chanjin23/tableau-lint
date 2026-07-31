"""L-B rule ⑪: 선반 배치 참조 무결성 (T4-a).

사용자가 **페이지·필터·마크·열·행**에 올린 것이 실재하는 필드인가를 본다
(`docs/01-problem-definition.md` §4 T4-a). 참조가 끊기면 파일은 열리되 그 필드가
워크시트에서 제거되거나 빨갛게 뜬다 — 층 2·4다.

**규칙 ②와 자리가 다르다.** ②는 `fieldref.REFERENCE_SURFACES` 9자리만 본다.
선반은 그 목록 **밖**에 있었다 — 마크 인코딩의 `color`·`size`·`tooltip`, 열·행의
**요소 텍스트**, 필터의 `<slices>/<column>`, 정렬·축 계열이 전부 무주공산이었다.

실측(2026-07-31, 실파일 84개 전수. 규칙 ②가 이미 보는 자리는 뺐다):

| 표면 | 해소 : 미해소 |
|---|---|
| `<slices>/<column>` (필터 선반) | 2,462 : 0 |
| `groupfilter@level` (필터) | 2,553 : 0 |
| `<cols>` (열 선반, 텍스트) | 445 : **10** |
| `<rows>` (행 선반, 텍스트) | 445 : **6** |
| `tooltip@column` · `color@column` · `size@column` (마크) | 871 : 0 |
| `computed-sort`·`manual-sort`·`sort`·`alphabetic-sort`·`shelf-sort-v2` | 429 : 0 |
| `pane@x-axis-name` · `@y-axis-name` (축) | 140 : **12** |
| `reference-line`·`label-data`·`order`·`table-calc@ordering-field` | 17 : 0 |
| `<pages>/<column>` (페이지 선반) | **실측 0회** — ↓ |

**WARNING이다** (02 S1-6). 반례 28건이 전부 골든셋 파일 하나(`태블로판차분석`)에서
나왔고, 그 파일은 정상적으로 열린다 — `Calculation_0630847643873281`·
`Calculation_2012107314806786`을 열·행·축이 가리키는데 데이터소스 어디에도 없다.
규칙 ②가 아는 **잔재 dangling과 같은 계열**이다. ERROR로 두면 AC7이 즉시 깨진다.

**`<pages>`는 실측이 0회다.** 그래도 넣는 근거는 추측이 아니라 **공식 XSD**다 —
`<pages>`의 내용 모델이 `<column>` 자식 목록이고 타입이 `QualifiedName-ST`로,
실측 2,462:0인 `<slices>/<column>`과 **같은 구조**다 (`twb_2026.1.0.xsd:5497`).

**여기서 보지 않는 것**:

- `<dictionary>/<bucket>` — 그룹·집합의 **값** 목록이지 선반이 아니다 (반례 172건)
- `<formatted-text>/<run>` — 텍스트 서식의 **본문**이다. 선반이 아니고,
  타사 생성 워크북의 `{%%KPI…}` 이름 34건이 전부 반례로 나온다
- `<datasource-dependencies>` 하위 — 워크시트가 쓰는 필드 **정의의 사본**이다
- 규칙 ②가 이미 보는 9자리 — 같은 결함을 두 규칙이 두 번 말하지 않는다
- **어떤 필드를 어떤 선반에 놓으면 오류인가**(T4-b) — 정답지가 없다 (01 §7 · `TODO.md` L1)
"""

from __future__ import annotations

from typing import Any

from twb_lint import fieldref
from twb_lint.models import Finding, Severity, WorkbookModel
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_FINDINGS = 100
"""합친 뒤에도 이만큼을 넘으면 자르고 그 사실을 보고한다."""

SKIP_SUBTREES = frozenset({"datasource-dependencies", "dictionary", "formatted-text"})
"""워크시트 안이지만 선반이 아닌 가지. 통째로 건너뛴다 (위 docstring 참조)."""

ATTR_SURFACES: dict[tuple[str, str], str] = {
    ("color", "column"): "마크(색상)",
    ("size", "column"): "마크(크기)",
    ("shape", "column"): "마크(모양)",
    ("detail", "column"): "마크(세부 정보)",
    ("label", "column"): "마크(레이블)",
    ("path", "column"): "마크(경로)",
    ("tooltip", "column"): "마크(도구 설명)",
    ("groupfilter", "level"): "필터",
    ("manual-sort", "column"): "정렬(수동)",
    ("computed-sort", "column"): "정렬(계산됨)",
    ("sort", "column"): "정렬",
    ("alphabetic-sort", "column"): "정렬(사전순)",
    ("shelf-sort-v2", "dimension-to-sort"): "정렬(선반)",
    ("shelf-sort-v2", "measure-to-sort-by"): "정렬(선반 기준)",
    ("pane", "x-axis-name"): "X축",
    ("pane", "y-axis-name"): "Y축",
    ("reference-line", "axis-column"): "참조선(축)",
    ("reference-line", "value-column"): "참조선(값)",
    ("label-data", "column"): "레이블",
    ("order", "field"): "테이블 계산(순서)",
    ("table-calc", "ordering-field"): "테이블 계산(정렬 필드)",
}
"""`(요소, 속성) → 사람이 읽는 선반 이름`. 실측에 나온 자리 + 마크 인코딩 동계열.

⚠️ 마크 인코딩 중 `text`·`lod`는 **일부러 빠졌다** — 규칙 ②가 이미 본다.
`<encodings>`의 자식을 통째로 훑지 않고 목록으로 두는 이유는, 새 인코딩 요소가
참조가 아닌 값을 담을 때 그 자리가 통째로 거짓 dangling이 되기 때문이다 (07 G-계열)."""

TEXT_SURFACES: dict[tuple[str, str], str] = {
    ("table", "rows"): "행 선반",
    ("table", "cols"): "열 선반",
    ("slices", "column"): "필터 선반",
    ("pages", "column"): "페이지 선반",
}
"""`(부모, 요소) → 선반 이름`. 값이 **요소 텍스트**에 실리는 자리다.

`rows`/`cols`는 수식일 수 있다 (`([a] / [b])`) → 참조를 **전부** 뽑는다.
`slices`/`pages`의 `<column>`은 참조 하나짜리 `QualifiedName-ST`다."""


@register
class ShelfRefsRule(RuleBase):
    id = "shelf.refs"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 선반 배치를 검사하지 못했다")
            return []

        worksheets = list(ctx.raw_tree.iter("worksheet"))
        if not worksheets:
            ctx.note_skip(self.id, "워크시트가 없어 검사할 선반이 없다")
            return []

        pool = _field_pool(ctx.model)
        if not pool:
            # 필드를 하나도 못 모았으면 전 참조가 dangling으로 보인다. 보고할 것은
            # 위반이 아니라 **대조할 수 없었다**는 사실이다 (02 S5).
            ctx.note_skip(self.id, "데이터소스 필드를 모으지 못해 선반 참조를 대조하지 못했다")
            return []

        seen: dict[tuple[str, str], _Broken] = {}
        unresolved = 0
        for worksheet in worksheets:
            sheet = worksheet.get("name") or "(이름 없음)"
            for shelf, raw, element in _placements(worksheet):
                for ref in _refs_in(shelf, raw):
                    if ref.special:
                        continue
                    if any(name in pool for name in ref.names):
                        continue
                    unresolved += 1
                    key = (shelf, ref.raw)
                    if key in seen:
                        seen[key].count += 1
                    else:
                        seen[key] = _Broken(shelf, ref.raw, sheet, element.sourceline)

        broken = sorted(seen.values(), key=lambda b: (b.shelf, b.value))
        if len(broken) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"끊긴 배치가 {len(broken)}종이라 앞 {MAX_FINDINGS}종만 보고했다",
                scope="worksheets",
            )
            broken = broken[:MAX_FINDINGS]
        return [b.to_finding(self.id) for b in broken]


class _Broken:
    """끊긴 배치 1종. 같은 (선반, 참조)는 몇 번 나와도 하나로 센다."""

    __slots__ = ("count", "line", "shelf", "sheet", "value")

    def __init__(self, shelf: str, value: str, sheet: str, line: int | None) -> None:
        self.shelf = shelf
        self.value = value
        self.sheet = sheet
        self.line = line
        self.count = 1

    def to_finding(self, rule_id: str) -> Finding:
        more = "" if self.count == 1 else f" (같은 값이 {self.count}곳)"
        return Finding(
            severity=Severity.WARNING,
            rule_id=rule_id,
            location=f"worksheet '{self.sheet}' / {self.shelf}",
            line=self.line,
            message=(
                f"{self.shelf}에 올린 `{self.value}`가 데이터소스에 없다{more} "
                "— 파일은 열리되 그 필드가 워크시트에서 제거되거나 오류 상태로 뜬다"
            ),
            fix=(
                "이름이 바뀐 필드면 현재 이름으로 고치고, 지워진 필드면 선반에서 뺀다. "
                "내부 이름은 `twb_inspect`의 `fields`로 확인한다."
            ),
        )


def _field_pool(model: WorkbookModel) -> set[str]:
    """대조 대상 — 전 데이터소스 필드의 합집합.

    데이터소스별로 좁히지 않는다. 참조의 `[ds]` 자격이 실제 소속과 어긋나는 자리가
    있어(07 G5) 좁히면 거짓 dangling이 난다. 대가는 거짓음성이고, AC7이 먼저다.
    """
    return {name for ds in model.datasources.values() for name in ds.fields}


def _placements(worksheet: Any) -> list[tuple[str, str, Any]]:
    """워크시트 하나가 선반에 올린 것 전부 — `(선반 이름, 원문, 요소)`."""
    out: list[tuple[str, str, Any]] = []
    for element in worksheet.iter():
        tag = str(element.tag)
        if tag in SKIP_SUBTREES:
            continue
        if _under_skipped_subtree(element, worksheet):
            continue

        for (etag, attr), shelf in ATTR_SURFACES.items():
            if tag != etag:
                continue
            value = element.get(attr)
            if value:
                out.append((shelf, value, element))

        parent = element.getparent()
        ptag = "" if parent is None else str(parent.tag)
        shelf = TEXT_SURFACES.get((ptag, tag))
        if shelf is not None:
            text = (element.text or "").strip()
            if text:
                out.append((shelf, text, element))
    return out


def _under_skipped_subtree(element: Any, stop: Any) -> bool:
    """`<datasource-dependencies>` 등의 하위인가. 워크시트 루트까지만 거슬러 본다."""
    node = element.getparent()
    while node is not None and node is not stop:
        if str(node.tag) in SKIP_SUBTREES:
            return True
        node = node.getparent()
    return False


def _refs_in(shelf: str, raw: str) -> list[fieldref.FieldRef]:
    """선반에 실린 원문에서 필드 참조를 뽑는다.

    행·열은 수식일 수 있어 **전부** 뽑고, 나머지는 값 하나로 읽는다. 값 하나짜리
    자리를 `find_all`로 훑으면 따옴표·괄호 안의 조각까지 참조로 읽힌다.
    """
    if shelf in ("행 선반", "열 선반"):
        return fieldref.find_all(raw)
    ref = fieldref.parse(raw.strip().strip('"'))
    return [] if ref is None else [ref]
