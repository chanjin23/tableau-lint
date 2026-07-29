"""필드 참조 표기 정규화 — 규칙 ②의 최대 함정을 한 곳에 가둔다 (07 G8 · 03 D3.6).

같은 필드가 자리에 따라 **두 가지 표기**로 적힌다:

```
calc 수식 안       [Calculation_2403322100842499]                 내부 이름 그대로
워크시트 속성      [federated.1wko…].[usr:Calculation_1737…:qk]   역할 접두 + 종류 접미
```

정규화 없이 대조하면 규칙 ②가 **전량 dangling**을 뱉는다. 그래서 대조 전에 반드시
여기를 통과시킨다.

**후보를 여러 개 낸다** (`FieldRef.names`). 접두/접미를 벗기는 규칙이 어긋났을 때
"필드가 없다"고 단정하는 대신 원문도 함께 후보로 두면, 판정이 틀리는 방향이
거짓양성(정상 파일을 막는다)이 아니라 거짓음성(진짜 오류를 놓친다)이 된다.
AC7이 AC2보다 앞선다 (02 S1-6).

**`]]`는 `]`의 이스케이프다** (실측). 필드 이름에 대괄호가 들어가면 이렇게 적힌다:

```
이름   [P_Year](복사본)_2403322090242050
표기   [[P_Year]](복사본)_2403322090242050]
```

`\\[[^\\]]*\\]`로 자르면 여기서 잘못 끊겨 존재하지 않는 참조가 만들어진다.

특수 네임스페이스는 실측으로 확정했다 — `[:Measure Names]`가 1,294회 나오고,
과거 lint가 정확히 여기서 오탐했다 (함정 S9).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_BRACKET = r"\[(?:[^\]]|\]\])*\]"
"""대괄호 토큰 1개. `]]`(= 이스케이프된 `]`)를 이름의 일부로 먹는다."""

_REF = re.compile(rf"(?P<ds>{_BRACKET})\.(?P<name>{_BRACKET})|(?P<solo>{_BRACKET})")
"""`[ds].[field]` 또는 `[field]`. 자격 있는 형태를 먼저 시도한다."""

_DECORATED = re.compile(r"^(?P<role>[a-z]{1,8}):(?P<inner>.+):(?P<kind>[a-z]{2})(?::\d+)?$")
"""`usr:Calculation_1737…:qk` — 역할 접두 + 종류 접미.

역할은 소문자 짧은 토큰(`none`·`usr`·`sum`·`min`·`mn`·`yr`·`cnt`·`io`·`attr` …),
종류는 2글자(`nk`·`qk`·`ok`)다. **목록으로 고정하지 않는다** — 목록에 없는 집계 접두사가
하나만 나와도 그 필드가 통째로 dangling이 되기 때문이다 (D3.6 실측 분포).

꼬리의 `:숫자`는 같은 필드를 여러 번 올렸을 때 붙는 인스턴스 번호다
(`usr:Calculation_1476…:qk:3` — 실측). 이름의 일부가 아니다."""

REFERENCE_SURFACES = (
    ("column-instance", "column"),
    ("column-instance", "name"),
    ("format", "field"),
    ("text", "column"),
    ("groupfilter", "member"),
    ("filter", "column"),
    ("encoding", "field"),
    ("computed-sort", "using"),
    ("lod", "column"),
)
"""필드를 **직접** 참조하는 요소·속성 (03 D3.6 실측 + 추가 확인분).

`column@name`은 여기 없다 — 그것은 참조가 아니라 **정의**다. 넣으면 규칙 ②가
자기 정의를 근거로 항상 통과한다.

목록 밖 속성은 검사하지 않는다. 추측해서 참조로 읽으면 그 자리가 통째로
거짓 dangling이 된다 (02 S1-6)."""

SPECIAL_PREFIX = ":"
"""`[:Measure Names]`·`[:Measure Values]` — 필드가 아니라 Tableau 내장 축이다."""

SPECIAL_NAMES = frozenset({"Multiple Values"})
"""필드가 아니라 Tableau가 쓰는 표시용 자리표시자 (실측 104회 이상)."""

SPECIAL_DATASOURCES = frozenset({"__tableau_internal_object_id__"})
"""실제 데이터소스가 아니라 Tableau 내부 객체 식별자 네임스페이스다 (실측 42회).
`<datasources>`에 정의가 없으므로 일반 필드 대조로는 항상 dangling이 된다."""


@dataclass(frozen=True, slots=True)
class FieldRef:
    """정규화된 필드 참조 1건."""

    raw: str
    """원문 표기. 사람이 읽는 메시지에 그대로 쓴다."""

    datasource: str | None
    """`[ds].[field]`의 `ds`. 수식 안 참조처럼 자격이 없으면 None."""

    names: tuple[str, ...]
    """대조 후보 (좁은 것 → 넓은 것). **하나라도 맞으면 해소된 것으로 본다.**"""

    special: str | None = None
    """특수 네임스페이스면 그 사유. 규칙 ②는 이 참조를 대조하지 않는다."""


def unescape(name: str) -> str:
    """대괄호 안 이름의 `]]`를 `]`로 되돌린다."""
    return name.replace("]]", "]")


def parse(text: str) -> FieldRef | None:
    """`[a]` 또는 `[a].[b]` 표기 **하나**를 `FieldRef`로 만든다. 형태가 아니면 None.

    >>> parse("[federated.abc].[usr:Calculation_1:qk]").names
    ('Calculation_1', 'usr:Calculation_1:qk')
    >>> parse("[:Measure Names]").special
    'measure-axis'
    """
    m = _REF.fullmatch(text.strip())
    return None if m is None else _from_match(m)


def find_all(text: str) -> list[FieldRef]:
    """문자열 안의 모든 필드 참조. 수식·속성값 어느 쪽에도 쓴다.

    속성값 하나에 참조가 여러 개 들어가는 자리가 있다 (예: `computed-sort@using`).
    """
    return [_from_match(m) for m in _REF.finditer(text)]


def _from_match(m: re.Match[str]) -> FieldRef:
    if m.group("solo") is not None:
        datasource = None
        name = unescape(m.group("solo")[1:-1])
    else:
        datasource = unescape(m.group("ds")[1:-1])
        name = unescape(m.group("name")[1:-1])
    return FieldRef(
        raw=m.group(),
        datasource=datasource,
        names=_candidates(name),
        special=_special_reason(datasource, name),
    )


def _candidates(name: str) -> tuple[str, ...]:
    """대조 후보. 장식을 벗긴 이름을 앞에, 원문을 뒤에 둔다.

    원문을 남기는 이유: 필드 이름 자체가 `abc:xyz:nk`처럼 생겼을 수 있다.
    벗긴 것만 남기면 그 필드가 dangling이 된다.
    """
    m = _DECORATED.match(name)
    if m is None:
        return (name,)
    return (m.group("inner"), name)


def _special_reason(datasource: str | None, name: str) -> str | None:
    """일반 필드 집합으로 대조하면 안 되는 참조인가. 아니면 None."""
    if name.startswith(SPECIAL_PREFIX):
        return "measure-axis"
    if name in SPECIAL_NAMES:
        return "placeholder"
    if datasource in SPECIAL_DATASOURCES:
        return "internal-object-id"
    return None
