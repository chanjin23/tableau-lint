"""`twb_lint.recipes` — 저작 레시피 조회.

레시피의 SOR은 `docs/recipes/`다. 이 테스트는 저장소 체크아웃을 전제로
실제 문서를 읽는다 — 문서가 이사하면 여기가 먼저 깨져서 알려준다.
"""

from __future__ import annotations

from twb_lint import recipes


def test_index_is_the_mapping_table() -> None:
    index = recipes.load_index()
    assert index is not None
    assert "레시피" in index


def test_all_recipes_load_and_management_docs_are_excluded() -> None:
    loaded = recipes.load_all()
    assert "01-calc-field-create.md" in loaded
    # 관리 문서(인덱스·원장·로그)는 검색 대상이 아니다
    assert "README.md" not in loaded
    assert "00-inventory.md" not in loaded
    assert "90-e2e-log.md" not in loaded


def test_find_matches_the_obvious_recipe() -> None:
    hit = recipes.find("계산 필드 추가")
    assert hit is not None
    name, content = hit
    assert name == "01-calc-field-create.md"
    assert "calculation" in content


def test_find_matches_by_topic_keyword() -> None:
    hit = recipes.find("하이라이트 동작")
    assert hit is not None
    assert hit[0] == "08-action-highlight.md"


def test_find_returns_none_for_nonsense() -> None:
    """없는 주제에 아무 레시피나 돌려주면 '지어내지 않는다' 원칙이 깨진다."""
    assert recipes.find("qqqqzzzz") is None
    assert recipes.find("   ") is None
