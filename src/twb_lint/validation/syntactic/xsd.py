"""L-A: 공식 XSD 구문 검증.

`source-build` → 릴리스 매칭 XSD(vendored) → **fcp 접두사 정규화** → lxml XMLSchema 검증.
미지원 릴리스는 조용히 통과시키지 말고 WARNING을 낸다.

전처리가 L-A의 실질이다 — 공식 XSD를 그대로 쓰면 정상 파일 9/9가 실패한다
(docs/05-xsd-spike.md):

1. import 스텁 주입 + 과엄격 패치 → vendoring 시점 (tools/vendor_schemas.py)
2. `_.fcp.<기능>.<true|false>...<이름>` 접두사 제거 → **검증 직전, 트리 사본에서**
   (요소 태그와 속성 키 양쪽. 원본 트리는 불변)

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
        # 구현: release = config.release_from_source_build(model.source_build)
        #       → config.xsd_path(release)로 XSD 로드 → fcp 정규화 → 검증 → findings.
        #       release 미지원이면 WARNING 1건 (조용히 통과 금지).
        return []
