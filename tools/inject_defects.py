"""정상 워크북에 결함을 **하나씩** 주입해 고장본 골든셋을 만든다.

고장 파일이 남아 있지 않으므로(과거 산출물 미보존) 정상본에서 만들어 낸다.
레시피는 `docs/06-rule-candidates.md` §D의 실측 목록이며, 각 항목은
**"실제 Tableau에서 안 열림"이 과거에 관측된** 조건이다.

원칙 (docs/TODO D):
- **결함 1개씩** — 한 파일에 두 개를 넣으면 어느 쪽이 거부를 유발했는지 알 수 없다
- **복사본에만** — 원본 9개는 불가침이다. 이 스크립트는 입력을 절대 쓰지 않는다
- **결정론** — 같은 입력에 같은 산출. 골든셋을 언제든 재생성할 수 있다
- `.hyper`는 손대지 않는다 — `.twb` 엔트리만 교체하고 나머지는 바이트 그대로 복사한다

산출물과 함께 **라벨 대장**(`labels.json`)을 낸다. 사용자가 Tableau Desktop에서 한 배치로
열어 보고 결과를 채우면 그대로 AC2·AC3 측정 입력이 된다.

사용:
```bash
# 레시피 전부, 파일 1개에 대해
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리>

# 실험 B — 매니페스트 항목 16종을 하나씩 지운 파일들
.venv/Scripts/python tools/inject_defects.py --source <원본.twbx> --out <디렉토리> --experiment-b

# 목록만 보기
.venv/Scripts/python tools/inject_defects.py --list
```
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from twb_lint import fcp  # noqa: E402
from twb_lint.io import safety  # noqa: E402

Mutator = Callable[[Any], str | None]
"""트리를 제자리에서 변형하고, 무엇을 했는지 한 줄로 반환한다.
변형할 대상이 없으면 None을 반환한다 (그 표본에 해당 기능이 없다는 뜻)."""


@dataclass(frozen=True, slots=True)
class Recipe:
    """결함 주입 레시피 1건."""

    id: str
    rule: str
    """이 결함을 잡아야 하는 twb-lint 규칙 id (검출 측정용)."""

    expected: str
    """과거 실측에서 관측된 Tableau의 반응."""

    source: str
    mutate: Mutator


# --- 레시피 구현 ---------------------------------------------------------------------


def _manifest(root: Any) -> Any:
    for el in root.iter():
        if isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == fcp.MANIFEST_TAG:
            return el
    return None


def _drop_manifest_item(root: Any, predicate: Callable[[str], bool]) -> str | None:
    manifest = _manifest(root)
    if manifest is None:
        return None
    for child in list(manifest):
        if isinstance(child.tag, str) and predicate(child.tag):
            manifest.remove(child)
            return f"매니페스트 항목 '{child.tag}' 삭제"
    return None


def _r1a_drop_fcp_item(root: Any) -> str | None:
    """R1-a — fcp 매니페스트 항목만 삭제 (사용 요소는 유지). 실험 A와 같다."""
    used = sorted(fcp.features_in_tree(root))
    if not used:
        return None
    target = fcp.expected_manifest_item(used[0])
    return _drop_manifest_item(root, lambda tag: tag == target)


def _r1b_drop_sort_tag_cleanup(root: Any) -> str | None:
    """R1-b — `SortTagCleanup` 삭제. `<manual-sort>`는 그대로 둔다."""
    uses_manual_sort = any(
        isinstance(el.tag, str) and fcp.strip_prefix(el.tag) == "manual-sort" for el in root.iter()
    )
    if not uses_manual_sort:
        return None
    return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == "SortTagCleanup")


def _r2_drop_viewpoint(root: Any) -> str | None:
    """R2 — 대시보드 window의 viewpoint 1개 삭제 → 내부 오류 2805CF18."""
    for window in root.iter():
        if not isinstance(window.tag, str) or fcp.strip_prefix(window.tag) != "window":
            continue
        if window.get("class") != "dashboard":
            continue
        for vps in window:
            if not isinstance(vps.tag, str) or fcp.strip_prefix(vps.tag) != "viewpoints":
                continue
            children = list(vps)
            if not children:
                continue
            victim = children[0]
            vps.remove(victim)
            return (
                f"대시보드 '{window.get('name')}'의 viewpoint "
                f"'{victim.get('name')}' 삭제"
            )
    return None


def _r3_dangle_zone(root: Any) -> str | None:
    """R3 — 존의 `name`을 없는 시트로 바꾼다 → dangling 참조."""
    for zone in root.iter():
        if not isinstance(zone.tag, str) or fcp.strip_prefix(zone.tag) != "zone":
            continue
        name = zone.get("name")
        if not name:
            continue
        zone.set("name", f"{name}__twb_lint_dangling__")
        return f"zone name '{name}' → 존재하지 않는 시트로 변조"
    return None


def _r4_move_style_before_column(root: Any) -> str | None:
    """R4 — datasource 자식 순서 위반 → D2E8DA72."""
    for ds in root.iter():
        if not isinstance(ds.tag, str) or fcp.strip_prefix(ds.tag) != "datasource":
            continue
        def child(children: list[Any], tag: str) -> Any:
            return next(
                (c for c in children if isinstance(c.tag, str) and fcp.strip_prefix(c.tag) == tag),
                None,
            )

        children = list(ds)
        style = child(children, "style")
        column = child(children, "column")
        if style is None or column is None:
            continue
        ds.remove(style)
        ds.insert(list(ds).index(column), style)
        return f"datasource '{ds.get('name')}'에서 <style>을 첫 <column> 앞으로 이동"
    return None


def _r7_bad_enum(root: Any) -> str | None:
    """R7 — `param-domain-type='all'` (정답은 'any') → enum 위반, D2E8DA72."""
    for el in root.iter():
        if "param-domain-type" in el.attrib:
            old = el.attrib["param-domain-type"]
            el.attrib["param-domain-type"] = "all"
            return f"param-domain-type '{old}' → 'all' (열거형 밖)"
    return None


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        id="R1a-drop-fcp-manifest-item",
        rule="manifest.gates",
        expected="로드 거부 (미검증 — 실험 A가 확정한다)",
        source="docs/05-xsd-spike.md F7 / docs/06-rule-candidates.md R1-a",
        mutate=_r1a_drop_fcp_item,
    ),
    Recipe(
        id="R1b-drop-SortTagCleanup",
        rule="manifest.gates",
        expected="로드 거부: no declaration found for element 'manual-sort'",
        source="docs/05-xsd-spike.md F5 (함정 W2)",
        mutate=_r1b_drop_sort_tag_cleanup,
    ),
    Recipe(
        id="R2-drop-viewpoint",
        rule="named.refs",
        expected="내부 오류 2805CF18",
        source="docs/06-rule-candidates.md R2 (함정 S1)",
        mutate=_r2_drop_viewpoint,
    ),
    Recipe(
        id="R3-dangling-zone",
        rule="named.refs",
        expected="로드 거부 또는 존 렌더 실패",
        source="docs/06-rule-candidates.md R3",
        mutate=_r3_dangle_zone,
    ),
    Recipe(
        id="R4-datasource-child-order",
        rule="xsd.schema",
        expected="로드 거부 D2E8DA72 (element not allowed for content model)",
        source="docs/06-rule-candidates.md R4 (함정 W1)",
        mutate=_r4_move_style_before_column,
    ),
    Recipe(
        id="R7-param-domain-type-all",
        rule="xsd.schema",
        expected="로드 거부 D2E8DA72 (value 'all' not in enumeration)",
        source="docs/06-rule-candidates.md R7 (함정 B10)",
        mutate=_r7_bad_enum,
    ),
)


def experiment_b_recipes(items: list[str]) -> tuple[Recipe, ...]:
    """실험 B — 대응 요소를 모르는 매니페스트 항목을 하나씩 지운다.

    거부 메시지의 `no declaration found for element '<요소>'`가 **대응 요소를 직접
    알려준다.** 열리면 그 표본이 해당 기능을 안 쓴다는 뜻이며 그것도 정보다
    (docs/06-rule-candidates.md §D.1).
    """

    def make(item: str) -> Mutator:
        def mutate(root: Any) -> str | None:
            return _drop_manifest_item(root, lambda tag: fcp.strip_prefix(tag) == item)

        return mutate

    return tuple(
        Recipe(
            id=f"B-drop-{item}",
            rule="manifest.gates",
            expected="거부되면 메시지가 대응 요소를 알려준다 / 열리면 이 표본이 해당 기능 미사용",
            source="docs/06-rule-candidates.md §D.1 (실험 B)",
            mutate=make(item),
        )
        for item in items
    )


# --- 패키징 -------------------------------------------------------------------------


def _twb_entry(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if n.lower().endswith(".twb")]
    if not names:
        raise RuntimeError("아카이브에 .twb가 없다")
    return names[0]


def _write_twbx(source: Path, out: Path, new_twb: bytes) -> None:
    """`.twb`만 교체하고 나머지 엔트리는 **그대로** 복사한다.

    `.hyper`는 읽어서 다시 쓰지 않는다 — 압축 방식까지 원본 엔트리 정보를 따라간다
    (02 S1 무손실 원칙, 07 G6).
    """
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(out, "w") as dst:
        twb_name = _twb_entry(src)
        for info in src.infolist():
            data = new_twb if info.filename == twb_name else src.read(info.filename)
            # 원본 엔트리의 압축 방식·타임스탬프를 유지해 결정론을 지킨다.
            dst.writestr(info, data)


def _load_root(source: Path) -> tuple[Any, str | None]:
    """`.twb`/`.twbx`에서 루트와 (twbx면) 내부 엔트리 이름을 얻는다."""
    parser = safety.make_parser()
    if source.suffix.lower() == ".twb":
        return etree.parse(str(source), parser).getroot(), None
    with zipfile.ZipFile(source) as zf:
        name = _twb_entry(zf)
        with zf.open(name) as fh:
            return etree.parse(fh, parser).getroot(), name


def inject(source: Path, recipe: Recipe, out_dir: Path) -> dict[str, object] | None:
    """레시피 1건을 적용한 고장본을 만든다. 적용 대상이 없으면 None."""
    root, _ = _load_root(source)
    tree = root.getroottree()

    detail = recipe.mutate(root)
    if detail is None:
        return None

    payload = etree.tostring(tree, xml_declaration=True, encoding="utf-8")
    out_path = out_dir / f"{source.stem}__{recipe.id}{source.suffix}"

    if source.suffix.lower() == ".twbx":
        _write_twbx(source, out_path, payload)
    else:
        out_path.write_bytes(payload)

    return {
        "file": out_path.name,
        "recipe": recipe.id,
        "rule": recipe.rule,
        "injected": detail,
        "expected_tableau": recipe.expected,
        "source_doc": recipe.source,
        "origin": source.name,
        # 사용자가 Tableau Desktop에서 열어 보고 채우는 칸 (docs/TODO D 보고 형식).
        "observed": None,
        "error_text": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="정상본에 결함을 주입해 고장본을 만든다")
    parser.add_argument("--source", type=Path, action="append", help="원본 .twb/.twbx (반복 가능)")
    parser.add_argument("--out", type=Path, help="산출 디렉토리")
    parser.add_argument(
        "--experiment-b",
        action="store_true",
        help="매니페스트 항목을 하나씩 지운 파일도 만든다 (대응표 캐기)",
    )
    parser.add_argument("--list", action="store_true", help="레시피 목록만 출력한다")
    args = parser.parse_args(argv)

    # 레시피 설명에 한글·em dash가 있다. Windows 기본 콘솔(cp949)에서 죽지 않게 한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.list:
        for r in RECIPES:
            print(f"{r.id:34} rule={r.rule:16} {r.expected}")
        return 0

    if not args.source or not args.out:
        parser.error("--source 와 --out 이 필요하다 (또는 --list)")

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    recipes: tuple[Recipe, ...] = RECIPES
    if args.experiment_b:
        gates_path = Path(__file__).resolve().parent.parent / (
            "src/twb_lint/data/manifest_gates.json"
        )
        items = json.loads(gates_path.read_text(encoding="utf-8"))["known_items_unmapped"]["items"]
        recipes = recipes + experiment_b_recipes(items)

    labels: list[dict[str, object]] = []
    skipped: list[str] = []
    for source in args.source:
        if not source.exists():
            print(f"SKIP 원본 없음: {source}", file=sys.stderr)
            continue
        for recipe in recipes:
            entry = inject(source, recipe, out_dir)
            if entry is None:
                skipped.append(f"{source.name} / {recipe.id}")
                continue
            labels.append(entry)

    labels_path = out_dir / "labels.json"
    labels_path.write_text(
        json.dumps(
            {
                "note": (
                    "각 항목을 Tableau Desktop 2026.1에서 열어 보고 observed/error_text를 "
                    "채운다. 보고 형식: 열림 / 안 열림 + 에러 문구 원문 / 열리는데 이상함 + 무엇이."
                ),
                "cases": labels,
                "not_applicable": skipped,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"OK   generated={len(labels)} skipped={len(skipped)} labels={labels_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
