"""`.twb` XML 파싱/직렬화.

철칙: **문자열 편집 금지.** 항상 파싱된 트리(lxml)를 다룬다.

스캐폴딩 단계 = 시그니처만. 구현 단계에서 lxml로 채운다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse(twb_path: Path) -> Any:
    """`.twb`를 lxml 트리로 파싱해 루트 element를 반환한다."""
    raise NotImplementedError("scaffold: twb.parse")


def read_version(twb_path: Path) -> str | None:
    """`<workbook version=...>` 값을 읽는다 (XSD 버전 매칭용)."""
    raise NotImplementedError("scaffold: twb.read_version")


def serialize(root: Any, out: Path) -> Path:
    """트리를 `.twb`로 직렬화한다."""
    raise NotImplementedError("scaffold: twb.serialize")
