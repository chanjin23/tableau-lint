"""구조 인스펙터 [C2] — .twb를 WorkbookModel로 추출.

검증 규칙과 (향후) 편집기가 공유하는 구조 모델을 만든다.
스캐폴딩 단계 = 최소 모델만 채워 파이프라인이 관통하게 한다.
"""

from __future__ import annotations

from pathlib import Path

from twb_lint.io import twbx
from twb_lint.models import WorkbookModel


def inspect(source: Path, workdir: Path) -> WorkbookModel:
    """`.twb`/`.twbx`를 구조 모델로 추출한다.

    스캐폴딩: unpack만 시도하고(가능하면) 빈 모델을 반환한다.
    구현 단계에서 datasources/fields/calc/sheets/dashboards/참조를 채운다.
    """
    if source.suffix.lower() == ".twbx":
        # 구현 단계에서 실제 unpack. 스캐폴딩은 경로만 매단다.
        try:
            unpacked = twbx.unpack(source, workdir)
            twb_path: Path | None = unpacked.twb_path
        except NotImplementedError:
            twb_path = None
    else:
        twb_path = source

    return WorkbookModel(source=source, twb_path=twb_path)
