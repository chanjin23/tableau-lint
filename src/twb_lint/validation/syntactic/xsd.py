"""L-A: 공식 XSD 구문 검증.

`source-build` → 릴리스 매칭 XSD(vendored) → **fcp 접두사 정규화** → lxml XMLSchema 검증.
미지원 릴리스는 조용히 통과시키지 말고 스킵을 보고한다.

전처리가 L-A의 실질이다 — 공식 XSD를 그대로 쓰면 정상 파일 9/9가 실패한다
(docs/05-xsd-spike.md):

1. import 스텁 주입 + 과엄격 패치 → vendoring 시점 (tools/vendor_schemas.py)
2. `_.fcp.<기능>.<true|false>...<이름>` 접두사 제거 → **검증 직전, 트리 사본에서**
   (`ctx.normalized_tree()`. 원본은 규칙 ⑥-a가 쓰므로 불변)

스캐폴딩 = 등록 + 입력 확인 + **심각도 정책 확정**. 검증 호출만 구현 단계에 남는다.
"""

from __future__ import annotations

from twb_lint import config
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

# --- A3. L-A 위반의 심각도 정책 (2026-07-29 실측으로 확정) ---------------------------
#
# 왜 "XSD 위반 = 전부 ERROR"가 아닌가: `explain-data`가 이미 **XSD가 실제 Tableau보다
# 엄격하다**는 실증이다 (05 F3). 표본 9개로 못 걸른 과엄격이 더 있으면 전부 ERROR로 낼 때
# AC7(정상본 ERROR 0건)이 무너진다.
#
# 실측으로 판별 기준을 정했다. lxml `error_log`의 `type_name`을 찍어 보면:
#
#   enum 위반          SCHEMAV_CVC_ENUMERATION_VALID (1840)
#   datatype 위반      SCHEMAV_CVC_DATATYPE_VALID_1_2_1 (1824)
#   미지/오위치 요소   SCHEMAV_ELEMENT_CONTENT (1871) "... This element is not expected."
#   필수 자식 누락     SCHEMAV_ELEMENT_CONTENT (1871) "... Missing child element(s)."
#                      ^^^^^ explain-data 거짓양성이 정확히 이것이다
#
# **거짓양성과 진짜 오류가 같은 type_name을 쓴다.** 그래서 type_name만으로는 가를 수 없고
# 메시지 본문을 함께 본다. libxml2 메시지는 영어로 고정돼 있어 매칭이 성립한다.

CONFIRMED_ERROR_TYPES = frozenset(
    {
        "SCHEMAV_CVC_ENUMERATION_VALID",
        "SCHEMAV_CVC_DATATYPE_VALID_1_2_1",
        "SCHEMAV_CVC_DATATYPE_VALID_1_2_2",
        "SCHEMAV_CVC_DATATYPE_VALID_1_2_3",
        "SCHEMAV_CVC_LENGTH_VALID",
        "SCHEMAV_CVC_MINLENGTH_VALID",
        "SCHEMAV_CVC_MAXLENGTH_VALID",
        "SCHEMAV_CVC_PATTERN_VALID",
    }
)
"""값 자체가 스키마와 어긋나는 유형 — 실측상 로드 거부(D2E8DA72)로 직결된다.
`param-domain-type='all'`이 실제 사례다 (docs/06-rule-candidates.md R7)."""

MISSING_CHILD_MARKER = "Missing child element"
"""`SCHEMAV_ELEMENT_CONTENT` 안에서 **과엄격 위험 클래스**를 가르는 표지.

이 문구가 붙은 오류는 "스키마가 요구하는데 파일에 없다"이며, `explain-data`처럼
실제 Tableau는 요구하지 않는 경우가 실측으로 확인됐다 → WARNING."""

NOT_EXPECTED_MARKER = "This element is not expected"
"""같은 코드지만 반대 방향 — "파일에 있는데 스키마가 허용하지 않는다".
R4·R5·R6(자식 순서 위반)이 이 클래스이며 전부 실제 로드 거부로 확인됐다 → ERROR."""


def severity_for(type_name: str, message: str) -> Severity:
    """XSD 오류 1건의 심각도를 정한다 (A3 정책의 실행부).

    확신할 수 있는 유형만 ERROR, 나머지는 WARNING (02 S1-6). 분류가 애매하면
    **WARNING 쪽으로 떨어뜨린다** — 거짓 ERROR 1건이 게이트를 무력화하기 때문이다.
    """
    if type_name in CONFIRMED_ERROR_TYPES:
        return Severity.ERROR
    if NOT_EXPECTED_MARKER in message:
        return Severity.ERROR
    if MISSING_CHILD_MARKER in message:
        return Severity.WARNING
    return Severity.WARNING


@register
class XsdRule(RuleBase):
    id = "xsd.schema"
    stage = Stage.SYNTACTIC

    def check(self, ctx: ValidationContext) -> list[Finding]:
        release = config.release_from_source_build(ctx.model.source_build)

        # 미지원 릴리스에서 ERROR를 내면 안 된다 — 우리가 그 문법을 모른다는 뜻일 뿐이다.
        # 검증한 적 없는 릴리스에 정책을 적용하면 AC7이 그 릴리스에서 무너진다.
        if not config.is_supported(release):
            ctx.note_skip(
                self.id,
                "미지원 릴리스라 XSD 구문 검증을 하지 못했다 "
                f"(source-build={ctx.model.source_build!r})",
            )
            return [
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location="workbook/@source-build",
                    message=(
                        f"릴리스 {release or '(판별 불가)'}는 지원 대상이 아니다 — "
                        "구문 검증을 건너뛴다"
                    ),
                    fix=(
                        "config.XSD_BY_RELEASE에 해당 릴리스 XSD를 추가하고 "
                        "정상본 회귀를 다시 돌린다."
                    ),
                )
            ]

        if ctx.raw_tree is None:
            ctx.note_skip(self.id, "트리를 파싱하지 못해 구문 검증을 하지 못했다")
            return []

        # 구현: config.xsd_path(release)로 XMLSchema 로드(캐시) →
        #       schema.validate(ctx.normalized_tree()) →
        #       error_log의 각 error를 severity_for(e.type_name, e.message)로 등급 매겨
        #       Finding(line=e.line, location=e.path)로 변환.
        ctx.note_skip(self.id, "규칙 미구현 (스캐폴딩)")
        return []
