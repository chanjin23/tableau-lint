"""tableau/tableau-document-schemas → vendored XSD 동기화.

산출:
```
src/twb_lint/data/schemas/twb_2026.1.0.xsd   패치 적용된 공식 XSD
src/twb_lint/data/schemas/user-stub.xsd      우리가 쓴 스텁 (공식 XSD가 참조만 하고 안 줌)
src/twb_lint/data/schemas/xml-stub.xsd       우리가 쓴 스텁
src/twb_lint/data/schemas/NOTICE             Apache-2.0 출처 표기
```

**vendored XSD는 원본 그대로가 아니다.** 공식 XSD를 lxml에 그대로 넣으면 컴파일조차
되지 않고, 컴파일해도 정상 워크북 9/9가 실패한다 (docs/05-xsd-spike.md F1·F3).
이 스크립트가 그 격차를 메운다:

1. **스텁 주입** — `xs:import` 2개가 `schemaLocation` 없이 선언돼 있는데 본문은 그
   네임스페이스의 컴포넌트를 참조한다 → libxml2가 미해결 참조로 컴파일 거부
2. **과엄격 패치** — `explain-data`가 필수로 선언돼 있으나 실제 Tableau는 미사용 시
   쓰지 않는다 → `minOccurs="0"`

패치는 **목록으로 코드에 있다.** 상류가 갱신되면 재적용하고, 하나라도 적용되지 않으면
**vendoring을 실패시킨다** — 조용히 넘기면 "패치된 줄 알았던" XSD로 검증하게 되고
정상본이 전부 ERROR가 난다.

사용:
```bash
.venv/Scripts/python tools/vendor_schemas.py                  # GitHub에서 받는다
.venv/Scripts/python tools/vendor_schemas.py --source <클론>  # 로컬 클론에서 (오프라인)
.venv/Scripts/python tools/vendor_schemas.py --check          # 산출물이 최신인지만 확인
```
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = "tableau/tableau-document-schemas"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/schemas"

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "twb_lint" / "data" / "schemas"

# 릴리스 키 → (상류 디렉토리, 파일명). config.XSD_BY_RELEASE와 짝을 맞춘다.
RELEASES: dict[str, tuple[str, str]] = {
    "2026.1": ("2026_1", "twb_2026.1.0.xsd"),
}

USER_STUB = "user-stub.xsd"
XML_STUB = "xml-stub.xsd"


@dataclass(frozen=True, slots=True)
class Patch:
    """공식 XSD에 적용하는 수정 1건.

    `find`는 **정확히 `count`번** 나타나야 한다. 상류가 바뀌어 매치 수가 달라지면
    vendoring이 실패하며, 그때 사람이 XSD를 다시 읽고 패치를 갱신한다.
    """

    id: str
    find: str
    replace: str
    why: str
    source: str
    count: int = 1


PATCHES: tuple[Patch, ...] = (
    Patch(
        id="import-user-stub",
        find='<xs:import namespace="http://www.tableausoftware.com/xml/user"/>',
        replace=(
            '<xs:import namespace="http://www.tableausoftware.com/xml/user"'
            f' schemaLocation="{USER_STUB}"/>'
        ),
        why=(
            "schemaLocation이 없는데 본문이 user:UserAttributes-AG를 3곳에서 참조한다 → "
            "libxml2가 미해결 참조로 컴파일을 거부한다"
        ),
        source="docs/05-xsd-spike.md F1",
    ),
    Patch(
        id="import-xml-stub",
        find='<xs:import namespace="http://www.w3.org/XML/1998/namespace"/>',
        replace=(
            '<xs:import namespace="http://www.w3.org/XML/1998/namespace"'
            f' schemaLocation="{XML_STUB}"/>'
        ),
        why="위와 동일 — xml:base 등을 참조하면서 위치를 주지 않는다",
        source="docs/05-xsd-spike.md F1",
    ),
    Patch(
        id="explain-data-optional",
        find='<xs:element name="explain-data">',
        replace='<xs:element minOccurs="0" name="explain-data">',
        why=(
            "XSD가 실제 Tableau보다 엄격하다 — 기능 미사용 시 이 요소는 아예 없다. "
            "표본 9개 전부 없어서 파일당 1건의 거짓 오류가 났다"
        ),
        source="docs/05-xsd-spike.md F3",
    ),
)

USER_STUB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!-- 공식 XSD가 참조만 하고 정의를 주지 않는 attributeGroup의 관대한 스텁.
     근거: docs/05-xsd-spike.md F1. 이 파일은 우리 산출물이며 상류에 없다. -->
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://www.tableausoftware.com/xml/user"
           elementFormDefault="qualified">
  <xs:attributeGroup name="UserAttributes-AG">
    <xs:anyAttribute namespace="##any" processContents="skip"/>
  </xs:attributeGroup>
</xs:schema>
"""

XML_STUB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!-- W3C xml 네임스페이스 속성의 최소 정의. 공식 XSD가 schemaLocation 없이 import 한다.
     근거: docs/05-xsd-spike.md F1. 이 파일은 우리 산출물이며 상류에 없다. -->
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://www.w3.org/XML/1998/namespace"
           xmlns:xml="http://www.w3.org/XML/1998/namespace">
  <xs:attribute name="lang" type="xs:string"/>
  <xs:attribute name="space" type="xs:string"/>
  <xs:attribute name="base" type="xs:anyURI"/>
  <xs:attribute name="id" type="xs:ID"/>
</xs:schema>
"""

NOTICE = f"""vendored Tableau document schemas
=================================

출처     https://github.com/{REPO}
라이선스 Apache License 2.0 — Copyright (c) 2024 Salesforce, Inc.

`twb_*.xsd`는 상류 원본에 **패치가 적용된 사본**이다. 원본 그대로가 아니다.
패치 목록과 사유는 tools/vendor_schemas.py의 PATCHES에 있으며,
실측 근거는 docs/05-xsd-spike.md F1·F3이다.

`user-stub.xsd`·`xml-stub.xsd`는 상류에 없는 **우리 산출물**이다 —
공식 XSD가 참조만 하고 정의를 주지 않는 두 네임스페이스를 메운다.

재생성: .venv/Scripts/python tools/vendor_schemas.py
"""


def apply_patches(text: str) -> str:
    """패치를 순서대로 적용한다. 하나라도 매치 수가 어긋나면 예외를 던진다."""
    for patch in PATCHES:
        found = text.count(patch.find)
        if found != patch.count:
            raise RuntimeError(
                f"패치 '{patch.id}' 적용 실패: {patch.count}회 매치를 기대했는데 {found}회. "
                f"상류 XSD가 바뀌었을 수 있다. 사유: {patch.why} (근거: {patch.source})"
            )
        text = text.replace(patch.find, patch.replace, patch.count)
    return text


def fetch(release: str, source_dir: Path | None) -> str:
    """상류 XSD 원문을 가져온다 (로컬 클론 우선)."""
    upstream_dir, filename = RELEASES[release]
    if source_dir is not None:
        path = source_dir / "schemas" / upstream_dir / filename
        if not path.exists():  # 클론 루트가 아니라 schemas/ 를 직접 준 경우
            path = source_dir / upstream_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"로컬 소스에서 XSD를 찾지 못했다: {path}")
        return path.read_text(encoding="utf-8")

    url = f"{RAW_BASE}/{upstream_dir}/{filename}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 — 고정 https URL
        raw: bytes = resp.read()
    return raw.decode("utf-8")


def verify_compiles(xsd_path: Path) -> None:
    """산출물이 실제로 컴파일되는지 확인한다. 여기서 실패하면 vendoring이 실패한 것이다."""
    from lxml import etree

    etree.XMLSchema(etree.parse(str(xsd_path)))


def vendor(release: str, source_dir: Path | None, out_dir: Path) -> Path:
    """릴리스 하나를 vendoring 한다. 산출 XSD 경로를 반환."""
    _, filename = RELEASES[release]
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / USER_STUB).write_text(USER_STUB_XML, encoding="utf-8")
    (out_dir / XML_STUB).write_text(XML_STUB_XML, encoding="utf-8")
    (out_dir / "NOTICE").write_text(NOTICE, encoding="utf-8")

    patched = apply_patches(fetch(release, source_dir))
    out_path = out_dir / filename
    out_path.write_text(patched, encoding="utf-8")

    verify_compiles(out_path)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="공식 Tableau XSD를 vendoring 한다")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help=f"로컬 {REPO} 클론 경로 (생략하면 GitHub에서 받는다)",
    )
    parser.add_argument(
        "--release",
        action="append",
        choices=sorted(RELEASES),
        help="대상 릴리스 (반복 가능, 생략하면 전부)",
    )
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="산출 디렉토리")
    parser.add_argument(
        "--check",
        action="store_true",
        help="파일을 쓰지 않고 현재 산출물이 재생성 결과와 같은지만 확인한다",
    )
    args = parser.parse_args(argv)

    releases = args.release or sorted(RELEASES)
    for release in releases:
        if args.check:
            _, filename = RELEASES[release]
            current = args.out / filename
            if not current.exists():
                print(f"FAIL {release}: 산출물이 없다 ({current})", file=sys.stderr)
                return 1
            expected = apply_patches(fetch(release, args.source))
            if current.read_text(encoding="utf-8") != expected:
                print(
                    f"FAIL {release}: 산출물이 상류와 어긋난다 — 재생성이 필요하다",
                    file=sys.stderr,
                )
                return 1
            print(f"OK   {release}: 최신")
            continue

        try:
            out = vendor(release, args.source, args.out)
        except (RuntimeError, FileNotFoundError, OSError) as exc:
            print(f"FAIL {release}: {exc}", file=sys.stderr)
            return 1
        size = out.stat().st_size
        print(f"OK   {release}: {out.name} ({size:,}B) + 스텁 2개 + NOTICE, 컴파일 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
