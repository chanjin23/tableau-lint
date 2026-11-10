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


def get(ref: str) -> tuple[str, str] | None:
    """레시피 식별자로 정확히 찾는다 — 파일명(`18-datasource-folders-palette.md`),
    확장자 뺀 이름, 번호(`18`) 중 무엇이든. 못 찾으면 None.

    키워드 검색(`find`)과 달리 **추측하지 않는다** — 식별자가 모호하면 None이다.
    """
    token = ref.strip().lower().removesuffix(".md")
    if not token:
        return None
    loaded = load_all()
    for name, content in loaded.items():
        stem = name.removesuffix(".md").lower()
        number = stem.split("-", 1)[0].lstrip("0")
        if token == stem or (token.isdigit() and number == token.lstrip("0")):
            return name, content
    return None


def find(query: str) -> tuple[str, str] | None:
    """질의어와 가장 잘 맞는 레시피 (파일명, 본문). 아무 항도 안 맞으면 None.

    순위: **질의어 토큰을 몇 종류 담았나**가 먼저, 그다음 점수(제목 줄에 있으면 크게,
    본문 등장 횟수만큼 작게). 한 단어만 수십 번 나오는 레시피가 질의어를 다 담은
    레시피를 이기지 않게 한다 — "상위 N 매개변수"가 매개변수 레시피(25)로 갔다.
    동점은 파일명 순으로 앞의 것 — 결정론 유지.

    **한 글자 영숫자 토큰은 세지 않는다** (`Top N`의 `n`). 부분 문자열로 세기 때문에
    `n`은 영어 단어마다 걸려 긴 레시피가 이긴다 — "상위 N"이 CSV 레시피(21)를 돌려줬다
    (2026-11-10). 그런 토큰만 있는 질의는 그대로 쓴다.
    """
    terms = [t.lower() for t in query.split() if t.strip()]
    if not terms:
        return None
    meaningful = [t for t in terms if not (len(t) == 1 and t.isascii() and t.isalnum())]
    terms = meaningful or terms
    best: tuple[tuple[int, int], str, str] | None = None
    for name, content in sorted(load_all().items()):
        lowered = content.lower()
        title = lowered.splitlines()[0] if lowered else ""
        covered = sum(1 for t in set(terms) if t in lowered)
        score = sum(10 * title.count(t) + lowered.count(t) for t in terms)
        rank = (covered, score)
        if score > 0 and (best is None or rank > best[0]):
            best = (rank, name, content)
    if best is None:
        return None
    return best[1], best[2]
