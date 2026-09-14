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
    r"|(?P<punct>[(),{}])"
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


@dataclass(frozen=True, slots=True)
class CalcStructure:
    """한 수식의 **구조 집계** — 규칙 ⑯(`calc.syntax`)이 소비한다.

    D3.7이 예고한 "스캐너 **위에** 얹는다"의 첫 사례다. 구문 트리를 세우지 않는다 —
    짝이 맞는지를 세기만 하므로 스캐너처럼 **실패할 수 없고**, 지원 못 한 구문마다
    파싱 실패가 나는 문법 파서의 노이즈 클래스가 여기에도 없다.

    주석·문자열·필드 참조는 토큰 우선순위에서 먼저 먹히므로 그 **안의** `END`나 `(`는
    세지 않는다 (실측: 정상본 85,316개 수식 위반 0건, 거짓양성 함정 4/4 침묵).
    """

    paren_depth: int
    """끝까지 닫히지 않은 `(`의 수. 0이 정상."""

    paren_underflow: bool
    """여는 것보다 닫는 `)`가 먼저 나온 적이 있는가."""

    brace_depth: int
    """LOD `{}`의 잔여 깊이. 0이 정상."""

    ifs: int
    cases: int
    ends: int
    thens: int
    whens: int
    """언어 키워드 출현 횟수 (대소문자 무시)."""

    @property
    def opens(self) -> int:
        """`END`를 요구하는 블록의 수. `IF`와 `CASE` 둘 다다."""
        return self.ifs + self.cases


def structure(formula: str) -> CalcStructure:
    """수식의 괄호·블록 짝을 센다. 예외를 던지지 않는다 (`extract`와 같은 계약).

    >>> structure("IF [A] > 0 THEN 1 ELSE 0 END").opens
    1
    >>> structure("SUM([매출]) / SUM([수량]").paren_depth
    1
    >>> structure("IF [A] THEN 'END' ELSE 0 END").ends      # 문자열 안은 안 센다
    1
    """
    depth = brace = 0
    underflow = False
    counts: dict[str, int] = {}
    for m in _TOKEN.finditer(formula):
        kind = m.lastgroup
        if kind in ("comment", "string", "bracket"):
            continue
        if kind == "punct":
            token = m.group()
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
                if depth < 0:
                    # 0으로 되돌린다 — 뒤에 진짜로 안 닫힌 괄호가 또 있으면
                    # 그것도 보여야 한다. 음수를 끌고 가면 서로 상쇄된다.
                    underflow, depth = True, 0
            elif token == "{":
                brace += 1
            elif token == "}":
                brace -= 1
            # `,`는 짝을 세는 대상이 아니다 — 여기서 걸러내지 않으면 `}`로 읽힌다
        elif kind in ("func", "name"):
            word = m.group().upper()
            counts[word] = counts.get(word, 0) + 1
    return CalcStructure(
        paren_depth=depth,
        paren_underflow=underflow,
        brace_depth=brace,
        ifs=counts.get("IF", 0),
        cases=counts.get("CASE", 0),
        ends=counts.get("END", 0),
        thens=counts.get("THEN", 0),
        whens=counts.get("WHEN", 0),
    )


@dataclass(frozen=True, slots=True)
class AggregationSplit:
    """수식을 **집계 문맥 기준**으로 가른 결과 — 규칙 ⑧-c가 소비한다.

    Tableau는 한 수식 안에서 집계와 행수준을 섞는 것을 거부한다:

        SUM([매출]) + [수량]                      집계 + 행수준 -> 거부
        IF SUM([A]) > 0 THEN [B] ELSE 0 END      조건은 집계, 분기는 행수준 -> 거부

    가리는 것은 두 가지다. **집계 함수의 인자 안**은 행수준이 정상이고
    (`SUM([A] + [B])`), **LOD 중괄호 안**도 마찬가지다 — LOD 결과는 행수준 값처럼
    쓰이므로 그 안의 집계는 바깥 문맥을 물들이지 않는다 (규칙 ⑧-a와 같은 판단).
    """

    aggregates: tuple[str, ...]
    """가려지지 않은 자리에서 호출된 집계 함수들."""

    bare_refs: tuple[str, ...]
    """가려지지 않은 자리에 **맨몸으로** 나온 필드 참조 (원문 표기)."""


def aggregation_split(
    formula: str,
    aggregates: frozenset[str],
    arity_sensitive: frozenset[str] = frozenset(),
) -> AggregationSplit:
    """수식에서 최상위 집계 호출과 맨 필드 참조를 가른다.

    `aggregates`·`arity_sensitive`를 **인자로 받는다** — 어느 함수가 집계인가는
    calc 언어의 어휘가 아니라 규칙의 정책이고, 스캐너는 정책을 갖지 않는다.

    `arity_sensitive`는 **인자 수로 성격이 갈리는** 함수다. `MIN`/`MAX`가 그렇다 —
    `MIN([A])`는 집계지만 `MIN([A], [B])`는 행수준 함수다 (실측: 1개 4,849 · 2개 49).
    인자 수는 닫는 괄호에서야 알 수 있으므로 판정을 그때까지 미룬다.

    >>> agg = frozenset({"SUM"})
    >>> aggregation_split("SUM([A]) + [B]", agg).bare_refs
    ('[B]',)
    >>> aggregation_split("SUM([A] + [B])", agg).bare_refs
    ()
    """
    tokens = [
        (m.lastgroup, m.group())
        for m in _TOKEN.finditer(formula)
        if m.lastgroup not in ("comment", "string")
    ]
    top_aggs: list[str] = []
    top_refs: list[str] = []
    shielded = 0
    # 프레임: [함수명|None, 최상위 콤마 수, 이 프레임이 가리는가, 모아 둔 참조]
    stack: list[list[Any]] = []

    i = 0
    while i < len(tokens):
        kind, text = tokens[i]
        if kind == "func" and text.upper() not in KEYWORDS:
            name = text.upper()
            deferred = name in arity_sensitive
            shields = name in aggregates and not deferred
            if shields and shielded == 0:
                top_aggs.append(name)
            stack.append([name, 0, shields, []])
            if shields:
                shielded += 1
            i += 2  # 바로 뒤 '('를 프레임으로 다시 세지 않는다
            continue

        if kind == "punct" and text == "(":
            stack.append([None, 0, False, []])
        elif kind == "punct" and text == "{":
            stack.append([None, 0, True, []])
            shielded += 1
        elif kind == "punct" and text in ")}":
            if stack:
                name, commas, shields, buffered = stack.pop()
                if shields:
                    shielded -= 1
                elif name in arity_sensitive and commas == 0 and name in aggregates:
                    # 인자 1개였다 = 집계다. 그 안의 참조는 가려진 것으로 되돌린다.
                    if shielded == 0:
                        top_aggs.append(name)
                    buffered = []
                if buffered:
                    (stack[-1][3] if stack else top_refs).extend(buffered)
        elif kind == "punct" and text == ",":
            if stack:
                stack[-1][1] += 1
        elif kind == "bracket" and shielded == 0:
            (stack[-1][3] if stack else top_refs).append(text)
        i += 1

    return AggregationSplit(aggregates=tuple(top_aggs), bare_refs=tuple(top_refs))
