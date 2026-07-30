"""L-B rule ⑧: 사용자 지정 집계(`usr:`)로 올린 계산의 집계 정합.

Tableau는 계산필드를 뷰에 올릴 때 두 가지로 직렬화한다:

```xml
<column-instance column="[X]" derivation="None" name="[none:X:nk]" />   차원으로
<column-instance column="[X]" derivation="User" name="[usr:X:qk]"  />   사용자 지정 집계로
```

`derivation="User"`는 *"이 계산이 스스로 집계한다"*는 선언이다. 수식에 집계가 없으면
Tableau가 거부한다 — 파일은 열리되 그 필드가 **빨갛게 뜨고 시트가 비어 있다**:

    오류: 'C_L_전체' 계산에는 집계되지 않은 수식의 사용자 지정 집계가 필요합니다.

실측(2026-07-30, docs/05-xsd-spike.md F5-e): 정상본 61개에서 `usr:` 인스턴스의 계산은
**참조 체인을 끝까지 펼치면 반드시 집계 함수가 나온다**(20종 표본 전부, 반례 0).
MA_003 매출표의 `C_L_전체`(`"전체"`)·`C_L_세부현황`은 체인 전체에 집계가 없었다.

**LOD(`{ FIXED … : MAX(…) }`)는 집계로 치지 않는다.** LOD 결과는 행 수준 값처럼 쓰이며,
실측에서 LOD만 참조하는 `C_L_세부현황`이 정확히 이 오류로 거부됐다.

**WARNING이다** (02 S1-6). 파일은 열린다.

⚠️ **모르면 침묵한다.** 참조를 펼치지 못했으면(외부 필드·미지 표기) 그 계산은 판정하지
않고 건너뛴 사실을 `note_partial`로 보고한다. 집계 함수 목록이 불완전하면 거짓양성이
나는 구조라, 판정 불가를 위반으로 읽지 않는다.
"""

from __future__ import annotations

import re
from typing import Any

from twb_lint.calc.extractor import extract
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_DEPTH = 8
"""참조 체인 추적 깊이. 실측 최대 4단이라 여유가 충분하다."""

AGGREGATE_FUNCTIONS = frozenset(
    {
        "SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD", "MEDIAN", "ATTR",
        "STDEV", "STDEVP", "VAR", "VARP", "PERCENTILE", "COLLECT", "CORR",
        "COVAR", "COVARP", "GROUP_CONCAT",
        # 테이블 계산도 집계 문맥을 만든다
        "TOTAL", "INDEX", "SIZE", "FIRST", "LAST", "LOOKUP", "PREVIOUS_VALUE",
        "RANK", "RANK_DENSE", "RANK_MODIFIED", "RANK_PERCENTILE", "RANK_UNIQUE",
        "RUNNING_SUM", "RUNNING_AVG", "RUNNING_MIN", "RUNNING_MAX", "RUNNING_COUNT",
        "WINDOW_SUM", "WINDOW_AVG", "WINDOW_MIN", "WINDOW_MAX", "WINDOW_COUNT",
        "WINDOW_MEDIAN", "WINDOW_STDEV", "WINDOW_VAR", "WINDOW_CORR", "WINDOW_COVAR",
        "WINDOW_PERCENTILE",
    }
)
"""집계 문맥을 만드는 함수. `data/functions/`의 화이트리스트는 집계 여부를 구분하지
않으므로 여기 따로 둔다 (출처: Tableau 2026.1 함수 분류 + 실파일 61개 실측)."""

_LOD_BLOCK = re.compile(r"\{[^{}]*\}")
"""LOD 표현식. 안쪽 집계는 집계로 치지 않는다 — 위 독스트링 참조."""


@register
class CalcAggregationRule(RuleBase):
    id = "calc.aggregation"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 집계 정합을 검사하지 못했다")
            return []

        formulas = _formulas_by_name(ctx.raw_tree)
        if not formulas:
            ctx.note_skip(self.id, "계산필드가 없어 집계 정합을 검사할 것이 없다")
            return []
        if not ctx.model.datasources:
            # 필드 유니버스가 없으면 "정의가 없는 참조"와 "원본 컬럼"을 못 가른다.
            ctx.note_skip(self.id, "데이터소스가 없어 참조를 펼치지 못했다")
            return []

        known = _known_fields(ctx)
        undecided: list[str] = []
        out: list[Finding] = []
        for el, name in _user_aggregations(ctx.raw_tree):
            formula = formulas.get(name)
            if formula is None:
                continue  # 이 워크북에 정의가 없는 계산 — 규칙 ②의 소관이다
            verdict = _chain_has_aggregate(name, formulas, known)
            if verdict is None:
                undecided.append(name)
                continue
            if verdict:
                continue
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(el),
                    line=el.sourceline,
                    message=(
                        f"`{name}`를 사용자 지정 집계(`usr:`)로 올렸는데 수식에 집계가 없다 — "
                        "필드가 오류 상태가 되고 그 시트가 **비어 나온다**"
                    ),
                    fix=(
                        f"수식을 집계로 감싸거나(`MIN({formula.strip()[:40]}…)`) "
                        "뷰에서 차원(`none:`)으로 올린다."
                    ),
                )
            )

        if undecided:
            # 판정 못 한 것을 조용히 넘기면 "전부 검사했다"로 읽힌다 (02 S5).
            ctx.note_partial(
                self.id,
                f"참조를 끝까지 펼치지 못해 {len(undecided)}종은 판정하지 못했다 "
                f"({', '.join(sorted(undecided)[:5])})",
                scope="aggregation-undecided",
            )
        return out


def _formulas_by_name(root: Any) -> dict[str, str]:
    """계산필드 이름 → 수식. 워크시트 안 복제본도 같은 이름을 쓴다."""
    out: dict[str, str] = {}
    for col in root.iter("column"):
        name = (col.get("name") or "").strip("[]")
        calc = col.find("calculation")
        if name and calc is not None and calc.get("formula"):
            out.setdefault(name, calc.get("formula") or "")
    return out


def _user_aggregations(root: Any) -> list[tuple[Any, str]]:
    """`derivation="User"` 인스턴스 → (요소, 대상 계산 이름). 이름당 첫 자리만."""
    seen: set[str] = set()
    out: list[tuple[Any, str]] = []
    for ci in root.iter("column-instance"):
        if ci.get("derivation") != "User":
            continue
        name = (ci.get("column") or "").strip("[]")
        if name and name not in seen:
            seen.add(name)
            out.append((ci, name))
    return out


def _known_fields(ctx: ValidationContext) -> set[str]:
    """워크북이 정의한 모든 필드 이름 (계산·원본·매개변수). 규칙 ②와 같은 유니버스다.

    여기 있는 비계산 필드는 **집계가 아님이 확실**하다. 여기에도 없는 참조만
    "판정 불가"로 센다."""
    return {
        name for ds in ctx.model.datasources.values() for name in ds.fields
    }


def _chain_has_aggregate(
    name: str,
    formulas: dict[str, str],
    known: set[str],
    depth: int = 0,
    seen: set[str] | None = None,
) -> bool | None:
    """참조 체인에 집계가 있는가. `None`이면 **판정 불가**(펼치지 못한 참조가 있다).

    판정 불가와 "집계 없음"을 구분하는 것이 이 규칙의 안전장치다 —
    섞으면 우리 지식의 공백이 남의 정상 파일을 막는다 (02 S1-6).
    """
    seen = seen or set()
    if name in seen:
        return False  # 순환 — 이 가지에서는 집계를 못 찾았다
    if depth >= MAX_DEPTH:
        return None
    seen.add(name)

    formula = formulas.get(name)
    if formula is None:
        return None

    outside_lod = _LOD_BLOCK.sub(" ", formula)
    if AGGREGATE_FUNCTIONS & extract(outside_lod).functions:
        return True

    unresolved = False
    for raw in sorted(extract(formula).field_refs):
        ref = _last_name(raw)
        if ref in formulas:
            nested = _chain_has_aggregate(ref, formulas, known, depth + 1, seen)
            if nested:
                return True
            if nested is None:
                unresolved = True
        elif ref not in known:
            # 워크북 어디에도 정의가 없다 — 우리가 못 펼친 것이지 비집계라는 뜻이 아니다.
            unresolved = True
        # `known`에 있는 비계산 필드(원본 컬럼·매개변수)는 집계가 아니다 → 그냥 넘어간다
    return None if unresolved else False


def _last_name(raw: str) -> str:
    """`[ds].[field]` · `[field]` 어느 쪽이든 마지막 이름만 꺼낸다."""
    parts = [p for p in raw.replace("].[", "]\x00[").split("\x00") if p]
    return parts[-1].strip("[]") if parts else raw.strip("[]")


def _path_of(el: Any) -> str:
    return str(el.getroottree().getpath(el))
