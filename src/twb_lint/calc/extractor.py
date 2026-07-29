"""calc 수식에서 함수 호출·필드 참조를 추출한다.

규칙 ①(함수 화이트리스트)·②(필드참조 해소)가 소비한다. 수집 표면은
`docs/03-design.md` D3.6에 실측으로 확정돼 있다.

**문법 파서가 아니라 어휘 스캐너다** (D3.7). Tableau calc 언어의 전체 문법을 세우면
지원하지 못한 구문마다 파싱 실패 WARNING이 나는데, 규칙 ①②가 필요로 하는 것은
"함수 이름"과 "필드 참조" 두 종류의 토큰뿐이다. 스캐너는 **실패하지 않으므로**
그 노이즈 클래스 자체가 없다.

실측 근거 (표본 10개, 수식 5,270건 = `calculation@formula` + `groupfilter@expression`):
함수 26종이 나왔고 **218종 화이트리스트 미매칭 0건**이다. 즉 이 스캐너로 규칙 ①이
정상본에서 침묵한다 (AC7).

XML 엔티티(`&apos;`·`&#13;&#10;`)는 여기 오기 전에 풀린다 — lxml이 속성값을 읽을 때
디코드하므로 수식 문자열에는 이미 실제 따옴표·개행이 들어 있다.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

FORMULA_SURFACES = (("calculation", "formula"), ("groupfilter", "expression"))
"""수식이 들어 있는 요소·속성 (03 D3.6 실측, 표본 9개 4,757 + 3회).

**데이터로 갖는다.** 목록 밖 요소는 침묵한다 — 표본에 `<reference-line>`이 없었다고
"안 나온다"는 뜻은 아니지만, 추측해서 검사하지는 않는다."""

_TOKEN = re.compile(
    # 순서가 곧 우선순위다. 주석·문자열을 **먼저** 먹어야 그 안의 `[...]`나 함수처럼
    # 생긴 글자가 참조로 새지 않는다.
    r"(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)"
    r"|(?P<string>'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")"
    # `]]`는 `]`의 이스케이프다 — 이름에 대괄호가 들어가면 이렇게 적힌다
    # (`[[P_Year]](복사본)_2403…]`). `[^\]]*`로 자르면 여기서 잘못 끊긴다 (fieldref 참조).
    r"|(?P<bracket>\[(?:[^\]]|\]\])*\](?:\.\[(?:[^\]]|\]\])*\])*)"
    r"|(?P<func>[A-Za-z_][A-Za-z0-9_]*)(?=\s*\()"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)

KEYWORDS = frozenset(
    {
        "IF",
        "THEN",
        "ELSE",
        "ELSEIF",
        "END",
        "CASE",
        "WHEN",
        "AND",
        "OR",
        "NOT",
        "IN",
        "FIXED",
        "INCLUDE",
        "EXCLUDE",
        "TRUE",
        "FALSE",
        "NULL",
    }
)
"""함수처럼 `(`가 뒤따를 수 있는 **언어 키워드**. 함수 호출로 세지 않는다.

`IF (x > 1) THEN …`의 `IF`를 함수로 세면 화이트리스트에 없어 WARNING이 난다.
이 목록이 넓으면 **미지 함수를 놓칠 뿐**(거짓음성)이고, 좁으면 정상 수식에서
경고가 난다(거짓양성). AC7이 우선이라 넓은 쪽으로 잡았다 (02 S1-6)."""


@dataclass(slots=True)
class CalcRefs:
    """한 calc 수식에서 뽑아낸 참조들."""

    functions: set[str] = field(default_factory=set)
    """호출된 함수명 (대문자 정규화 — Tableau 함수는 대소문자를 가리지 않는다)."""

    field_refs: set[str] = field(default_factory=set)
    """참조된 필드명. 원문 표기 그대로 (`[Field]` 또는 `[ds].[Field]`).

    **정규화하지 않는다** — 워크시트 속성 표기(`[ds].[usr:name:qk]`)와 맞추는 일은
    규칙 ②의 몫이고, 여기서 미리 벗기면 어느 쪽 표기였는지가 사라진다 (07 G8)."""


def formulas_in(root: Any) -> Iterator[tuple[Any, str]]:
    """트리에서 수식을 전부 걷는다 — `(요소, 수식)`.

    규칙 ①②가 **같은 표면**을 봐야 한다. 한쪽만 `groupfilter@expression`을 빠뜨리면
    두 규칙의 커버리지가 조용히 달라진다.
    """
    for tag, attr in FORMULA_SURFACES:
        for el in root.iter(tag):
            value = el.get(attr)
            if value:
                yield el, value


def extract(formula: str) -> CalcRefs:
    """calc 수식 문자열에서 함수·필드 참조를 추출한다.

    예외를 던지지 않는다 — 어떤 문자열이 와도 결과가 나온다. 닫히지 않은 `[`는
    참조로 잡히지 않는데, Tableau가 그런 수식을 저장하지 못하므로 실사용에서는
    나타나지 않는다.
    """
    refs = CalcRefs()
    for m in _TOKEN.finditer(formula):
        kind = m.lastgroup
        if kind == "bracket":
            refs.field_refs.add(m.group())
        elif kind == "func":
            name = m.group().upper()
            if name not in KEYWORDS:
                refs.functions.add(name)
    return refs
