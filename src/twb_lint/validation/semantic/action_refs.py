"""L-B rule ⑩: 동작(`<actions>`) 참조 무결성.

동작은 **시트·필드·매개변수·집합을 이름으로 배선한다.** 배선이 끊기면 그 동작이
아무 일도 하지 않거나 대상 필드가 오류 상태가 된다 — 파일은 열리므로 층 2~4다
(01 v2.0 §3).

**XSD는 이걸 원리적으로 못 잡는다.** 배선의 절반이 `<param name= value= />`에 실리는데
XSD에서 이 둘은 **임의 문자열 쌍**이다. 없는 `target-parameter`를 넣어도 L-A는 통과한다
(06 R14 · README "한계").

실측(2026-07-31, 실파일 84개 중 `<actions>` 보유 33개)으로 표면과 해소율을 확정했다:

| 표면 | 대조 대상 | 해소 : 미해소 |
|---|---|---|
| `source@worksheet` | 워크시트 | 81 : 0 |
| `source@dashboard` | 대시보드 | 153 : 0 |
| `source@datasource` | 데이터소스(이름 ∪ caption) | 4 : 0 |
| `exclude-sheet@name` | 시트 ∪ 대시보드 | 3,016 : 0 |
| `param exclude` (콤마 목록) | 시트 ∪ 대시보드 | 979 : 0 |
| `param target` | 시트 ∪ 대시보드 | 30 : 0 |
| `param target-group` | 집합 이름 ∪ 필드 | 46 : 0 |
| `param target-parameter` 한정자 | `[Parameters].` | 83 : 0 |
| `param target-parameter` 대상 | Parameters의 필드 | 77 : **6** |
| `param source-field` | 전 데이터소스 필드 | 75 : **4** |

**전부 WARNING이다** (02 S1-6). 규칙 ③(`named.refs`)이 ERROR인 것과 대비된다 —
저쪽은 *viewpoint 누락 = 내부 오류 2805CF18*이라는 **로드 거부 실측**이 있었다.
동작 배선이 끊긴 파일이 열리지 않는다는 근거는 우리에게 없고, 뒤 두 줄의 반례가
그 반대를 시사한다. 승격은 라벨 확보 후다 (`TODO.md` L2).

반례 10건의 정체 (실측으로 확인):

- `target-parameter` 6건 — `[Parameters].[ColorStart]`인데 그 파일의 `Parameters`에는
  `매개 변수 1~6`뿐이다. **진짜 dangling**이고, 그 파일은 골든셋 밖(`old/`)이다
- `source-field` 4건 — 가리키는 이름이 `groupfilter@level`에만 있고 `<column>`·
  `<column-instance>` 어디에도 없다. 규칙 ②가 아는 **잔재 dangling과 같은 계열**이며
  골든셋 파일 1개가 여기 포함된다. 그래서 이 표면은 ERROR가 될 수 없다

**같은 결함을 여러 번 말하지 않는다.** `exclude-sheet`는 파일 하나에 수백 번 나온다
(실측 3,016회/33파일) — 시트 하나가 없으면 그 수만큼 finding이 난다. 표면·값으로
합치고 등장 횟수를 메시지에 적는다.
"""

from __future__ import annotations

from typing import Any

from twb_lint import fieldref
from twb_lint.models import Finding, Severity, WorkbookModel
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

PARAMETERS_DS = "Parameters"
"""매개변수를 담는 고정 데이터소스 이름. 규칙 ⑦-c와 같은 전제다 (05 F5-d)."""

CONTAINER_TAGS = frozenset({"datasources", "datasource-dependencies"})
"""`<actions>`의 자식이지만 동작이 아니다 — 동작이 참조하는 필드 정의의 사본이다."""

MAX_FINDINGS = 100
"""합친 뒤에도 이만큼을 넘으면 자르고 그 사실을 보고한다."""


@register
class ActionRefsRule(RuleBase):
    id = "action.refs"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 동작 배선을 검사하지 못했다")
            return []

        actions = [
            el
            for container in ctx.raw_tree.iter("actions")
            for el in container
            if str(el.tag) not in CONTAINER_TAGS
        ]
        if not actions:
            ctx.note_skip(self.id, "동작(`<actions>`)이 없어 검사할 것이 없다")
            return []

        pools = _Pools.of(ctx.model, ctx.raw_tree)
        seen: dict[tuple[str, str], _Broken] = {}
        for action in actions:
            for surface, value, hit in _references(action, pools):
                if hit:
                    continue
                key = (surface, value)
                if key in seen:
                    seen[key].count += 1
                else:
                    seen[key] = _Broken(
                        surface=surface,
                        value=value,
                        where=_label(action),
                        line=action.sourceline,
                    )

        broken = sorted(seen.values(), key=lambda b: (b.surface, b.value))
        if len(broken) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"끊긴 배선이 {len(broken)}종이라 앞 {MAX_FINDINGS}종만 보고했다",
                scope="actions",
            )
            broken = broken[:MAX_FINDINGS]
        return [b.to_finding(self.id) for b in broken]


class _Broken:
    """끊긴 배선 1종. 같은 (표면, 값)은 몇 번 나와도 하나로 센다."""

    __slots__ = ("count", "line", "surface", "value", "where")

    def __init__(self, surface: str, value: str, where: str, line: int | None) -> None:
        self.surface = surface
        self.value = value
        self.where = where
        self.line = line
        self.count = 1

    def to_finding(self, rule_id: str) -> Finding:
        spec = _SURFACES[self.surface]
        more = "" if self.count == 1 else f" (같은 값이 {self.count}곳)"
        return Finding(
            severity=Severity.WARNING,
            rule_id=rule_id,
            location=f"actions/{self.where}",
            line=self.line,
            message=(
                f"동작이 가리키는 {spec.noun} `{self.value}`가 없다 "
                f"[{self.surface}]{more} — {spec.symptom}"
            ),
            fix=spec.fix,
        )


class _Spec:
    """표면 하나가 사람에게 어떻게 읽히는가."""

    __slots__ = ("fix", "noun", "symptom")

    def __init__(self, noun: str, symptom: str, fix: str) -> None:
        self.noun = noun
        self.symptom = symptom
        self.fix = fix


_SHEET_FIX = "동작을 지우거나, 이름이 바뀐 시트를 현재 이름으로 고친다."

_SURFACES = {
    "source@worksheet": _Spec(
        "원본 워크시트", "그 동작이 발동하지 않는다", _SHEET_FIX
    ),
    "source@dashboard": _Spec("원본 대시보드", "그 동작이 발동하지 않는다", _SHEET_FIX),
    "source@datasource": _Spec(
        "원본 데이터소스",
        "그 동작이 발동하지 않는다",
        "`<source datasource=…>`를 실제 데이터소스 이름으로 고친다.",
    ),
    "exclude-sheet@name": _Spec(
        "제외 대상 시트", "제외 설정이 무시된다", _SHEET_FIX
    ),
    "param exclude": _Spec("제외 대상 시트", "제외 설정이 무시된다", _SHEET_FIX),
    "param target": _Spec("대상 시트", "동작이 갈 곳을 잃는다", _SHEET_FIX),
    "param target-parameter": _Spec(
        "대상 매개변수",
        "매개변수 동작이 아무 값도 바꾸지 못한다",
        "`<param name='target-parameter'>`의 값을 실재하는 매개변수로 고친다.",
    ),
    "param target-parameter 한정자": _Spec(
        "매개변수 한정자",
        f"매개변수는 항상 `[{PARAMETERS_DS}].[이름]`으로 적는다 (실측 83:0)",
        f"값을 `[{PARAMETERS_DS}].[매개변수 이름]` 형태로 고친다.",
    ),
    "param target-group": _Spec(
        "대상 집합",
        "집합 동작이 집합을 갱신하지 못하고, 그 집합을 쓰는 계산이 깨진다",
        "`<param name='target-group'>`의 값을 실재하는 `<group>`으로 고친다.",
    ),
    "param source-field": _Spec(
        "원본 필드",
        "동작이 넘길 값을 못 찾는다",
        "`<param name='source-field'>`의 값을 실재하는 필드로 고친다.",
    ),
}

_PARAM_FIELD_SURFACES = frozenset({"target-parameter", "target-group", "source-field"})


class _Pools:
    """대조 대상 집합들. 파일당 한 번만 만든다."""

    __slots__ = ("datasources", "fields", "groups", "parameters", "places")

    def __init__(
        self,
        places: set[str],
        datasources: set[str],
        fields: set[str],
        parameters: set[str],
        groups: set[str],
    ) -> None:
        self.places = places
        self.datasources = datasources
        self.fields = fields
        self.parameters = parameters
        self.groups = groups

    @classmethod
    def of(cls, model: WorkbookModel, tree: Any) -> _Pools:
        params = model.datasources.get(PARAMETERS_DS)
        fields = {name for ds in model.datasources.values() for name in ds.fields}
        return cls(
            places=set(model.worksheets) | set(model.dashboards),
            datasources=set(model.datasources)
            | {ds.caption for ds in model.datasources.values() if ds.caption},
            fields=fields,
            parameters=set() if params is None else set(params.fields),
            # 집합 이름은 `<group name='[X 집합]'>`이라 대괄호가 붙어 있다. 필드 풀에도
            # 들어 있지만(인스펙터가 group을 걷는다) 여기서 따로 모아 두면 집합이
            # 아예 없는 파일과 이름만 틀린 경우를 같은 코드로 다룰 수 있다.
            groups={_unbracket(g.get("name")) for g in tree.iter("group") if g.get("name")},
        )


def _references(action: Any, pools: _Pools) -> list[tuple[str, str, bool]]:
    """동작 하나가 거는 배선 전부 — `(표면, 값, 해소됐는가)`."""
    out: list[tuple[str, str, bool]] = []

    for source in action.iter("source"):
        for attr, pool in (
            ("worksheet", pools.places),
            ("dashboard", pools.places),
            ("datasource", pools.datasources),
        ):
            value = source.get(attr)
            if value is not None:
                out.append((f"source@{attr}", value, value in pool))

    for exclude in action.iter("exclude-sheet"):
        name = exclude.get("name")
        if name is not None:
            out.append(("exclude-sheet@name", name, name in pools.places))

    for param in action.iter("param"):
        out += _param_references(param, pools)
    return out


def _param_references(param: Any, pools: _Pools) -> list[tuple[str, str, bool]]:
    name, value = param.get("name"), param.get("value")
    if not name or value is None:
        return []

    if name == "target":
        return [("param target", value, value in pools.places)]
    if name == "exclude":
        return [("param exclude", part, part in pools.places) for part in _sheet_list(value, pools)]
    if name not in _PARAM_FIELD_SURFACES:
        return []

    ref = fieldref.parse(value)
    if ref is None:
        # 필드 참조 표기가 아니면 대조 자체가 성립하지 않는다. 추측해서 dangling으로
        # 읽으면 그 자리가 통째로 거짓양성이 된다 (02 S1-6).
        return []

    out: list[tuple[str, str, bool]] = []
    if name == "target-parameter":
        out.append(
            ("param target-parameter 한정자", value, ref.datasource == PARAMETERS_DS)
        )
        pool = pools.parameters
    elif name == "target-group":
        pool = pools.groups | pools.fields
    else:
        pool = pools.fields
    out.append((f"param {name}", value, any(n in pool for n in ref.names)))
    return out


def _sheet_list(value: str, pools: _Pools) -> list[str]:
    """콤마로 이어붙인 시트 목록을 쪼갠다.

    **통째로 해소되면 쪼개지 않는다.** 시트 이름에 콤마를 넣는 것이 금지돼 있지 않기
    때문이다 — 실측 1,460개 이름에 콤마가 하나도 없었지만(실측 979:0), 있는 순간
    쪼개기가 존재하지 않는 이름 두 개를 만들어 낸다.
    """
    if value in pools.places:
        return [value]
    return [part for part in value.split(",") if part]


def _label(action: Any) -> str:
    name = action.get("caption") or action.get("name") or str(action.tag)
    return str(name).strip("[]")


def _unbracket(name: str | None) -> str:
    return "" if name is None else fieldref.unescape(name).strip("[]")
