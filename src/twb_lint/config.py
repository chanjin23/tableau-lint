"""버전 매핑·경로 설정.

TWB version ↔ 공식 XSD / 함수 화이트리스트 파일 매핑을 한 곳에서 관리한다.
새 Tableau 버전 대응 = 여기 매핑 + data/ 파일 추가.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

# TWB version("26.1") → XSD 파일명. 신버전은 여기에 추가.
XSD_BY_VERSION: dict[str, str] = {
    "26.1": "twb_2026.1.0.xsd",
    "26.2": "twb_2026.2.0.xsd",
}

# TWB version → 함수 화이트리스트 파일명.
FUNCTIONS_BY_VERSION: dict[str, str] = {
    "26.1": "functions_2026.1.json",
    "26.2": "functions_2026.2.json",
}


def data_dir(name: str) -> Path:
    """패키지 내 data 하위 디렉토리 경로 (schemas | functions)."""
    return Path(str(files("twb_lint").joinpath("data", name)))


def xsd_path(twb_version: str) -> Path | None:
    """버전에 맞는 vendored XSD 경로. 미지원 버전이면 None."""
    fname = XSD_BY_VERSION.get(twb_version)
    if fname is None:
        return None
    path = data_dir("schemas") / fname
    return path if path.exists() else None


def functions_path(twb_version: str) -> Path | None:
    """버전에 맞는 함수 화이트리스트 경로. 미지원 버전이면 None."""
    fname = FUNCTIONS_BY_VERSION.get(twb_version)
    if fname is None:
        return None
    path = data_dir("functions") / fname
    return path if path.exists() else None
