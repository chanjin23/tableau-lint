"""`.twb` XML 파싱/직렬화.

철칙: **문자열 편집 금지.** 항상 파싱된 트리(lxml)를 다룬다 (02 S1-1 · 07 G6).
파서는 `safety.make_parser()`로만 만든다 — 파서 없이 `etree.parse(path)`를 부르면
기본 파서(엔티티 해석 활성)가 쓰여 XXE·엔티티 폭탄이 그대로 열린다 (07 G10).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from twb_lint.io import safety


class MalformedXmlError(safety.InputError):
    """`.twb`가 well-formed XML이 아니거나 읽을 수 없다. 계약은 `safety.InputError` (03 D9.1)."""


def parse(twb_path: Path) -> Any:
    """`.twb`를 lxml 트리로 파싱해 루트 element를 반환한다.

    줄번호가 필요하면 반환된 element에서 `.getroottree()`로 트리를 되찾는다 —
    Finding은 `line`을 정수로 갖고, L-A는 `error_log`의 줄번호를 그대로 쓴다.

    Raises:
        MalformedXmlError: XML이 깨졌거나 파일을 읽을 수 없을 때.
    """
    from lxml import etree

    try:
        tree = etree.parse(str(twb_path), safety.make_parser())
    except etree.XMLSyntaxError as exc:
        raise MalformedXmlError(
            safety.InputProblem(
                safety.ProblemKind.MALFORMED_XML,
                f"`.twb`가 well-formed XML이 아니다 (line {exc.lineno}): {exc.msg}",
                fix="XML이 깨진 파일은 Tableau도 열지 못한다. 생성기 쪽 출력을 확인한다.",
            )
        ) from exc
    except OSError as exc:
        raise MalformedXmlError(
            safety.InputProblem(
                safety.ProblemKind.UNREADABLE,
                f"`.twb`를 읽을 수 없다: {exc}",
            )
        ) from exc
    return tree.getroot()


def read_version(twb_path: Path) -> str | None:
    """`<workbook version=...>` 값을 읽는다. 없으면 None.

    ⚠️ **XSD 선택 키가 아니다.** 이 값은 "이 버전 이상이면 열 수 있다"는 **최소 호환
    버전**이라 2026.1이 저장해도 `18.1`이 나온다. 스키마·함수목록 선택은
    `source-build`로 한다 (07 G1 · 05 F4). 이 값의 용도는 로더 문법 판정(규칙 ⑥)이다.

    검증 경로는 이 함수를 쓰지 않는다 — 파일당 파싱 1회 원칙 때문에 `load_context()`가
    이미 파싱한 트리에서 직접 읽는다 (07 G9). 여기는 트리가 없는 일회성 호출자용이다.
    """
    root = parse(twb_path)
    value = root.get("version")
    return str(value) if value is not None else None


def serialize(root: Any, out: Path) -> Path:
    """트리를 `.twb`로 직렬화한다. 반환은 쓴 경로.

    인코딩은 **원본 선언을 따른다** — 실파일은 `utf-8`이고 한글 caption·필드명이 그대로
    들어 있다. 여기서 ASCII로 이스케이프하면 diff가 통째로 뒤집혀 골든셋 회귀가 무의미해진다.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    tree = root.getroottree()
    encoding = tree.docinfo.encoding or "utf-8"
    tree.write(str(out), xml_declaration=True, encoding=encoding)
    return out
