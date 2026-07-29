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

from functools import lru_cache
from typing import Any

from twb_lint import config
from twb_lint.io import safety
from twb_lint.models import Finding, Severity
from twb_lint.validation.context import ValidationContext
from twb_lint.validation.registry import register
from twb_lint.validation.rule import RuleBase, Stage

MAX_FINDINGS = 200
"""한 파일에서 낼 L-A finding 상한.

XSD가 어긋나기 시작하면 오류가 수천 건까지 간다 — 전부 실으면 리포트가 못 읽는 물건이
되고, 소비자가 AI라 앞의 몇 건이 묻힌다. 잘린 사실은 `note_partial`로 **반드시 보고한다**
(조용히 자르면 "이게 전부"로 읽힌다 — 02 S5)."""

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


@lru_cache(maxsize=4)
def load_schema(xsd_path: str) -> Any:
    """vendored XSD를 컴파일한 `XMLSchema`. **경로 기준으로 캐시한다.**

    MCP 서버는 상주 프로세스라 검증 호출마다 재컴파일하면 그 비용이 매 호출에 실린다
    (26MB급 스키마 컴파일은 싸지 않다 — TODO E1, AC5와 충돌). 릴리스 수가 손에 꼽으므로
    maxsize 4로 충분하다.

    ⚠️ 캐시된 `XMLSchema`는 **호출 간 공유**된다. lxml 스키마 객체는 스레드 안전이
    보장되지 않으므로, 서버를 멀티스레드로 돌릴 때는 여기에 락이 필요하다.
    """
    from lxml import etree

    return etree.XMLSchema(etree.parse(xsd_path, safety.make_parser()))


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

        path = config.xsd_path(release)
        if path is None:
            # 릴리스는 지원 목록에 있는데 파일이 없다 = 패키징 사고다. 파일의 문제가
            # 아니므로 ERROR가 아니다 (02 S1-6).
            ctx.note_skip(self.id, f"릴리스 {release}의 vendored XSD 파일이 없다")
            return [
                Finding(
                    severity=Severity.WARNING,
                    rule_id=self.id,
                    location="(vendored XSD)",
                    message=f"릴리스 {release}의 XSD를 찾지 못해 구문 검증을 건너뛴다",
                    fix="tools/vendor_schemas.py를 돌려 data/schemas를 채운다.",
                )
            ]

        schema = load_schema(str(path))
        # 정규화 사본을 본다 — fcp 접두사를 벗기지 않으면 정상본 9/9가 실패한다 (G2).
        # deepcopy는 `sourceline`을 보존하므로 오류의 줄번호는 **원본 .twb 기준**이다.
        normalized = ctx.normalized_tree()
        if normalized is None:  # raw_tree가 있으면 여기 오지 않는다 (위에서 걸렀다)
            ctx.note_skip(self.id, "정규화 트리를 만들지 못해 구문 검증을 하지 못했다")
            return []

        if schema.validate(normalized.getroottree()):
            return []

        # `error_log`는 다음 validate 호출에서 덮어쓰인다 — 즉시 스냅샷을 뜬다.
        errors = list(schema.error_log)
        if len(errors) > MAX_FINDINGS:
            ctx.note_partial(
                self.id,
                f"XSD 오류 {len(errors)}건 중 앞 {MAX_FINDINGS}건만 보고한다",
                scope="xsd-errors",
            )
            errors = errors[:MAX_FINDINGS]

        return [
            Finding(
                severity=severity_for(e.type_name, e.message),
                rule_id=self.id,
                location=e.path or "workbook",
                message=e.message,
                line=e.line or None,
            )
            for e in errors
        ]
