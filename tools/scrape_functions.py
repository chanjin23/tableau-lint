"""help.tableau.com 함수 레퍼런스 → 버전별 화이트리스트 JSON 생성.

공식 machine-readable 목록이 **없다.** HTML을 1회 스크랩해 JSON으로 고정하고,
재스크랩은 사람이 명시적으로 돌린다 (HTML 구조 변경에 취약하므로 CI에 넣지 않는다).

산출: `src/twb_lint/data/functions/functions_<릴리스>.json`

**이 목록은 완전하지 않아도 된다.** 규칙 ①은 목록에 없는 함수를 만나면 ERROR가 아니라
WARNING을 낸다 — "그런 함수가 없다"가 아니라 "**우리 목록이 불완전하다**"가 더 그럴듯한
해석이기 때문이다 (docs/02-specification.md S1-6). 그래서 추출은 **관대한 쪽**으로 튼다:
빠뜨리면 노이즈가 늘고, 여분이 있으면 검출력만 조금 준다. 둘 다 게이트를 무력화하지 않는다.

추출 전략 (2026-07-29 실측):
- 페이지의 `<a name="ABS">` 앵커가 레퍼런스 항목이다 — 151개. 다만 **불완전하다**:
  `WINDOW_SUM`은 앵커가 `WINDOW`로 잘려 있고 `RANK_DENSE`는 앵커가 아예 없다
- 그래서 본문 텍스트의 `NAME(` 시그니처도 함께 걷고, 둘을 합집합한다
- 합집합에 섞여 드는 비함수 토큰(`NULL`·`TRUE`·`AGG` 등)만 명시적 블랙리스트로 뺀다

사용:
```bash
.venv/Scripts/python tools/scrape_functions.py                # 2026.1 생성
.venv/Scripts/python tools/scrape_functions.py --diff         # 기존 JSON과 차이만 출력
```
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "twb_lint" / "data" / "functions"

HELP_BASE = "https://help.tableau.com/current/pro/desktop/en-us"

# 긁을 페이지. 404는 건너뛴다 — Tableau가 페이지를 재편해도 나머지로 계속 돈다.
PAGES = (
    "functions_all_alphabetical.htm",
    "functions_all_categories.htm",
    "functions_functions_aggregate.htm",
    "functions_functions_tablecalculation.htm",
    "functions_functions_logical.htm",
    "functions_functions_string.htm",
    "functions_functions_date.htm",
    "functions_functions_number.htm",
    "functions_functions_typeconversion.htm",
    "functions_functions_userfunctions.htm",
    "functions_functions_spatial.htm",
    "functions_functions_passthrough.htm",
    "functions_functions_analytics.htm",
)

ANCHOR_RE = re.compile(r'<a[^>]*name="([A-Z][A-Z0-9_]{1,40})"')
SIGNATURE_RE = re.compile(r"\b([A-Z][A-Z0-9_]{1,40})\s*\(")
TAG_RE = re.compile(r"<[^>]+>")

NON_FUNCTIONS = frozenset(
    {
        # 리터럴·타입 키워드 — 함수 호출처럼 보이지만 함수가 아니다
        "TRUE",
        "FALSE",
        "NULL",
        # 문서 본문에 등장하는 약어
        "AGG",
        "PDA",
        "SQL",
        "API",
        "CSV",
        "URL",
        "JSON",
        "XML",
        "UTC",
        "LOD",
        "ISO",
        "ICU",
        "JWT",
        "HTML",
        "REST",
    }
)
"""합집합에 섞여 드는 비함수 토큰. **짧게 유지한다** — 여기에 진짜 함수를 넣으면
규칙 ①이 정상 워크북에 WARNING을 낸다."""


def fetch(page: str) -> str | None:
    """페이지 HTML. 없으면 None (404 등은 조용히 건너뛴다)."""
    req = urllib.request.Request(
        f"{HELP_BASE}/{page}", headers={"User-Agent": "twb-lint/vendoring"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 — 고정 https
            raw: bytes = resp.read()
    except OSError:
        return None
    return raw.decode("utf-8", errors="replace")


def extract(html: str) -> set[str]:
    """한 페이지에서 함수 이름 후보를 뽑는다 (앵커 ∪ 시그니처)."""
    anchors = set(ANCHOR_RE.findall(html))
    text = html_mod.unescape(TAG_RE.sub(" ", html))
    signatures = set(SIGNATURE_RE.findall(text))
    return (anchors | signatures) - NON_FUNCTIONS


def scrape(release: str) -> dict[str, Any]:
    """전 페이지를 긁어 화이트리스트 JSON 구조를 만든다."""
    found: set[str] = set()
    sources: list[str] = []
    for page in PAGES:
        html = fetch(page)
        if html is None:
            continue
        names = extract(html)
        if names:
            sources.append(page)
            found |= names

    if not found:
        raise RuntimeError("함수를 하나도 추출하지 못했다 — 네트워크 또는 페이지 구조를 확인한다")

    return {
        "release": release,
        "functions": sorted(found),
        "count": len(found),
        "provenance": {
            "base": HELP_BASE,
            "pages": sources,
            "strategy": "앵커(<a name=…>) ∪ 본문 시그니처(NAME() 패턴) − 비함수 블랙리스트",
            "note": (
                "완전성은 보장되지 않는다. 규칙 ①은 목록에 없는 함수를 ERROR가 아니라 "
                "WARNING으로 처리하므로(02 S1-6) 누락은 노이즈일 뿐 게이트를 무력화하지 않는다."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tableau 함수 화이트리스트를 생성한다")
    parser.add_argument("--release", default="2026.1", help="릴리스 키 (기본 2026.1)")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="산출 디렉토리")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="파일을 쓰지 않고 기존 JSON과의 차이만 출력한다",
    )
    args = parser.parse_args(argv)

    try:
        data = scrape(args.release)
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    out_path = args.out / f"functions_{args.release}.json"
    new: set[str] = set(data["functions"])

    if args.diff:
        if not out_path.exists():
            print(f"기존 파일 없음 ({out_path}) — 신규 {len(new)}개")
            return 0
        old = set(json.loads(out_path.read_text(encoding="utf-8"))["functions"])
        added, removed = sorted(new - old), sorted(old - new)
        print(f"추가 {len(added)}: {added}")
        print(f"삭제 {len(removed)}: {removed}")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 콘솔 인코딩(cp949)에서 죽지 않도록 ASCII로만 보고한다.
    print(
        f"OK   {args.release}: {out_path.name} "
        f"functions={len(new)} pages={len(data['provenance']['pages'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
