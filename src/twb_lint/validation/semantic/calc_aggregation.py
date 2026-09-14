"""L-B rule ⑧: 계산필드 수식과 `column-instance@derivation`의 집계 정합.

방향이 둘이다. ⑧-a는 **집계가 모자란** 쪽, ⑧-b는 **집계가 겹친** 쪽이다.
같은 두 표면(수식 · 파생)을 교차 검사하므로 한 규칙에 둔다.

## ⑧-a — 사용자 지정 집계(`usr:`)로 올린 계산의 집계 정합

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

## ⑧-b — 집계식에 집계 파생을 다시 걸었다 (이중 집계)

반대 방향이다. 수식이 이미 집계인데 `derivation="Sum"` 같은 집계 파생을 얹으면
`SUM(SUM(…))`이 되어 그 필드가 **빨간 알약**이 되고 시트가 렌더링되지 않는다.

```xml
<column name='[C_매출]'><calculation formula='SUM(IF … THEN [idct_val] END)' /></column>
<column-instance column='[C_매출]' derivation='Sum' name='[sum:C_매출:qk]' />
```

**수식을 행 수준에서 집계로 고칠 때 인스턴스가 따라오지 않아서** 생긴다 (2026-08-12
MA_011 실측). 저작 시점에는 행 수준이라 `[sum:…]`이 맞았고, 나중에 수식만 `SUM(…)`으로
바꾸면서 파생이 남았다. 규칙 ⑧-a도 ②도 못 잡는다 — 수식은 멀쩡하고 참조도 해소된다.

**워크시트에 등재된 인스턴스만 본다.** 실측(2026-08-12, 실파일 47개): 위반 65건 중
63건이 데이터소스에만 있고 어느 워크시트도 쓰지 않는 **잔재**다. 잔재까지 세면
정상본이 시끄러워지고(AC7의 취지) 증상도 없다 — 빨간 알약은 그 인스턴스를 실제로
쓰는 시트에서만 난다.

남는 반례는 2건, `태블로판차분석` 한 계보뿐이다(`SUM({ FIXED … })`에 `sum:`).
그 파일은 규칙 ⑪에서도 dangling 28건이 나온 파일이라 진짜 결함일 가능성이 높지만,
확인 전까지는 **WARNING**이다 (02 S1-6).

## ⑧-c — 한 수식 안에서 집계와 행수준을 섞었다 (2026-09-14)

⑧-a·⑧-b와 **입력이 다르다.** 둘은 수식과 `derivation` 선언을 교차 검사하지만,
⑧-c는 **수식 안만** 본다. 묻는 것은 같다 — 집계 수준이 맞는가.

```
SUM([매출]) + [수량]                        집계 + 행수준
IF SUM([A]) > 0 THEN [B] ELSE 0 END        조건은 집계, 분기는 행수준
```

    오류: 집계 및 비집계 인수를 이 함수와 함께 혼합할 수 없습니다.

**가려지는 자리가 둘이다.** 집계 함수의 인자 안은 행수준이 정상이고(`SUM([A] + [B])`),
LOD 중괄호 안도 마찬가지다(`{FIXED [a] : SUM([b])} + [c]`는 정상) — ⑧-a가 LOD를
집계로 치지 않는 것과 같은 판단이다.

**`MIN`·`MAX`는 인자 수로 갈린다.** `MIN([A])`는 집계지만 `MIN([A], [B])`는 행수준
함수다 (실측 1개 4,849 : 2개 49). 이걸 안 가르면 정상본이 걸린다 — 실제로 첫
시제품이 MA_006의 `F_PERIOD` 계열 21건을 오탐했고, 원인이 그것이었다.

실측 (2026-09-14, 실파일 138개 · 수식 85,316건): **혼합 0건.**
`TODO.md`가 *"시제품 실측이 실파일에서 혼합 0건 → 잡을 게 없는 규칙"*으로 적어 둔
그 수치인데, **읽기가 틀렸다**: 0건은 규칙이 무용하다는 뜻이 아니라 **AC7 근거**다.
정상 워크북은 Tableau 편집기를 통과했으므로 혼합이 있을 수 없다. 검출 근거는
규칙 ⑯과 같은 자리에서 온다 — 주입 레시피 R31과 우리 저작본이다 (01 v2.0).

⚠️ **모르면 침묵한다**는 ⑧-a와 같다. 맨 참조를 끝까지 펼치지 못하면 위반이 아니라
`note_partial`이다. 매개변수는 상수라 어느 쪽에도 걸지 않는다.
"""

from __future__ import annotations

import re
from typing import Any

from twb_lint import fieldref
from twb_lint.calc.extractor import (
    aggregation_split,
    extract,
    formulas_in,
)
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

AGGREGATE_DERIVATIONS = frozenset(
    {
        "Sum", "Avg", "Min", "Max", "Count", "CountD", "Median",
        "Stdev", "StdevP", "Var", "VarP", "Attr",
    }
)
"""집계를 **거는** 파생. `User`(수식이 스스로 집계)와 `None`·`Month` 등은 아니다.

⑧-b가 쓴다. 실파일 47개에 실제로 나온 것은 `Sum`·`Attribute` 계열이지만, 목록을
좁히면 `Avg`로 쓴 같은 결함을 놓친다 — 여기 있는 것은 전부 집계 함수 이름이다."""

ARITY_SENSITIVE_AGGREGATES = frozenset({"MIN", "MAX"})
"""인자 1개면 집계, 2개면 **행수준 함수**다 (실측 `MIN` 1개:4,849 · 2개:49).

⑧-c만 쓴다. ⑧-a·⑧-b의 `_chain_has_aggregate`는 이 구분 없이 돌아왔고, 그 결과를
지금 바꾸면 두 검사의 실측 근거가 함께 흔들린다 — 필요해지면 따로 잰다."""

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
        out = self._missing_aggregate(ctx, formulas, known, undecided)
        out += self._double_aggregate(ctx, formulas, known, undecided)
        out += self._mixed_levels(ctx, formulas, known, undecided)

        if undecided:
            # 판정 못 한 것을 조용히 넘기면 "전부 검사했다"로 읽힌다 (02 S5).
            ctx.note_partial(
                self.id,
                f"참조를 끝까지 펼치지 못해 {len(set(undecided))}종은 판정하지 못했다 "
                f"({', '.join(sorted(set(undecided))[:5])})",
                scope="aggregation-undecided",
            )
        return out

    def _missing_aggregate(
        self,
        ctx: ValidationContext,
        formulas: dict[str, str],
        known: set[str],
        undecided: list[str],
    ) -> list[Finding]:
        """⑧-a — `usr:`로 올렸는데 수식에 집계가 없다."""
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
        return out

    def _double_aggregate(
        self,
        ctx: ValidationContext,
        formulas: dict[str, str],
        known: set[str],
        undecided: list[str],
    ) -> list[Finding]:
        """⑧-b — 집계식에 집계 파생(`sum:` 등)을 다시 걸었다."""
        out: list[Finding] = []
        for el, name, derivation in _view_aggregate_instances(ctx.raw_tree):
            if name not in formulas:
                continue  # 계산이 아닌 원본 컬럼 — `SUM([매출액])`은 정상이다
            verdict = _chain_has_aggregate(name, formulas, known)
            if verdict is None:
                undecided.append(name)
                continue
            if not verdict:
                continue
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(el),
                    line=el.sourceline,
                    message=(
                        f"`{name}`는 이미 집계식인데 `derivation='{derivation}'`으로 "
                        "다시 집계했다 — 필드가 **빨간 알약**이 되고 그 시트가 "
                        "렌더링되지 않는다"
                    ),
                    fix=(
                        "`derivation='User'` · `name='[usr:…:qk]'`로 바꾸고, 그 인스턴스를 "
                        "가리키는 선반·필터·`slices`·`style-rule/format@field`·"
                        "`encodings` 참조도 함께 교체한다."
                    ),
                )
            )
        return out


    def _mixed_levels(
        self,
        ctx: ValidationContext,
        formulas: dict[str, str],
        known: set[str],
        undecided: list[str],
    ) -> list[Finding]:
        """⑧-c — 한 수식 안에서 집계와 행수준을 섞었다."""
        params = _parameter_names(ctx)
        out: list[Finding] = []
        for el, formula in formulas_in(ctx.raw_tree):
            split = aggregation_split(
                formula, AGGREGATE_FUNCTIONS, ARITY_SENSITIVE_AGGREGATES
            )
            if not split.aggregates:
                continue
            row_level = _confident_row_level(
                split.bare_refs, formulas, known, params, undecided
            )
            if not row_level:
                continue
            shown = ", ".join(f"`{r}`" for r in row_level[:3])
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(el),
                    line=el.sourceline,
                    message=(
                        f"수식이 집계(`{split.aggregates[0]}`)와 행수준 참조 {shown}를 "
                        "같은 자리에서 섞었다 — Tableau가 *'집계 및 비집계 인수를 이 "
                        "함수와 함께 혼합할 수 없습니다'*로 거부하고, 그 필드를 쓰는 "
                        "시트가 **빈 화면**이 된다"
                    ),
                    fix=(
                        f"행수준 참조를 집계로 감싸거나(`SUM({row_level[0]})`·"
                        f"`ATTR({row_level[0]})`), 반대로 집계를 벗겨 양쪽을 행수준으로 "
                        "맞춘다. 뷰 그레인과 무관한 값이면 LOD(`{FIXED … }`)로 고정한다."
                    ),
                )
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


def _view_aggregate_instances(root: Any) -> list[tuple[Any, str, str]]:
    """**워크시트에 등재된** 집계 파생 인스턴스 → (요소, 대상 계산 이름, 파생).

    데이터소스에만 있는 인스턴스는 빼는 것이 이 함수의 요점이다 — 실측 위반 65건 중
    63건이 그 잔재였다 (⑧-b 독스트링). 이름당 첫 자리만 보고한다.
    """
    seen: set[tuple[str, str]] = set()
    out: list[tuple[Any, str, str]] = []
    for worksheet in root.iter("worksheet"):
        for ci in worksheet.iter("column-instance"):
            derivation = ci.get("derivation") or ""
            if derivation not in AGGREGATE_DERIVATIONS:
                continue
            name = (ci.get("column") or "").strip("[]")
            if not name or (name, derivation) in seen:
                continue
            seen.add((name, derivation))
            out.append((ci, name, derivation))
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

    if AGGREGATE_FUNCTIONS & extract(_strip_lod(formula)).functions:
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



def _parameter_names(ctx: ValidationContext) -> set[str]:
    """매개변수 이름. 상수이므로 집계에도 행수준에도 걸지 않는다."""
    ds = ctx.model.datasources.get("Parameters")
    return set(ds.fields) if ds is not None else set()


def _confident_row_level(
    refs: tuple[str, ...],
    formulas: dict[str, str],
    known: set[str],
    params: set[str],
    undecided: list[str],
) -> list[str]:
    """맨 참조 중 **행수준임이 확실한** 것만 고른다.

    판정 불가를 위반으로 읽지 않는 것이 이 검사의 안전장치다 (⑧-a와 같다).
    확실한 세 가지만 통과시킨다 — 정의를 아는 비집계 계산 · 원본 컬럼 · 그 둘뿐이다.
    """
    out: list[str] = []
    for raw in refs:
        ref = fieldref.parse(raw)
        if ref is None or ref.special is not None:
            continue  # `[:Measure Names]` 같은 내장 축 — 필드가 아니다
        name = _last_name(raw)
        if name in params:
            continue  # 매개변수는 상수다
        if name in formulas:
            verdict = _chain_has_aggregate(name, formulas, known)
            if verdict is None:
                undecided.append(name)
            elif not verdict:
                out.append(raw)
            continue
        if name in known:
            out.append(raw)  # 원본 컬럼 — 집계가 아님이 확실하다
        else:
            undecided.append(name)
    return out


def _strip_lod(formula: str) -> str:
    """LOD 블록을 **중첩까지** 지운다.

    한 번만 치환하면 `{ FIXED a : AVG({ FIXED a,b : SUM(…) }) }`에서 안쪽만 지워지고
    바깥 `AVG(`가 남아 집계로 읽힌다. 실측에서 MA_008의 `C_목표값`이 정확히 이 모양이라
    ⑧-b가 정상 필드 6건을 위반으로 셌다 (2026-08-12).
    """
    prev = None
    while prev != formula:
        prev = formula
        formula = _LOD_BLOCK.sub(" ", formula)
    return formula


def _last_name(raw: str) -> str:
    """`[ds].[field]` · `[field]` 어느 쪽이든 마지막 이름만 꺼낸다."""
    parts = [p for p in raw.replace("].[", "]\x00[").split("\x00") if p]
    return parts[-1].strip("[]") if parts else raw.strip("[]")


def _path_of(el: Any) -> str:
    return str(el.getroottree().getpath(el))
