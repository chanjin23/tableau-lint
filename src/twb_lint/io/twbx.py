"""`.twbx` unpack/pack [C1].

`.twbx` = ZIP(`.twb` XML + `.hyper`/기타 바이너리). unpack/pack 시 `.hyper`
바이너리는 **무손실 보존**해야 한다 (재압축·재인코딩 금지).

스캐폴딩 단계 = 시그니처만. 구현 단계에서 `zipfile` 기반으로 채운다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Unpacked:
    """unpack 결과."""

    twb_path: Path
    """추출된 .twb 경로."""

    root: Path
    """추출 루트 디렉토리 (.hyper 등 포함)."""


def unpack(path: Path, dest: Path) -> Unpacked:
    """`.twbx`를 dest에 풀어 `.twb`와 부속 파일을 얻는다.

    `.twb` 입력이면 그대로 감싸 반환한다.
    """
    raise NotImplementedError("scaffold: twbx.unpack")


def pack(root: Path, out: Path) -> Path:
    """디렉토리를 `.twbx`로 다시 묶는다 (.hyper 무손실)."""
    raise NotImplementedError("scaffold: twbx.pack")
