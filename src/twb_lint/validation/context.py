"""`ValidationContext` — 규칙 하나가 받는 입력 전부.

**왜 `check(model)`이 아닌가** (docs/03-design.md D3.5, docs/TODO A1):

1. 모델만 넘기면 트리가 필요한 규칙(L-A, 규칙 ⑥)이 1MB XML을 **각자 재파싱**한다.
   규칙 수에 비례해 파싱이 늘어 AC5(속도)와 정면으로 충돌한다.
2. 트리 **하나**를 넘겨도 부족하다. 규칙 ⑥-a는 fcp 정규화 **전** 원본을,
   L-A는 정규화 **후** 사본을 봐야 한다 — 정규화가 요소의 소속 기능을 지우기 때문이다
   (docs/05-xsd-spike.md F7 함의 2).

그래서 컨텍스트가 **두 트리를 분리해서** 갖고, 정규화 사본은 처음 요구될 때 한 번만 만든다.

컨텍스트는 규칙의 보고 창구이기도 하다 — `note_skip()`/`note_partial()`로 "검사하지
못했다"를 남기면 리포트의 `coverage`에 실린다. findings가 비었다는 사실만으로는
"문제없음"과 "검사 못 함"이 구분되지 않는다 (02 S5 "조용히 통과 금지").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from twb_lint import fcp
from twb_lint.models import CoverageNote, CoverageStatus, WorkbookModel


@dataclass(slots=True)
class ValidationContext:
    """규칙 실행 1회분의 입력 + 보고 창구.

    엔진이 파일당 하나를 만들어 모든 규칙에 **공유**한다. 규칙은 이 객체를 변경하지
    않는다 — 유일한 예외가 `_notes` 추가(보고)와 정규화 사본 캐시(계산 결과 재사용)다.
    """

    model: WorkbookModel
    """구조 모델 (C2 인스펙터 산출물). 대부분의 L-B 규칙은 이것만으로 충분하다."""

    raw_tree: Any | None = None
    """**정규화 전** 원본 lxml 트리. 규칙 ⑥-a(fcp 매니페스트)의 유일한 유효 입력.

    `None`이면 파싱되지 않았다는 뜻이다(입력 오류, 또는 트리가 필요 없는 호출).
    트리를 요구하는 규칙은 `None`일 때 검사를 **스킵하고 그 사실을 보고**해야 한다."""

    _normalized: Any | None = field(default=None, repr=False)
    _normalized_done: bool = field(default=False, repr=False)
    _notes: list[CoverageNote] = field(default_factory=list, repr=False)

    def normalized_tree(self) -> Any | None:
        """fcp 접두사를 벗긴 트리 사본 (L-A 입력). 원본이 없으면 None.

        최초 호출 때 한 번만 만들고 캐시한다 — 1MB XML 사본은 싸지 않다.
        """
        if not self._normalized_done:
            self._normalized = (
                None if self.raw_tree is None else fcp.normalize_tree(self.raw_tree)
            )
            self._normalized_done = True
        return self._normalized

    def note_skip(self, rule_id: str, reason: str, scope: str = "*") -> None:
        """이 규칙이 (해당 범위를) **검사하지 못했다**고 보고한다.

        예: 미지원 릴리스라 XSD가 없다 · 트리가 파싱되지 않았다 · 대응표에 없는 기능이다.
        """
        self._notes.append(
            CoverageNote(rule_id=rule_id, status=CoverageStatus.SKIPPED, scope=scope, reason=reason)
        )

    def note_partial(self, rule_id: str, reason: str, scope: str) -> None:
        """대상 일부만 검사했다고 보고한다.

        예: calc 하나가 파싱에 실패해 그 calc의 하위 검사만 건너뛴 경우 (02 S1-6).
        """
        self._notes.append(
            CoverageNote(rule_id=rule_id, status=CoverageStatus.PARTIAL, scope=scope, reason=reason)
        )

    def notes_for(self, rule_id: str) -> list[CoverageNote]:
        """특정 규칙이 남긴 보고. 엔진이 coverage를 조립할 때 쓴다."""
        return [n for n in self._notes if n.rule_id == rule_id]
