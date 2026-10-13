"""L-B rule ⑲: 데이터 원본 팔레트의 키 인스턴스는 **데이터 원본 직속**에도 선언돼 있어야 한다.

**층 2(설정이 버려진다)다.** 파일은 열린다. 그런데 Tableau가 읽으면서 팔레트를
통째로 버린다 — 색이 기본 색으로 나오고, 저장하면 팔레트 항목이 사라진다.
오류 대화상자가 없어서 `passed=true`를 받은 사용자는 *"색이 왜 안 먹지"*에서 멈춘다
(2026-10-13 MA_028 SEC01·SEC03 제보, docs/05-xsd-spike.md F5-q).

```xml
<datasource …>
  <column … />
  <column-instance column='[Calculation_…022]' derivation='User'            <!-- ⓐ 이게 없으면 -->
                   name='[usr:Calculation_…022:nk]' pivot='key' type='nominal' />
  <layout … />
  <style>
    <style-rule element='mark'>
      <encoding attr='color' field='[usr:Calculation_…022:nk]' type='palette'>   <!-- ⓑ 버려진다 -->
        <map to='#2563eb'><bucket>&quot;달성&quot;</bucket></map>
```

⚠️ 레시피 18은 한동안 이 요건을 적지 않았다 — 워크시트의 `<datasource-dependencies>`
안 선언만으로 충분해 보인다. **충분하지 않다.** 팔레트 키는 데이터 원본 수준에서
해소된다.

## 실측 (2026-10-13, `C:/dev/JW/**` 내용 해시로 중복 제거)

- 팔레트 `encoding@field`가 파생 인스턴스(`[usr:X:nk]`·`[none:X:nk]` …) 모양인 것
  **3629건** 중 **3626건**이 같은 데이터 원본 직속 `<column-instance>`에 선언돼 있다
- 반례 **3건**은 한 파일(`MA_004…손익계산서_JWP.twb`)의 합성 ID(`Calculation_91000…`)이며,
  그 데이터 원본에는 `column-instance`가 **0개**다 — Tableau가 저장한 모양이 아니라
  저작물이다. 이 규칙이 잡으려는 바로 그 결함의 표본으로 읽는다
- 인과 — **단일 변수 분리 실험으로 확정**(2026-10-13). 제보자의 *색이 적용되는* 고침본에서
  팔레트 항목은 그대로 두고 팔레트 키 2개의 직속 `column-instance`**만** 지웠더니 색이
  적용되지 않았다 (요소 단위 diff로 다른 차이 0 확인, 주입 레시피 R36이 만든 파일).
  제보 당시 두 변경을 한꺼번에 해서 남았던 의문이 이로써 닫혔다 — 직속 선언은 **필요조건**이다
- 그래도 **WARNING**이다 — 인과 때문이 아니라 층 때문이다. 파일은 열리고 설정만 버려지므로
  층 2다 (S1-6: ERROR는 파일이 안 열린다고 확신할 때만)

## 이 규칙이 보지 않는 것 — 같은 제보가 제안했으나 실측이 반례를 냈다

- **`[:Measure Names]` 별칭 키**의 인스턴스 선언 — 22,904건 중 **1,529건이 미선언**이다
  (6.7%). 별칭 키는 필드를 지워도 남는 낡은 키가 많아서 *"선언돼 있어야 한다"*가 성립하지
  않는다. 규칙으로 만들면 정상본이 거짓양성으로 쏟아진다
- **`usr:` 팔레트 키의 `column@role`** — `measure` 2002건 : `dimension` **41건**. 정상본에
  반례가 41건 있으므로 role로 거르지 않는다. (제보의 `dimension`→`measure` 정정은 이미
  이전 저장에서 반영돼 있었고, 이번 증상의 원인으로 분리되지 않았다)
- **데이터 원본 직속 인스턴스를 워크시트 사용분의 *합집합*으로 채워야 하는가** — 정본
  파일은 합집합 모양이지만 필요조건인지는 확정되지 않았다. **팔레트 키만** 본다
- 파생 모양이 아닌 필드(`[:Measure Names]` 등 내장 필드)는 키 인스턴스가 없다 — 판정 대상이 아니다
"""

from __future__ import annotations

import re
from typing import Any

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

# `[<파생>:<필드>:<접미>]` — 파생 인스턴스 이름. `[:Measure Names]`는 파생이 비어 여기 안 걸린다.
_INSTANCE_NAME = re.compile(r"^\[[a-z]+:[^\]]+:[a-z]+\]$")


@register
class PaletteInstancesRule(RuleBase):
    id = "palette.instance_declared"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 팔레트 인스턴스를 검사하지 못했다")
            return []

        block = ctx.raw_tree.find("datasources")
        datasources = list(block.findall("datasource")) if block is not None else []

        findings: list[Finding] = []
        checked = 0
        for ds in datasources:
            declared = {ci.get("name") for ci in ds.findall("column-instance")}
            for enc in ds.findall("style/style-rule/encoding"):
                field = enc.get("field") or ""
                if enc.get("type") != "palette" or not _INSTANCE_NAME.match(field):
                    continue
                checked += 1
                if field not in declared:
                    findings.append(_finding_for(ds, enc, field))

        if not checked:
            ctx.note_skip(
                self.id,
                "데이터 원본 수준 색상 팔레트가 없어 검사할 것이 없다",
                scope="palette",
            )
        return findings


def _finding_for(ds: Any, enc: Any, field: str) -> Finding:
    name = (ds.get("caption") or ds.get("name") or "(이름 없음)").strip("[]")
    prefix, base, suffix = _split(field)
    return Finding(
        severity=Severity.WARNING,
        rule_id=PaletteInstancesRule.id,
        location=str(enc.getroottree().getpath(enc)),
        line=enc.sourceline,
        message=(
            f"데이터 원본 `{name}`의 팔레트 키 `{field}`가 같은 데이터 원본 직속 "
            "`<column-instance>`로 선언돼 있지 않다 — 파일은 열리지만 Tableau가 "
            "이 팔레트를 버려 색이 기본 색으로 나온다"
        ),
        fix=(
            f"`<datasource>` 직속(`<column>` 목록 뒤, `<layout>`·`<folders-common>` 앞)에 "
            f"`<column-instance column='[{base}]' derivation='{_derivation(prefix)}' "
            f"name='{field}' pivot='key' type='{_type(suffix)}' />`를 추가한다 "
            "(레시피 18). 워크시트의 `<datasource-dependencies>` 선언만으로는 "
            "팔레트가 살아남지 않는다."
        ),
    )


def _split(field: str) -> tuple[str, str, str]:
    """`[usr:Calculation_1:nk]` → (`usr`, `Calculation_1`, `nk`). 필드명에 `:`이 있어도 된다."""
    prefix, _, rest = field.strip("[]").partition(":")
    base, _, suffix = rest.rpartition(":")
    return prefix, base, suffix


def _derivation(prefix: str) -> str:
    return {"usr": "User", "none": "None", "sum": "Sum", "attr": "Attribute"}.get(prefix, prefix)


def _type(suffix: str) -> str:
    return {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}.get(suffix, "nominal")
