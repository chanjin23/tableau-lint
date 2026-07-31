"""L-B rule ⑬: 동작(`<actions>`)의 **모양**.

규칙 ⑩ `action.refs`와 묻는 것이 다르다. ⑩은 *"가리키는 시트·매개변수·집합·필드가
실재하는가"*를 본다 — **참조**다. 여기는 *"Tableau가 아는 배선 모양인가"*를 본다 —
**어휘**다. 가리키는 대상이 전부 실재해도 명령 이름이 틀리면 동작은 죽는다.

2026-07-31 저작본이 이걸 실증했다 (05 F5-g). `tsc:filter` + `source-field` param으로
동작을 짰더니 **파일은 열리고 ⑩도 침묵하는데** 동작 대화상자의 필드 열이 비고 편집
버튼이 죽었다. 층 2다 (01 v2.0 §3) — 열리지만 설정이 버려진다.

**XSD는 이걸 원리적으로 못 잡는다.** `ActionList-CommandName-ST`가
`<xs:pattern value="[^:]+:[^:]+"/>`일 뿐 열거가 아니고, `<param name= value= />`는
임의 문자열 쌍이다. `tsc:filter`도 `tsc:아무거나`도 L-A를 통과한다.

## 실측 (2026-07-31, 실파일 63개 · 동작 140건)

`<action>`은 **세 모양뿐이다.** 셋 다 명령과 `<link>`가 짝을 이룬다:

| 모양 | 명령 | `<link>` | 건수 |
|---|---|---|---|
| 필터 | `tsc:tsl-filter` | 있다 — `expression='tsl:…'`에 필드 매핑이 실린다 | **14 : 0** |
| 하이라이트 | `tsc:brush` | 없다 | **17 : 0** |
| URL | 없다 | 있다 — `expression='http…'` | **1** |

param 이름은 동작 종류마다 어휘가 갈린다. 교차 0건:

| 종류 | 관측된 param 이름 |
|---|---|
| `action` / `tsc:tsl-filter` | `target` 14 · `exclude` 14 |
| `action` / `tsc:brush` | `target` 17 · `exclude` 16 · `field-captions` 16 · `special-fields` 1 |
| `edit-parameter-action` | `target-parameter` 75 · `source-field` 70 |
| `edit-group-action` | `selection-clear-set-option` 47 · `target-group` 47 |

`source-field`가 **없는 이름이 아니라 자리가 틀린 이름**이라는 게 요점이다. 전역
화이트리스트로는 못 잡는다 — 종류별로 갈라야 저작본의 결함이 걸린다.

## 왜 WARNING인가

**우리 목록이 불완전할 수 있다.** 표본에 없는 명령이 Tableau에는 있을 수 있고
(`nav-action`은 실파일 0건이라 어휘 자체를 모른다), 릴리스가 늘리면 목록이 뒤처진다.
규칙 ①(`calc.functions`)과 같은 구조다 — 목록 밖은 *틀렸다*가 아니라 *모른다*이므로
ERROR가 될 수 없다 (02 S1-6). 그리고 층 2라 파일은 열린다: `tsc:filter`를 넣은
저작본을 Tableau가 **경고 없이** 열었다.

어휘를 모르는 종류는 **판정하지 않고 말한다** — `note_partial`.
"""

from __future__ import annotations

from typing import Any

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

CONTAINER_TAGS = frozenset({"datasources", "datasource-dependencies"})
"""`<actions>`의 자식이지만 동작이 아니다 — 동작이 참조하는 필드 정의의 사본이다."""

LEGACY_TAG = "action"
"""필터·하이라이트·URL 세 종류를 겸하는 요소. 명령으로 갈린다."""

COMMANDS = {"tsc:tsl-filter": 14, "tsc:brush": 17}
"""관측된 `<command @command>` 값과 실측 건수. 목록 밖은 WARNING이다."""

LINK_REQUIRED = frozenset({"tsc:tsl-filter"})
"""`<link>` 없이는 필드 매핑이 없어 아무것도 거르지 못하는 명령 (실측 14:0)."""

PARAM_VOCAB: dict[tuple[str, str | None], frozenset[str]] = {
    (LEGACY_TAG, "tsc:tsl-filter"): frozenset({"target", "exclude"}),
    (LEGACY_TAG, "tsc:brush"): frozenset(
        {"target", "exclude", "field-captions", "special-fields"}
    ),
    ("edit-parameter-action", None): frozenset({"target-parameter", "source-field"}),
    ("edit-group-action", None): frozenset(
        {"selection-clear-set-option", "target-group"}
    ),
}
"""(동작 종류, 명령) → 관측된 param 이름. 명령을 안 쓰는 종류는 `None`으로 건다."""

MAX_FINDINGS = 50
"""합친 뒤에도 이만큼을 넘으면 자르고 그 사실을 보고한다."""


@register
class ActionShapeRule(RuleBase):
    id = "action.shape"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 동작 모양을 검사하지 못했다")
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

        seen: dict[tuple[str, str], _Odd] = {}
        unknown_kinds: set[str] = set()
        for action in actions:
            kind = str(action.tag)
            command = _command_of(action)
            if kind == LEGACY_TAG:
                _fold(seen, action, _legacy_shape(action, command))
            vocab = PARAM_VOCAB.get((kind, None if kind != LEGACY_TAG else command))
            if vocab is None:
                # 어휘를 모르는 종류·명령이다. 여기서 이름을 판정하면 우리 표본의
                # 공백이 남의 정상 파일을 때린다. 명령 자체는 위에서 이미 말했다.
                if kind != LEGACY_TAG:
                    unknown_kinds.add(kind)
                continue
            _fold(seen, action, _odd_params(action, kind, command, vocab))

        for kind in sorted(unknown_kinds):
            ctx.note_partial(
                self.id,
                f"`<{kind}>`는 실파일 표본이 0건이라 param 어휘를 판정하지 못했다",
                scope="actions",
            )

        odd = sorted(seen.values(), key=lambda o: (o.axis, o.value))
        if len(odd) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"모양이 어긋난 자리가 {len(odd)}종이라 앞 {MAX_FINDINGS}종만 보고했다",
                scope="actions",
            )
            odd = odd[:MAX_FINDINGS]
        return [o.to_finding(self.id) for o in odd]


class _Odd:
    """어긋난 자리 1종. 같은 (축, 값)은 몇 번 나와도 하나로 센다."""

    __slots__ = ("axis", "count", "fix", "line", "message", "value", "where")

    def __init__(
        self, axis: str, value: str, message: str, fix: str, where: str, line: int | None
    ) -> None:
        self.axis = axis
        self.value = value
        self.message = message
        self.fix = fix
        self.where = where
        self.line = line
        self.count = 1

    def to_finding(self, rule_id: str) -> Finding:
        more = "" if self.count == 1 else f" (같은 값이 {self.count}곳)"
        return Finding(
            severity=Severity.WARNING,
            rule_id=rule_id,
            location=f"actions/{self.where}",
            line=self.line,
            message=f"{self.message}{more}",
            fix=self.fix,
        )


def _fold(seen: dict[tuple[str, str], _Odd], action: Any, found: list[_Odd]) -> None:
    for odd in found:
        odd.where = _label(action)
        odd.line = action.sourceline
        key = (odd.axis, odd.value)
        if key in seen:
            seen[key].count += 1
        else:
            seen[key] = odd


def _legacy_shape(action: Any, command: str | None) -> list[_Odd]:
    """`<action>`이 관측된 세 모양 중 하나인가 — 명령과 `<link>`의 짝."""
    has_link = action.find("link") is not None

    if command is None:
        if has_link:
            return []  # URL 동작 — `<link expression='http…'>`만 있다 (실측 1건)
        return [
            _Odd(
                axis="shape",
                value="empty",
                message=(
                    "동작에 `<command>`도 `<link>`도 없다 — **아무 일도 하지 않는다**. "
                    "실파일의 `<action>`은 셋 중 하나다: "
                    "`tsc:tsl-filter`+`<link>`(14) · `tsc:brush`(17) · "
                    "명령 없이 `<link expression='http…'>`(1)"
                ),
                fix=(
                    "필터면 `<command command='tsc:tsl-filter'>`와 `<link expression='tsl:…'>`를, "
                    "하이라이트면 `<command command='tsc:brush'>`를, "
                    "URL이면 `<link expression='http…'>`를 넣는다."
                ),
                where="",
                line=None,
            )
        ]

    if command not in COMMANDS:
        known = " · ".join(f"`{c}`({n}건)" for c, n in COMMANDS.items())
        return [
            _Odd(
                axis="command",
                value=command,
                message=(
                    f"동작 명령 `{command}`가 실측 목록에 없다 — 관측된 것은 {known}뿐이다. "
                    "Tableau가 모르는 명령이면 파일은 열리지만 **동작 대화상자에서 편집이 막히고 "
                    "동작이 발동하지 않는다**"
                ),
                fix=(
                    "필터 동작이면 `tsc:tsl-filter`, 하이라이트면 `tsc:brush`로 고친다. "
                    "URL 동작이면 `<command>` 없이 `<link expression='http…'>`만 둔다. "
                    "정말 쓰이는 명령인데 목록에 없다면 목록을 늘린다."
                ),
                where="",
                line=None,
            )
        ]

    if command in LINK_REQUIRED and not has_link:
        return [
            _Odd(
                axis="link",
                value=command,
                message=(
                    f"필터 동작(`{command}`)에 `<link>`가 없다 — 원본↔대상 **필드 매핑이 "
                    "`<link expression>`에 실린다**. 없으면 동작 대화상자의 필드 열이 비고 "
                    "아무 필터도 걸리지 않는다 (실측 14:0)"
                ),
                fix=(
                    "`<link expression='tsl:&lt;대시보드&gt;?&lt;필드&gt;~s0=…' "
                    "delimiter=',' escape='\\' include-null='true' multi-select='true' "
                    "url-escape='true' />`를 `<command>` 앞에 넣는다. 대시보드·필드 이름은 "
                    "퍼센트 인코딩한다."
                ),
                where="",
                line=None,
            )
        ]
    return []


def _odd_params(
    action: Any, kind: str, command: str | None, vocab: frozenset[str]
) -> list[_Odd]:
    """param 이름이 그 동작 종류의 어휘에 있는가."""
    out: list[_Odd] = []
    where = f"`<{kind}>`" if command is None else f"`<{kind}>`/`{command}`"
    known = " · ".join(f"`{n}`" for n in sorted(vocab))
    for param in action.iter("param"):
        name = param.get("name")
        if name is None or name in vocab:
            continue
        out.append(
            _Odd(
                axis="param",
                value=f"{kind}:{command}:{name}",
                message=(
                    f"{where}에 param `{name}`은 실파일에 없다 — 이 자리의 어휘는 "
                    f"{known}뿐이다. Tableau가 모르는 param은 **조용히 버려진다**"
                ),
                fix=(
                    f"이름을 {known} 중 하나로 고친다. 필터 동작의 필드 매핑은 param이 "
                    "아니라 `<link expression>`에 넣는다."
                ),
                where="",
                line=None,
            )
        )
    return out


def _command_of(action: Any) -> str | None:
    el = action.find("command")
    return None if el is None else el.get("command")


def _label(action: Any) -> str:
    name = action.get("caption") or action.get("name") or str(action.tag)
    return str(name).strip("[]")
