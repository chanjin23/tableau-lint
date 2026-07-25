"""L-A: 공식 XSD 구문 검증.

`<workbook version>` → 버전 매칭 XSD(vendored) → lxml XMLSchema 검증.
미지원 버전은 조용히 통과시키지 말고 WARNING을 낸다.

스캐폴딩 = 등록 + no-op. 구현 단계에서 lxml.etree.XMLSchema로 채운다.
"""

from __future__ import annotations

from twb_lint.models import Finding, WorkbookModel
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage


@register
class XsdRule(RuleBase):
    id = "xsd.schema"
    stage = Stage.SYNTACTIC

    def check(self, model: WorkbookModel) -> list[Finding]:  # noqa: ARG002
        # 구현: config.xsd_path(model.twb_version)로 XSD 로드 → 검증 → findings.
        return []
