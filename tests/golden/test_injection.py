"""결함 주입 → 검출 (AC2) + 무거짓통과 실증 (AC3).

`tools/inject_defects.py`가 만든 고장본이 **실제로 고장인지**, 그리고 **어느 계층이
잡는지**를 확인한다. 여기서 드러나는 것이 이 프로젝트의 전제다:

- R4·R7 → L-A(XSD)가 잡는다
- R1a·R1b·R2·R3 → **L-A를 그대로 통과한다** = AC3 무거짓통과 위반의 실증.
  L-B 규칙이 없으면 이 파일들은 게이트를 통과하고 Tableau에서 열리지 않는다

골든셋이 없으면 skip 된다 (tests/conftest.py).
"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest
from lxml import etree

from twb_lint import config, fcp
from twb_lint.io import safety
from twb_lint.validation.syntactic.xsd import severity_for

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"

# L-A가 잡아야 하는 레시피 (XSD 위반) / L-B만 잡을 수 있는 레시피.
CAUGHT_BY_XSD = {"R4-datasource-child-order", "R7-param-domain-type-all"}
INVISIBLE_TO_XSD = {
    "R1a-drop-fcp-manifest-item",
    "R1b-drop-SortTagCleanup",
    "R2-drop-viewpoint",
    "R3-dangling-zone",
}

# L-A는 못 잡지만 **L-B 규칙 ③이 잡는** 레시피 (3자 대조).
CAUGHT_BY_NAMED_REFS = {"R2-drop-viewpoint", "R3-dangling-zone"}

# 규칙 ⑥-b가 잡는 레시피 (대응표 2쌍 중 하나).
CAUGHT_BY_MANIFEST = {"R1b-drop-SortTagCleanup"}

# 게이트를 통과하는 유일한 레시피. **의도된 상태다** — ⑥-a는 관계만 확인했고
# "항목을 지우면 실제로 로드가 거부된다"는 인과가 미검증이라 WARNING이다 (05 F7).
# 실험 A(TODO D)로 인과가 확정되면 ERROR로 올리고 이 테스트를 검출 단언으로 바꾼다.
WARNING_ONLY = {"R1a-drop-fcp-manifest-item"}


def _load_injector() -> Any:
    spec = importlib.util.spec_from_file_location(
        "twb_lint_inject_defects", TOOLS_DIR / "inject_defects.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def injector() -> Any:
    return _load_injector()


@pytest.fixture(scope="module")
def schema() -> etree.XMLSchema:
    path = config.xsd_path("2026.1")
    assert path is not None
    return etree.XMLSchema(etree.parse(str(path)))


@pytest.fixture
def broken_set(
    require_golden_normal: list[Path], injector: Any, tmp_path: Path
) -> dict[str, Path]:
    """정상본 1개에 전 레시피를 주입한 결과 (레시피 id → 산출 경로)."""
    source = next((p for p in require_golden_normal if p.suffix.lower() == ".twbx"), None)
    if source is None:
        pytest.skip("골든셋에 .twbx가 없다")

    made: dict[str, Path] = {}
    for recipe in injector.RECIPES:
        entry = injector.inject(source, recipe, tmp_path)
        if entry is not None:
            made[recipe.id] = tmp_path / str(entry["file"])
    if not made:
        pytest.skip("이 표본에 적용 가능한 레시피가 없다")
    return made


def test_every_recipe_is_caught_by_the_rule_it_declares(
    broken_set: dict[str, Path], injector: Any, require_golden_normal: list[Path]
) -> None:
    """레시피가 지목한 규칙이 **실제로** 그 결함을 잡는가 (AC2의 일반형).

    `CAUGHT_BY_*` 집합은 레시피가 늘 때마다 손으로 갱신해야 한다 — 갱신을 잊으면
    새 레시피가 아무 검사도 받지 않고 조용히 지나간다. 이 테스트는 레시피 목록
    자체를 입력으로 삼아 그 구멍을 막는다.

    대조군도 같이 본다: **주입 전 원본에는 그 규칙의 finding이 없어야 한다.**
    없으면 "규칙이 원래부터 그 파일에서 울고 있었다"와 구분되지 않는다.
    """
    from twb_lint.validation import engine

    source = next(p for p in require_golden_normal if p.suffix.lower() == ".twbx")
    baseline = {f.rule_id for f in engine.validate(source).findings}

    for recipe in injector.RECIPES:
        path = broken_set.get(recipe.id)
        if path is None:
            continue  # 이 표본에 해당 기능이 없다 — 주입 자체가 건너뛰어졌다
        assert recipe.rule not in baseline, (
            f"규칙 {recipe.rule}가 주입 전 원본에서도 울고 있다 — "
            f"{recipe.id}의 검출을 이 규칙 덕으로 돌릴 수 없다"
        )
        found = {f.rule_id for f in engine.validate(path).findings}
        assert recipe.rule in found, (
            f"{recipe.id}를 규칙 {recipe.rule}가 놓쳤다 (잡힌 것: {sorted(found)})"
        )


def _xsd_errors(path: Path, schema: etree.XMLSchema) -> list[Any]:
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".twb"))
        with zf.open(name) as fh:
            root = etree.parse(fh, safety.make_parser()).getroot()
    schema.validate(fcp.normalize_tree(root).getroottree())
    return list(schema.error_log)


def test_injection_preserves_hyper_bytes(
    broken_set: dict[str, Path], require_golden_normal: list[Path]
) -> None:
    """주입은 `.twb`만 건드린다 — `.hyper`는 바이트 그대로여야 한다 (02 S1 / 07 G6)."""
    source = next(p for p in require_golden_normal if p.suffix.lower() == ".twbx")

    def hypers(p: Path) -> dict[str, bytes]:
        with zipfile.ZipFile(p) as zf:
            return {n: zf.read(n) for n in zf.namelist() if n.lower().endswith(".hyper")}

    expected = hypers(source)
    for recipe_id, path in broken_set.items():
        assert hypers(path) == expected, f"{recipe_id}가 .hyper를 바꿨다"


def test_xsd_catches_syntax_level_defects(
    broken_set: dict[str, Path], schema: etree.XMLSchema
) -> None:
    """R4·R7은 L-A가 잡는다 — 그리고 A3 정책이 이를 ERROR로 등급 매긴다."""
    for recipe_id in CAUGHT_BY_XSD & broken_set.keys():
        errors = _xsd_errors(broken_set[recipe_id], schema)
        assert errors, f"{recipe_id}를 XSD가 놓쳤다"
        severities = {severity_for(e.type_name, e.message).value for e in errors}
        assert "error" in severities, f"{recipe_id}가 ERROR로 승격되지 않았다"


def test_xsd_is_blind_to_semantic_defects(
    broken_set: dict[str, Path], schema: etree.XMLSchema
) -> None:
    """**AC3 무거짓통과의 실증** — 이 고장본들은 L-A를 그대로 통과한다.

    L-B 규칙 ③·⑥이 없으면 게이트가 이 파일들을 승인하고, Tableau는 열지 못한다.
    이 테스트가 깨지는 날(= XSD가 잡게 되는 날)에는 규칙 배치를 다시 검토한다.
    """
    for recipe_id in INVISIBLE_TO_XSD & broken_set.keys():
        errors = _xsd_errors(broken_set[recipe_id], schema)
        assert not errors, (
            f"{recipe_id}를 XSD가 잡았다 — L-B 규칙의 존재 근거가 바뀌었을 수 있다"
        )


def test_xsd_recipes_now_fail_the_gate(broken_set: dict[str, Path]) -> None:
    """AC2 부분 측정 — R4·R7은 게이트가 **막는다**.

    `test_xsd_catches_syntax_level_defects`는 스키마를 직접 태워 확인한다. 여기서는
    같은 사실이 **엔진을 통과해** 게이트 판정까지 도달하는지를 본다 — 규칙 배선이
    빠지면 앞 테스트만 통과하고 게이트는 조용히 승인한다.
    """
    from twb_lint.validation import engine

    for recipe_id in CAUGHT_BY_XSD & broken_set.keys():
        report = engine.validate(broken_set[recipe_id])
        assert not report.passed, f"{recipe_id}가 게이트를 통과했다"
        assert any(f.rule_id == "xsd.schema" for f in report.errors), (
            f"{recipe_id}를 막은 것이 L-A가 아니다"
        )


def test_named_refs_catches_what_xsd_cannot(broken_set: dict[str, Path]) -> None:
    """**AC3 무거짓통과의 해소** — XSD가 원리적으로 못 잡는 것을 규칙 ③이 막는다.

    R2·R3는 이름 대조라 문법으로는 판정할 수 없다. 이 둘이 게이트를 통과하던 것이
    이 프로젝트의 존재 이유였다.
    """
    from twb_lint.validation import engine

    for recipe_id in CAUGHT_BY_NAMED_REFS & broken_set.keys():
        report = engine.validate(broken_set[recipe_id])
        assert not report.passed, f"{recipe_id}가 게이트를 통과했다"
        assert any(f.rule_id == "named.refs" for f in report.errors), (
            f"{recipe_id}를 막은 것이 규칙 ③이 아니다"
        )


def test_manifest_gate_catches_the_mapped_recipe(broken_set: dict[str, Path]) -> None:
    """R1b — 대응표에 있는 쌍(`manual-sort` ↔ `SortTagCleanup`)은 ERROR다.

    XSD는 `manual-sort`를 무조건 허용한다. 이 파일이 L-A를 통과하고 Tableau에서
    열리지 않는 것이 규칙 ⑥의 존재 이유다 (05 F5).
    """
    from twb_lint.validation import engine

    for recipe_id in CAUGHT_BY_MANIFEST & broken_set.keys():
        report = engine.validate(broken_set[recipe_id])
        assert not report.passed, f"{recipe_id}가 게이트를 통과했다"
        assert any(f.rule_id == "manifest.gates" for f in report.errors)


@pytest.mark.stub
def test_fcp_recipe_warns_but_does_not_block(broken_set: dict[str, Path]) -> None:
    """R1a — **의도적으로 WARNING이다.** 관계는 표본 10/10에서 확인했지만, 항목을
    지우면 실제로 로드가 거부되는지(인과)는 확인하지 못했다.

    실험 A(TODO D)로 인과가 확정되면 ERROR로 올린다 — 그때 이 테스트를 검출 단언으로
    바꾼다. 지금 ERROR로 올리면 우리 추론이 남의 정상 파일을 막는다.
    """
    from twb_lint.validation import engine

    for recipe_id in WARNING_ONLY & broken_set.keys():
        report = engine.validate(broken_set[recipe_id])
        assert report.passed is True, f"{recipe_id}가 이제 막힌다 — 검출 단언으로 바꾼다"
        assert any(f.rule_id == "manifest.gates" for f in report.findings), (
            f"{recipe_id}에 대해 규칙 ⑥이 아무 말도 하지 않았다"
        )
