"""버전 매핑·경로 설정.

Tableau 릴리스 ↔ 공식 XSD / 함수 화이트리스트 파일 매핑을 한 곳에서 관리한다.
새 릴리스 대응 = 여기 매핑 + data/ 파일 추가.

**버전 키는 `source-build`다** (`<workbook version>`이 아니다).
`<workbook version>`은 저작 버전이 아니라 "이 버전 이상이면 열 수 있다"는 최소 호환
버전이며, 사용 기능들로부터 역산된다. Tableau 2026.1이 저장한 파일도 `version='18.1'`로
적히므로 XSD 선택에 쓸 수 없다. 실측: docs/05-xsd-spike.md F4.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

# `source-build` 앞부분에서 릴리스(YYYY.R)를 뽑는다.
# 예: "2026.1.1 (20261.26.0410.0924)" → "2026.1"
_RELEASE_RE = re.compile(r"^\s*(\d{4})\.(\d+)")

# Tableau 릴리스("2026.1") → vendored XSD 파일명.
# MVP 대상은 2026.1 단독 (docs/02-specification.md S7). 신 릴리스는 여기 추가.
XSD_BY_RELEASE: dict[str, str] = {
    "2026.1": "twb_2026.1.0.xsd",
}

# Tableau 릴리스 → 함수 화이트리스트 파일명.
FUNCTIONS_BY_RELEASE: dict[str, str] = {
    "2026.1": "functions_2026.1.json",
}


def release_from_source_build(source_build: str | None) -> str | None:
    """`source-build` 속성값에서 릴리스 키를 뽑는다.

    Args:
        source_build: `<workbook source-build>` 값 (예: "2026.1.1 (20261.26.0410.0924)").

    Returns:
        릴리스 키 (예: "2026.1"). 파싱 불가면 None.
    """
    if source_build is None:
        return None
    m = _RELEASE_RE.match(source_build)
    if m is None:
        return None
    return f"{m.group(1)}.{m.group(2)}"


def is_supported(release: str | None) -> bool:
    """해당 릴리스의 XSD 매핑이 있는지. 미지원이면 규칙이 명시 경고를 내야 한다."""
    return release is not None and release in XSD_BY_RELEASE


def data_dir(name: str) -> Path:
    """패키지 내 data 하위 디렉토리 경로 (schemas | functions)."""
    return Path(str(files("twb_lint").joinpath("data", name)))


def xsd_path(release: str | None) -> Path | None:
    """릴리스에 맞는 vendored XSD 경로. 미지원 릴리스거나 파일 부재면 None.

    vendored XSD는 원본 그대로가 아니다 — import 스텁 주입 + 과엄격 패치가 적용된
    산출물이다 (tools/vendor_schemas.py, docs/05-xsd-spike.md F1·F3).
    """
    if release is None:
        return None
    fname = XSD_BY_RELEASE.get(release)
    if fname is None:
        return None
    path = data_dir("schemas") / fname
    return path if path.exists() else None


def manifest_gates_path() -> Path | None:
    """기능↔매니페스트 대응표 경로 (규칙 ⑥). 파일 부재면 None.

    릴리스별로 갈리지 않는다 — 게이팅 관계 자체는 기능 도입 시점에 고정되기 때문이다.
    근거: docs/05-xsd-spike.md F5.
    """
    path = Path(str(files("twb_lint").joinpath("data", "manifest_gates.json")))
    return path if path.exists() else None


def functions_path(release: str | None) -> Path | None:
    """릴리스에 맞는 함수 화이트리스트 경로. 미지원이거나 파일 부재면 None."""
    if release is None:
        return None
    fname = FUNCTIONS_BY_RELEASE.get(release)
    if fname is None:
        return None
    path = data_dir("functions") / fname
    return path if path.exists() else None
