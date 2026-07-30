"""vendored 데이터가 실제로 쓸 수 있는 상태인지 — XSD·함수목록·매니페스트 대응표.

`data/`에 파일이 **있다**는 것과 **로드된다**는 것은 다르다. XSD는 컴파일되지 않으면
아무 소용이 없고, 컴파일 실패는 규칙을 구현한 뒤에야 드러난다. 여기서 먼저 잡는다.
"""

from __future__ import annotations

import json

from lxml import etree

from twb_lint import config


def test_vendored_xsd_exists_and_compiles() -> None:
    """공식 XSD는 **그대로는 컴파일되지 않는다** — 스텁 주입이 살아 있는지 확인한다 (05 F1)."""
    path = config.xsd_path("2026.1")
    assert path is not None, "vendored XSD가 없다 — tools/vendor_schemas.py를 돌린다"
    etree.XMLSchema(etree.parse(str(path)))  # 예외가 나면 vendoring이 깨진 것이다


def test_vendored_xsd_has_the_overstrict_patch() -> None:
    """`explain-data`가 필수로 남아 있으면 정상본이 파일당 1건씩 거짓 오류를 낸다 (05 F3)."""
    path = config.xsd_path("2026.1")
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert '<xs:element minOccurs="0" name="explain-data">' in text
    assert '<xs:element name="explain-data">' not in text


def test_stub_schemas_are_shipped_alongside() -> None:
    """import 스텁 2개가 XSD 옆에 없으면 schemaLocation이 풀리지 않는다."""
    schemas = config.data_dir("schemas")
    assert (schemas / "user-stub.xsd").exists()
    assert (schemas / "xml-stub.xsd").exists()
    assert (schemas / "NOTICE").exists(), "Apache-2.0 출처 표기가 필요하다"


def test_function_whitelist_loads_and_covers_common_functions() -> None:
    """규칙 ①의 전제. 없으면 규칙이 전량 WARNING을 낸다."""
    path = config.functions_path("2026.1")
    assert path is not None, "함수 목록이 없다 — tools/scrape_functions.py를 돌린다"

    data = json.loads(path.read_text(encoding="utf-8"))
    functions = set(data["functions"])

    # 실파일에서 실제로 관측된 함수들 (docs/03-design.md D3.6 실측).
    assert {"SUM", "ZN", "IIF", "DATEDIFF", "WINDOW_SUM", "RUNNING_SUM"} <= functions
    # LOD 키워드도 수식 안에서 함수 토큰처럼 잡힌다.
    assert {"FIXED", "INCLUDE", "EXCLUDE"} <= functions


def test_function_whitelist_records_its_provenance() -> None:
    """스크랩 산출물은 출처가 없으면 갱신 시점에 신뢰할 수 없다."""
    path = config.functions_path("2026.1")
    assert path is not None
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["provenance"]["pages"]
    assert data["release"] == "2026.1"


def test_manifest_gates_table_is_loadable() -> None:
    """규칙 ⑥-b의 대응표. 표에 있는 기능만 ERROR로 쓴다."""
    path = config.manifest_gates_path()
    assert path is not None
    data = json.loads(path.read_text(encoding="utf-8"))

    elements = {g["element"] for g in data["gates"]}
    assert {"manual-sort", "edit-group-action"} <= elements
    # 실측 쌍: manual-sort ↔ SortTagCleanup (05 F5)
    manual = next(g for g in data["gates"] if g["element"] == "manual-sort")
    assert manual["requires"] == ["SortTagCleanup"]
    # 2026-07-30 실측분 (MA_003 매출표 로드 거부 D2E8DA72)
    assert {"computed-sort", "edit-parameter-action", "clear-option"} <= elements
    computed = next(g for g in data["gates"] if g["element"] == "computed-sort")
    assert computed["requires"] == ["SortTagCleanup"], "sort 계열은 같은 항목이 게이팅한다"


def test_every_gate_records_its_symptom_and_source() -> None:
    """게이트는 ERROR를 낸다 — 근거 없는 항이 표에 들어오면 거짓 ERROR가 된다 (S1-6)."""
    path = config.manifest_gates_path()
    assert path is not None
    data = json.loads(path.read_text(encoding="utf-8"))

    for gate in data["gates"]:
        assert gate["requires"], gate["element"]
        assert gate["symptom"], gate["element"]
        assert gate["source"], gate["element"]


def test_unmapped_items_are_kept_separate_from_gates() -> None:
    """이름만 알고 대응 요소를 모르는 항목을 `gates`에 섞으면 추측 ERROR가 난다 (S1-6)."""
    path = config.manifest_gates_path()
    assert path is not None
    data = json.loads(path.read_text(encoding="utf-8"))

    gate_requirements = {req for g in data["gates"] for req in g["requires"]}
    unmapped = set(data["known_items_unmapped"]["items"])
    assert not (gate_requirements & unmapped), "대응 요소를 모르는 항목이 gates에 들어와 있다"
