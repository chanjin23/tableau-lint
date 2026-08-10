"""L-B rule ⑭: 데이터 원본의 객체 모델 골격.

**층 정의 바깥의 실패다.** 파일은 정상적으로 열리고 시트도 보이는데,
**데이터 원본 탭을 클릭하는 순간 Tableau가 그대로 종료된다** — 빨간 느낌표보다 나쁘다.
저장할 것도 없이 앱이 사라진다 (2026-08-10 실측, docs/06-rule-candidates.md R25).

Tableau가 만든 파일은 연결된 데이터 원본을 **두 벌**로 기록한다:

```xml
<datasource …>
  <connection class='federated'>
    <relation connection='textscan.…' table='[관찰_data#csv]' type='table'>
      <columns character-set='UTF-8' header='yes' separator=','>   <!-- ⓑ 파일 연결의 열 목록 -->
        <column datatype='string' name='지역' ordinal='0' />
      </columns>
    </relation>
  </connection>
  <object-graph>                                                   <!-- ⓐ 같은 relation의 사본 -->
    <objects><object caption='…' id='…'><properties context=''>
      <relation …>…</relation>
    </properties></object></objects>
  </object-graph>
</datasource>
```

중복처럼 보이지만 **둘 다 있어야 한다.** 데이터 원본 화면은 `<object-graph>`를 읽는다.

실측 — 상관과 인과를 **둘 다** 잡았다:

- **상관** — 실파일 113개 데이터 원본(`text` 74 · `table` 39) 전부
  `<relation>`이 있으면 `<object-graph>`도 있다. 반례 0
- **인과** — 분리 실험 V1(정본에서 `<object-graph>`만 제거):
  데이터 원본 탭 클릭 시 Tableau 즉시 종료

**ERROR다.** 이 규칙만 예외적으로 층 1이 아닌데 ERROR를 낸다:

- 거짓양성 위험이 없다 — 실파일 114개에서 finding 0건 (AC7)
- 인과가 실험으로 확정됐다 — 상관만 보고 낸 것이 아니다
- 증상이 층 4보다 무겁다. 빨간 느낌표는 보고 고칠 수 있지만 **앱 종료는 작업분이 날아간다**

같은 실험에서 **후보 하나가 죽었다** — `relation@type='table'`에 `<columns>`가
없는 변형(V2)은 데이터 원본 탭이 **멀쩡했다**. 상관은 39:0이었지만 증상이 없어
규칙에 넣지 않는다 (D2-b 폐기와 같은 판단). 정본 형태는 레시피 21 §②에 남긴다.

매니페스트 3항목(`ObjectModelTableType`·`ObjectModelEncapsulateLegacy`·
`SchemaViewerObjectModel`)이 없으면 `<object-graph>`는 **로드 자체가 거부**된다(V3).
그쪽은 규칙 ⑥-b `manifest.gates`의 담당이다 — 여기는 항목이 선언된 상태에서
요소가 빠진 경우를 본다.

⚠️ 워크시트 안 `<datasource-dependencies>`의 사본은 대상이 아니다 —
연결이 없으므로 `<relation>`도 없고, 여기서 자연히 걸러진다.
"""

from __future__ import annotations

from typing import Any

from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class DatasourceShapeRule(RuleBase):
    id = "datasource.shape"
    stage = Stage.SEMANTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 데이터 원본 골격을 검사하지 못했다")
            return []

        connected = [
            ds for ds in _top_level_datasources(ctx.raw_tree) if _has_relation(ds)
        ]
        if not connected:
            ctx.note_skip(self.id, "연결된 데이터 원본이 없어 검사할 것이 없다")
            return []

        return [_finding_for(ds) for ds in connected if ds.find("object-graph") is None]


def _top_level_datasources(root: Any) -> list[Any]:
    """`<workbook>/<datasources>` 직속만. 워크시트 안 사본은 보지 않는다."""
    block = root.find("datasources")
    return list(block.findall("datasource")) if block is not None else []


def _has_relation(ds: Any) -> bool:
    connection = ds.find("connection")
    return connection is not None and connection.find("relation") is not None


def _finding_for(ds: Any) -> Finding:
    name = (ds.get("caption") or ds.get("name") or "(이름 없음)").strip("[]")
    return Finding(
        severity=Severity.ERROR,
        rule_id=DatasourceShapeRule.id,
        location=str(ds.getroottree().getpath(ds)),
        line=ds.sourceline,
        message=(
            f"데이터 원본 `{name}`에 `<object-graph>`가 없다 — "
            "파일은 열리지만 데이터 원본 탭을 클릭하면 Tableau가 즉시 종료된다"
        ),
        fix=(
            "`</datasource>` 앞에 `<object-graph>`를 넣고 `<connection>`의 "
            "`<relation>`을 `<objects><object><properties context=''>` 아래에 "
            "그대로 복제한다 (레시피 21 §⑤)."
        ),
    )
