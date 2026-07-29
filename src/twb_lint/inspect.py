"""구조 인스펙터 [C2] — .twb를 WorkbookModel + 파싱 트리로 추출.

검증 규칙과 (향후) 편집기가 공유하는 구조 모델을 만든다.
스캐폴딩 단계 = 최소 모델만 채워 파이프라인이 관통하게 한다.

**파싱은 여기서 딱 한 번 일어난다.** 규칙마다 재파싱하면 1MB XML × 규칙 수가 되어
AC5(속도)와 충돌한다 (docs/TODO A1). 그래서 `load_context()`가 트리와 모델을 함께 만들어
`ValidationContext`에 실어 넘긴다.
"""

from __future__ import annotations

from pathlib import Path

from twb_lint.io import safety, twbx
from twb_lint.models import WorkbookModel
from twb_lint.validation.context import ValidationContext


def inspect(source: Path, workdir: Path) -> WorkbookModel:
    """`.twb`/`.twbx`를 구조 모델로 추출한다 (MCP `twb_inspect`의 코어).

    스캐폴딩: unpack만 시도하고(가능하면) 빈 모델을 반환한다.

    구현 단계에서 채울 것:
    - `source_build`·`twb_version`·`original_version` — 루트 속성 3개.
      `source_build`가 XSD 선택 키다 (`twb_version`이 아니다 — docs/05-xsd-spike.md F4).
    - `manifest_features` — `<document-format-change-manifest>` 항목 (규칙 ⑥).
      **원문 그대로 담는다** — fcp 접두사를 벗기면 `.true...`/`.false...`가 구분되지 않는다
      (`twb_lint.fcp.manifest_items()` 참조).
    - `datasources` — 데이터소스별 필드/계산필드 (내부 name 기준, 규칙 ①②).
    - `worksheets`·`dashboards`·`worksheet_windows` — 참조 무결성 대조용 (규칙 ③).
    """
    ctx, _ = load_context(source, workdir)
    return ctx.model


def load_context(
    source: Path, workdir: Path
) -> tuple[ValidationContext, list[safety.InputProblem]]:
    """검증 1회분의 컨텍스트를 만든다 — **파싱은 여기서 한 번뿐이다.**

    Returns:
        `(컨텍스트, 입력 문제 목록)`. 문제 목록이 비어 있지 않으면 컨텍스트는 신뢰할 수
        없으며 엔진이 즉시 ERROR finding으로 바꿔 반환한다 (02 S5 — 예외를 던지지 않는다).

    스캐폴딩 단계에서는 `.twb` 트리를 아직 파싱하지 않으므로 `raw_tree`가 None이다.
    트리를 요구하는 규칙(L-A·⑥)은 None을 보고 **검사를 스킵하고 그 사실을 보고**해야 한다.
    """
    problems: list[safety.InputProblem] = []

    if source.suffix.lower() == ".twbx":
        # 구현 단계에서 실제 unpack (io/safety의 zip slip·zip bomb 정책 적용).
        try:
            unpacked = twbx.unpack(source, workdir)
            twb_path: Path | None = unpacked.twb_path
        except NotImplementedError:
            twb_path = None
    else:
        twb_path = source

    model = WorkbookModel(source=source, twb_path=twb_path)
    # raw_tree는 구현 단계에서 `io.twb.parse(twb_path)`(안전 파서)로 채운다.
    return ValidationContext(model=model, raw_tree=None), problems
