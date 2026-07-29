"""골든셋 회귀 — AC7(거짓양성 0)과 C4(`.hyper` 무손실)의 측정 지점.

**정상본 회귀가 1번이다.** v1.0 설계는 고장본 검출(AC2)부터 봤지만, 실측 결과
정상본 오탐이 먼저 터지는 문제임이 드러났다(전처리 없으면 9/9 실패) — docs/03-design.md D7.

골든셋은 저장소에 없다. 사내 재무 데이터라 커밋할 수 없다 (tests/conftest.py 참조).
`TWB_LINT_GOLDEN_NORMAL`이 없으면 이 파일의 테스트는 전부 skip 된다.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import pytest
from lxml import etree

from twb_lint import config, fcp
from twb_lint.io import safety
from twb_lint.validation import engine


def test_ac7_no_errors_on_known_good_workbooks(require_golden_normal: list[Path]) -> None:
    """AC7 — 정상 워크북에서 ERROR 0건.

    여기서 깨지면 **파일이 아니라 규칙을 의심한다.** 거짓 ERROR 1건이 게이트를
    무력화하고, 사용자가 게이트를 끄는 순간 프로젝트 목적이 사라진다 (02 S1-6).
    """
    offenders: list[str] = []
    for path in require_golden_normal:
        report = engine.validate(path)
        if report.errors:
            first = report.errors[0]
            offenders.append(f"{path.name}: [{first.rule_id}] {first.message}")
    assert not offenders, "정상본에서 ERROR가 났다 (AC7 위반):\n" + "\n".join(offenders)


def test_warning_counts_are_recorded(
    require_golden_normal: list[Path], record_property: object
) -> None:
    """WARNING은 허용하되 **건수를 기록**한다 — 경고 인플레이션 방지 (02 S4 AC7)."""
    total = 0
    for path in require_golden_normal:
        report = engine.validate(path)
        total += len(report.findings) - len(report.errors)
    record_property("golden_warning_count", total)  # type: ignore[operator]


def test_vendored_xsd_accepts_every_known_good_twb(require_golden_normal: list[Path]) -> None:
    """L-A 직접 회귀 — vendored XSD + fcp 정규화로 정상본이 통과하는가.

    `xsd.schema` 규칙 구현 **전에도** 돈다. 전처리 3단계가 살아 있는지를 규칙과 분리해
    확인하는 지점이라, vendoring을 갱신했을 때 여기가 먼저 알려준다 (03 D7 6번).
    """
    xsd_path = config.xsd_path("2026.1")
    assert xsd_path is not None, "vendored XSD가 없다 — tools/vendor_schemas.py를 돌린다"
    schema = etree.XMLSchema(etree.parse(str(xsd_path)))
    parser = safety.make_parser()

    failures: list[str] = []
    for path in require_golden_normal:
        root = _load_twb_root(path, parser)
        if root is None:
            continue
        normalized = fcp.normalize_tree(root)
        if not schema.validate(normalized.getroottree()):
            first = schema.error_log[0]
            failures.append(f"{path.name}: line {first.line} {first.message[:120]}")
    assert not failures, "vendored XSD가 정상본을 거부했다:\n" + "\n".join(failures)


def test_inspector_extracts_a_non_empty_model_from_every_workbook(
    require_golden_normal: list[Path], tmp_path: Path
) -> None:
    """인스펙터 실파일 회귀 — 추출이 조용히 비어도 게이트는 green이다.

    규칙은 모델만 본다. 추출 경로가 하나 어긋나면 findings가 0건이 되고 그것이
    "문제없음"처럼 보인다 (02 S5의 실체). 여기서 최소 사실만 고정한다.

    `zone ⊆ worksheets`와 `viewpoint ⊇ zone`은 규칙 ③이 정상본에서 침묵해야 한다는
    뜻이다 — 실측 10/10이 이 관계를 만족한다. 깨지면 규칙 ③이 AC7을 위반한다.
    """
    from twb_lint import inspect as inspector

    for i, path in enumerate(require_golden_normal):
        model = inspector.inspect(path, tmp_path / str(i))
        assert model.source_build, f"{path.name}: source-build가 없다 (XSD 선택 키)"
        assert model.manifest_features, f"{path.name}: 매니페스트가 비었다"
        assert model.datasources, f"{path.name}: 데이터소스가 비었다"
        assert model.worksheets, f"{path.name}: 워크시트가 비었다"
        for dash in model.dashboards.values():
            placed = set(dash.sheet_zones)
            assert placed <= model.worksheets, f"{path.name}/{dash.name}: 존이 시트를 벗어난다"
            assert placed <= dash.viewpoints, f"{path.name}/{dash.name}: viewpoint 누락"


@pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="io.twbx.unpack/pack 미구현 — 구현되면 XPASS로 바뀌고 이 마커를 제거한다",
)
def test_c4_hyper_survives_a_roundtrip_byte_for_byte(
    require_golden_normal: list[Path], tmp_path: Path
) -> None:
    """C4 — unpack→pack 라운드트립에서 `.hyper`가 **바이트 단위로 동일**해야 한다.

    원칙(02 S1·07 G6)만 있고 측정 기준이 없었다 (docs/TODO C4). 재압축·재인코딩이
    한 번이라도 끼면 추출 데이터가 조용히 달라지므로 등가성이 아니라 **동일성**으로 고정한다.
    """
    from twb_lint.io import twbx

    source = next((p for p in require_golden_normal if p.suffix.lower() == ".twbx"), None)
    if source is None:
        pytest.skip("골든셋에 .twbx가 없다")

    before = _hyper_bytes(source)
    unpacked = twbx.unpack(source, tmp_path / "unpacked")
    repacked = twbx.pack(unpacked.root, tmp_path / "repacked.twbx")

    assert _hyper_bytes(repacked) == before


def _load_twb_root(path: Path, parser: Any) -> Any:
    """`.twb`/`.twbx`에서 루트 element를 얻는다 (테스트 전용 최소 로더)."""
    if path.suffix.lower() == ".twb":
        return etree.parse(str(path), parser).getroot()
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".twb")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return etree.parse(fh, parser).getroot()


def _hyper_bytes(twbx_path: Path) -> dict[str, bytes]:
    """`.twbx` 안 `.hyper` 엔트리의 내용 (경로 → 바이트)."""
    with zipfile.ZipFile(twbx_path) as zf:
        return {
            name: zf.read(name) for name in zf.namelist() if name.lower().endswith(".hyper")
        }
