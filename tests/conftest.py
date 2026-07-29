r"""pytest 공용 설정 — 골든셋 경로 외부화 포함.

**골든셋을 저장소에 커밋하지 않는 이유는 용량이 아니라 기밀이다.**
정상 대조본 9개는 사내 재무 데이터(현금흐름·손익계산서)를 담은 실사용 워크북이다.
용량 문제는 주입 스크립트로 재생성 가능하게 만들어 해소했지만(03 D5), **원본 9개는
재생성할 수 없고 커밋해서도 안 된다.**

그래서 경로를 코드에 박지 않고 환경변수로 받는다. 값이 없으면 해당 테스트는 skip 된다 —
이 PC 밖에서도 나머지 테스트는 전부 돈다 (docs/TODO C1).

```bash
# bash
export TWB_LINT_GOLDEN_NORMAL='C:/dev/JW/2.개발/MA_002*/*.twbx;C:/dev/태블로판차분석*.twbx'
# PowerShell
$env:TWB_LINT_GOLDEN_NORMAL = 'C:\dev\JW\2.개발\MA_002*\*.twbx;C:\dev\태블로판차분석*.twbx'
```
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import pytest

GOLDEN_NORMAL_ENV = "TWB_LINT_GOLDEN_NORMAL"
"""정상 대조본 glob 목록. 구분자는 `;` (Windows 경로에 `:`가 들어가므로)."""

GOLDEN_BROKEN_ENV = "TWB_LINT_GOLDEN_BROKEN"
"""주입 고장본 디렉토리. `tools/inject_defects.py`의 산출 위치."""


def _resolve(env_name: str) -> list[Path]:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return []
    found: list[Path] = []
    for pattern in raw.split(";"):
        pattern = pattern.strip()
        if not pattern:
            continue
        found.extend(Path(p) for p in glob.glob(pattern))
    return sorted(p for p in found if p.is_file())


@pytest.fixture(scope="session")
def golden_normal() -> list[Path]:
    """정상 대조본 경로 목록. 환경변수가 없으면 빈 목록."""
    return _resolve(GOLDEN_NORMAL_ENV)


@pytest.fixture(scope="session")
def golden_broken() -> list[Path]:
    """주입 고장본 경로 목록. 환경변수가 없으면 빈 목록."""
    return _resolve(GOLDEN_BROKEN_ENV)


@pytest.fixture(scope="session")
def require_golden_normal(golden_normal: list[Path]) -> list[Path]:
    """정상 대조본이 필요한 테스트용 — 없으면 skip 한다."""
    if not golden_normal:
        pytest.skip(
            f"{GOLDEN_NORMAL_ENV}가 설정되지 않았다 — 정상본 회귀(AC7)를 건너뛴다. "
            "골든셋은 사내 재무 데이터라 저장소에 없다 (tests/conftest.py 참조)."
        )
    return golden_normal
