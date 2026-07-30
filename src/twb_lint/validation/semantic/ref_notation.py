"""L-B rule ⑦: 참조 **표기 규약**.

규칙 ②(`calc.field_refs`)와 묻는 것이 다르다 — ②는 *"가리키는 필드가 있는가"*,
⑦은 *"그 자리에 쓸 수 있는 표기인가"*다. 필드가 멀쩡히 존재해도 표기가 틀리면
Tableau는 **로드는 하고 그 설정만 버린다**:

```
'SEC06_추이' 오류: '측정값 이름' 필드의 필터를 구문 분석하는 동안
오류가 발생했습니다. 필터를 무시합니다.

'SEC06_추이' 워크시트에 오류가 있습니다. 다음이 제거됩니다.
 — 이름이 '[Multiple Values]'인 필드가 없습니다.
```

세 번째 표면은 수식이다 — 매개변수 참조에 `[Parameters].` 한정자가 없으면 계산필드가
통째로 **오류 상태**가 되고 그 필드에 의존하는 시트가 빈 화면이 된다 (⑦-c).

**전부 WARNING이다** (02 S1-6). 파일은 열린다 — 열리지 않는다고 확신할 때만 ERROR다.
대신 조용하지 않다: 필터가 사라진 화면은 **틀린 숫자를 보여준다.**

세 검사 모두 2026-07-30 MA_003 매출표 실측 + 실파일 61개 전수 상관이 근거다
(docs/05-xsd-spike.md F5-c).
"""

from __future__ import annotations

import re
from typing import Any

from twb_lint import fieldref
from twb_lint.calc.extractor import extract, formulas_in
from twb_lint.models import Finding, Severity, WorkbookModel
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_FINDINGS = 200
"""보고 상한. 자른 사실은 `note_partial`로 보고한다 (02 S5)."""

PARAMETERS_DS = "Parameters"
"""매개변수를 담는 인라인 데이터소스의 이름. 실측 61/61 파일에서 이 이름이다."""

_QUALIFIED_REF = re.compile(r"^\[[^\[\]]+\]\.\[[^\[\]]+\]$")
"""`[ds].[field]` 하나만. 여러 참조가 이어진 값은 대상이 아니다."""

BARE_PLACEHOLDER = "[Multiple Values]"
"""데이터소스 한정자가 없는 자리표시자 표기.

`fieldref.SPECIAL_NAMES`가 이 이름을 필드 대조에서 제외하므로 규칙 ②는 침묵한다 —
제외는 옳다(필드가 아니다). 빠진 것은 **한정자 유무**이고 그것이 이 검사다."""

PLACEHOLDER_SURFACES = (("text", "column"), ("rows", None), ("cols", None))
"""자리표시자가 나타나는 자리. `None`이면 속성이 아니라 요소 텍스트다.

목록 밖은 검사하지 않는다 — 추측해서 늘리면 그 자리가 통째로 거짓양성이 된다
(02 S1-6)."""


@register
class RefNotationRule(RuleBase):
    id = "ref.notation"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 참조 표기를 검사하지 못했다")
            return []

        findings = (
            self._member_literals(ctx.raw_tree)
            + self._placeholders(ctx.raw_tree)
            + self._bare_parameters(ctx)
        )
        findings.sort(key=lambda f: (f.location, f.message))
        if len(findings) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"표기 위반 {len(findings)}건 중 앞 {MAX_FINDINGS}건만 보고한다",
                scope="ref-notation",
            )
            findings = findings[:MAX_FINDINGS]
        return findings

    def _member_literals(self, root: Any) -> list[Finding]:
        """⑦-a — `groupfilter@member`의 필드 참조는 **문자열 리터럴**이어야 한다.

        `member`는 값을 담는 자리다. 필드 참조를 값으로 쓸 때도 따옴표로 감싼다:

        ```xml
        <groupfilter function='member' level='[:Measure Names]'
                     member='&quot;[federated.abc].[usr:C_실적:qk]&quot;' />
        ```

        실파일 61개: 감싼 것 714건 · 안 감싼 것은 **거부된 그 파일뿐**(14건, 반례 0).
        `member='true'`(불리언)·`member='&quot;SAMT&quot;'`(문자열)는 대상이 아니다 —
        `[ds].[field]` 형태일 때만 본다.
        """
        out: list[Finding] = []
        for el in root.iter("groupfilter"):
            if el.get("function") != "member":
                continue
            value = el.get("member")
            if value is None or not _QUALIFIED_REF.match(value):
                continue
            out.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location=_path_of(el),
                    line=el.sourceline,
                    message=(
                        f"필터 member `{value}`가 따옴표로 감싸이지 않았다 — "
                        "Tableau가 필터를 구문 분석하지 못하고 **무시한다**"
                    ),
                    fix=f"""member='"{value}"' 처럼 값 전체를 따옴표로 감싼다.""",
                )
            )
        return out

    def _placeholders(self, root: Any) -> list[Finding]:
        """⑦-b — `[Multiple Values]`는 데이터소스 한정자가 있어야 한다.

        실파일 22개에서 235회 나오는데 **전부** `[federated.…].[Multiple Values]`다.
        한정자를 빼면 *"이름이 '[Multiple Values]'인 필드가 없습니다"*로 그 필드가
        워크시트에서 제거된다 (2026-07-30 실측).
        """
        out: list[Finding] = []
        for tag, attr in PLACEHOLDER_SURFACES:
            for el in root.iter(tag):
                value = el.get(attr) if attr is not None else el.text
                if value is None or value.strip() != BARE_PLACEHOLDER:
                    continue
                where = f"{tag}@{attr}" if attr is not None else f"{tag} 텍스트"
                out.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_id=self.id,
                        location=_path_of(el),
                        line=el.sourceline,
                        message=(
                            f"{where}의 `{BARE_PLACEHOLDER}`에 데이터소스 한정자가 없다 — "
                            "Tableau가 그 필드를 찾지 못해 **워크시트에서 제거한다**"
                        ),
                        fix=(
                            f"`[<데이터소스 이름>].{BARE_PLACEHOLDER}`로 쓴다 "
                            "(그 워크시트의 `view/datasources`에 있는 이름)."
                        ),
                    )
                )
        return out


    def _bare_parameters(self, ctx: ValidationContext) -> list[Finding]:
        """⑦-c — 수식 안 매개변수 참조는 `[Parameters].[이름]`으로 한정해야 한다.

        ```
        DATE(DATEPARSE('yyyyMM', STR([P_YEAR]) + …))              계산에 오류 있음
        DATE(DATEPARSE('yyyyMM', STR([Parameters].[P_YEAR]) + …)) 정상
        ```

        실파일 61개: 한정된 참조 3,377건 · 한정 없는 것은 **거부된 그 파일뿐**(36건).

        ⚠️ **규칙 ②가 원리적으로 못 잡는다.** ②는 자격 없는 참조를 전 데이터소스 필드
        합집합과 대조하므로(07 G5의 의도된 트레이드오프) `[P_YEAR]`가 Parameters에
        있다는 이유로 해소된 것으로 본다. 여기서 그 거짓음성이 물었다.

        이름이 **데이터 컬럼에도** 있으면 보고하지 않는다 — 매개변수를 가리킨다고
        단정할 수 없다 (02 S1-6).
        """
        if ctx.raw_tree is None or PARAMETERS_DS not in ctx.model.datasources:
            return []

        params = ctx.model.field_names(PARAMETERS_DS)
        data_fields = _fields_outside_parameters(ctx.model)
        seen: set[str] = set()
        out: list[Finding] = []
        for el, formula in formulas_in(ctx.raw_tree):
            for raw in sorted(extract(formula).field_refs):
                for ref in fieldref.find_all(raw):
                    if ref.datasource is not None:
                        continue
                    hit = next((n for n in ref.names if n in params), None)
                    if hit is None or hit in data_fields or hit in seen:
                        continue
                    seen.add(hit)
                    out.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_id=self.id,
                            location=_path_of(el),
                            line=el.sourceline,
                            message=(
                                f"수식이 매개변수 `{hit}`를 한정자 없이 참조한다 — "
                                "계산필드가 **오류 상태**가 되고 그 필드를 쓰는 시트가 "
                                "빈 화면이 된다"
                            ),
                            fix=f"`[{PARAMETERS_DS}].[{hit}]`로 쓴다.",
                        )
                    )
        return out


def _fields_outside_parameters(model: WorkbookModel) -> set[str]:
    """매개변수가 아닌 데이터소스들의 필드 이름 합집합."""
    return {
        name
        for ds_name, ds in model.datasources.items()
        if ds_name != PARAMETERS_DS
        for name in ds.fields
    }


def _path_of(el: Any) -> str:
    """요소의 xpath. L-A·규칙 ②의 `location`과 같은 표기를 쓴다."""
    return str(el.getroottree().getpath(el))
