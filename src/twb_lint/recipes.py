"""저작 레시피 조회 — `docs/recipes/`를 코드에서 찾는다.

레시피의 SOR은 `docs/recipes/`다 (근거 커밋 sha가 붙은 실측 문서).
여기서는 찾아서 돌려줄 뿐 내용을 소유하지 않는다 — 문서를 고치면 그대로 반영된다.

경로는 저장소 체크아웃 기준이다 (editable install 전제, MCP 등록도 --directory 방식).
wheel로 설치하면 docs/가 없으므로 조회가 빈다 — 그때는 인덱스가 None이다.
"""

from __future__ import annotations

from pathlib import Path

_RECIPES_DIR = Path(__file__).resolve().parents[2] / "docs" / "recipes"

# 관리 문서 — 키워드 검색 대상에서 뺀다 (인덱스·원장·로그)
_NON_RECIPE = {"README.md", "00-inventory.md", "90-e2e-log.md"}


def recipes_dir() -> Path:
    """레시피 디렉토리 경로 (존재 보장 없음 — 호출자가 확인한다)."""
    return _RECIPES_DIR


def load_index() -> str | None:
    """매핑표(README.md) 본문. 없으면 None."""
    index = _RECIPES_DIR / "README.md"
    if not index.is_file():
        return None
    return index.read_text(encoding="utf-8")


def load_all() -> dict[str, str]:
    """레시피 파일명 -> 본문. 관리 문서는 제외."""
    if not _RECIPES_DIR.is_dir():
        return {}
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(_RECIPES_DIR.glob("*.md"))
        if p.name not in _NON_RECIPE
    }


def find(query: str) -> tuple[str, str] | None:
    """질의어와 가장 잘 맞는 레시피 (파일명, 본문). 아무 항도 안 맞으면 None.

    점수: 질의어 토큰이 제목 줄에 있으면 크게, 본문 등장 횟수만큼 작게.
    동점은 파일명 순으로 앞의 것 — 결정론 유지.
    """
    terms = [t.lower() for t in query.split() if t.strip()]
    if not terms:
        return None
    best: tuple[int, str, str] | None = None
    for name, content in load_all().items():
        lowered = content.lower()
        title = lowered.splitlines()[0] if lowered else ""
        score = sum(10 * title.count(t) + lowered.count(t) for t in terms)
        if score > 0 and (best is None or score > best[0]):
            best = (score, name, content)
    if best is None:
        return None
    return best[1], best[2]
