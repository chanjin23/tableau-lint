"""실파일 코퍼스의 XML 표면을 전수 집계한다 — 레시피 커버리지 대조용.

`docs/recipes/91-feature-coverage.md`의 근거를 재생산하는 도구다. 기능 리스트를
기억이나 UI 메뉴로 만들면 근거 등급이 `추정`이 된다(08 §5 "근거 없는 서술 0").
대신 **실파일에 실제로 나타난 태그**를 세고, 레시피가 그 태그를 언급하는지 대조한다.

경로 축이 아니라 **태그 축**으로 센다 — 대시보드 `zone`은 12겹까지 중첩돼서
경로로 세면 같은 기능이 표면 수십 개로 불어난다.

```bash
.venv/Scripts/python tools/scan_surfaces.py --root 'C:/dev/JW/2.개발' --root 'C:/dev'
```

`--root` 미지정 시 `TWB_LINT_GOLDEN_NORMAL`(';' 구분 glob)을 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

from twb_lint.io import safety

_REPEAT = re.compile(r"(?:/([^/]+))(?:/\1)+")


def collect_files(roots: list[str], depth: int = 3) -> list[Path]:
    """루트 아래 `.twb`/`.twbx`를 모은다. glob 패턴도 루트로 받는다."""
    seen: dict[str, Path] = {}
    for spec in roots:
        path = Path(spec)
        if any(ch in spec for ch in "*?["):
            candidates = Path(path.anchor or ".").glob(str(path.relative_to(path.anchor or ".")))
        elif path.is_file():
            candidates = iter([path])
        else:
            candidates = (
                p
                for d in range(depth)
                for suffix in ("*.twb", "*.twbx")
                for p in path.glob("*/" * d + suffix)
            )
        for p in candidates:
            if p.is_file() and p.suffix.lower() in (".twb", ".twbx"):
                seen.setdefault(str(p).lower(), p)
    return sorted(seen.values())


def read_twb_bytes(path: Path) -> bytes | None:
    """`.twbx`는 압축을 풀지 않고 `.twb` 엔트리만 꺼낸다 (`.hyper`가 수십 MB다)."""
    if path.suffix.lower() == ".twb":
        return path.read_bytes()
    try:
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".twb")]
            if not names:
                return None
            names.sort(key=lambda n: (n.count("/"), len(n)))
            return zf.read(names[0])
    except Exception:  # noqa: BLE001 — 못 읽는 파일은 건너뛰고 개수만 보고한다
        return None


def _squash(path: str) -> str:
    """`zone/zone/zone` → `zone+`. 중첩이 표면 수를 부풀리는 것을 막는다."""
    prev = None
    while prev != path:
        prev = path
        path = _REPEAT.sub(r"/\1+", path)
    return path


def _elem_path(el) -> str:
    parts: list[str] = []
    cur = el
    while cur is not None and isinstance(cur.tag, str):
        parts.append(cur.tag)
        cur = cur.getparent()
    return "/".join(reversed(parts))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", action="append", default=[], help="스캔 루트(디렉토리·파일·glob)")
    ap.add_argument("--out", type=Path, default=Path("tags.tsv"))
    args = ap.parse_args(argv)

    roots = args.root or [s for s in os.environ.get("TWB_LINT_GOLDEN_NORMAL", "").split(";") if s]
    if not roots:
        print("스캔 루트가 없다 — --root 또는 TWB_LINT_GOLDEN_NORMAL", file=sys.stderr)
        return 2

    files = collect_files(roots)
    total: Counter[str] = Counter()
    filecount: Counter[str] = Counter()
    paths: dict[str, Counter[str]] = defaultdict(Counter)
    attrs: dict[str, Counter[str]] = defaultdict(Counter)
    values: dict[str, Counter[str]] = defaultdict(Counter)
    skipped = 0

    for path in files:
        data = read_twb_bytes(path)
        if not data:
            skipped += 1
            continue
        try:
            root = etree.fromstring(data, safety.make_parser())
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        here: Counter[str] = Counter()
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            here[el.tag] += 1
            paths[el.tag][_squash(_elem_path(el))] += 1
            for key in el.attrib:
                attrs[el.tag][key.split("}")[-1]] += 1
            for key in ("class", "type", "element", "command"):
                v = el.get(key)
                if v:
                    values[el.tag][f"{key}={v}"] += 1
        total.update(here)
        for tag in here:
            filecount[tag] += 1

    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["tag", "files", "occurrences", "top_path", "attrs", "values"])
        for tag, n in sorted(total.items(), key=lambda kv: (-filecount[kv[0]], -kv[1])):
            w.writerow(
                [
                    tag,
                    filecount[tag],
                    n,
                    paths[tag].most_common(1)[0][0],
                    ",".join(k for k, _ in attrs[tag].most_common(10)),
                    ",".join(k for k, _ in values[tag].most_common(8)),
                ]
            )

    print(f"files={len(files)} skipped={skipped} tags={len(total)} -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
