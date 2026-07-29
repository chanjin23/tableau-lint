"""신뢰할 수 없는 입력에 대한 방어 정책 — **I/O 구현보다 먼저** 고정한다.

이 도구가 먹는 파일은 **AI가 생성한 것**이거나 출처를 모르는 것이다. 파서에
그냥 넘기면 XML/ZIP의 고전적 함정이 그대로 열린다. 정책을 io 구현 뒤로 미루면
이미 `etree.parse(path)`가 여기저기 박힌 뒤에 고치게 되므로 순서를 뒤집었다
(docs/TODO A7).

| 공격 | 방어 | 이 모듈 |
|---|---|---|
| XXE (외부 엔티티로 파일 탈취) | 엔티티·DTD·네트워크 전면 차단 | `make_parser()` |
| billion laughs (엔티티 폭탄) | 위와 동일 — 확장하지 않으면 안 터진다 | `make_parser()` |
| 거대 입력으로 메모리 고갈 | 파싱 전 크기 상한 | `check_source()` |
| zip slip (`../` 경로 탈출) | 엔트리 경로 정규화 후 목적지 하위인지 확인 | `safe_extract_path()` |
| zip bomb (압축비 폭탄) | 엔트리·총량·압축비 상한 | `check_zip_entry()` |

상한값은 **실측 기준**이다. 표본 워크북의 `.twb`는 799KB~1281KB,
`.twbx`는 `.hyper` 포함 수십 MB다 (docs/05-xsd-spike.md 표본). 정상 파일을 막으면
AC7(거짓양성 0)이 깨지므로 실측의 수십 배로 잡는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

# --- 크기 정책 (실측 대비 여유 배수) -------------------------------------------------

MAX_SOURCE_BYTES = 512 * 1024 * 1024
"""입력 파일 자체의 상한. 표본 `.twbx`가 수십 MB라 512MB면 정상 파일을 막지 않는다."""

MAX_TWB_BYTES = 64 * 1024 * 1024
"""`.twb` XML 하나의 상한. 표본 최대 1.3MB의 약 50배."""

MAX_UNPACKED_BYTES = 2 * 1024 * 1024 * 1024
"""`.twbx` 해제 총량 상한 (`.hyper` 포함)."""

MAX_COMPRESSION_RATIO = 200
"""엔트리 하나의 (해제 크기 / 압축 크기) 상한. 정상 XML도 10~20배는 나오므로
200배는 명백한 폭탄만 걸린다."""

MAX_ZIP_ENTRIES = 10_000
"""엔트리 개수 상한. 표본은 `.twb` 1개 + `.hyper` 1~4개다."""

VALID_SUFFIXES = (".twb", ".twbx")


class ProblemKind(StrEnum):
    """입력 단계에서 판정 가능한 문제 유형."""

    MISSING = "missing"
    NOT_A_FILE = "not_a_file"
    BAD_SUFFIX = "bad_suffix"
    TOO_LARGE = "too_large"
    UNREADABLE = "unreadable"
    CORRUPT_ARCHIVE = "corrupt_archive"
    UNSAFE_ARCHIVE = "unsafe_archive"


@dataclass(frozen=True, slots=True)
class InputProblem:
    """입력 파일의 문제 1건. 엔진이 `Stage.INPUT` finding으로 번역한다.

    여기서 Finding을 직접 만들지 않는 이유: io 계층은 검증 어휘를 몰라야 한다.
    무엇이 잘못됐는지만 말하고, 심각도 배정과 메시지 조립은 엔진이 한다.
    """

    kind: ProblemKind
    detail: str
    fix: str | None = None


def make_parser() -> Any:
    """`.twb` 파싱에 쓸 안전한 lxml 파서.

    옵션을 하나라도 빠뜨리면 방어가 무너지므로 **파서는 반드시 이 함수로만 만든다.**
    `etree.parse(path)`를 파서 없이 부르면 기본 파서(엔티티 해석 활성)가 쓰인다.

    - `resolve_entities=False` — XXE·billion laughs 차단. 엔티티를 확장하지 않는다
    - `no_network=True` — 스키마/DTD를 네트워크에서 끌어오지 않는다 (오프라인 원칙)
    - `load_dtd=False` — 외부 DTD 미로드
    - `huge_tree=False` — libxml2의 깊이/노드 수 하드 리밋 유지
    """
    from lxml import etree

    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        recover=False,
    )


def check_source(path: Path) -> list[InputProblem]:
    """검증 파이프라인에 들어가기 전 입력 파일을 점검한다.

    **예외를 던지지 않는다** — 문제를 목록으로 반환한다. 게이트 판정 경로를 하나로
    유지하려면 입력 오류도 finding이어야 하기 때문이다 (02 S5).
    """
    problems: list[InputProblem] = []
    if not path.exists():
        return [
            InputProblem(
                ProblemKind.MISSING,
                f"파일이 없다: {path}",
                fix="경로를 확인한다. 상대경로면 작업 디렉토리 기준으로 해석된다.",
            )
        ]
    if not path.is_file():
        return [InputProblem(ProblemKind.NOT_A_FILE, f"파일이 아니다(디렉토리 등): {path}")]

    suffix = path.suffix.lower()
    if suffix not in VALID_SUFFIXES:
        problems.append(
            InputProblem(
                ProblemKind.BAD_SUFFIX,
                f"지원하지 않는 확장자 '{suffix}' (지원: {', '.join(VALID_SUFFIXES)})",
                fix=".twb 또는 .twbx 파일을 넘긴다.",
            )
        )

    try:
        size = path.stat().st_size
    except OSError as exc:  # 권한·잠금 등
        return [InputProblem(ProblemKind.UNREADABLE, f"파일 정보를 읽을 수 없다: {exc}")]

    limit = MAX_TWB_BYTES if suffix == ".twb" else MAX_SOURCE_BYTES
    if size > limit:
        problems.append(
            InputProblem(
                ProblemKind.TOO_LARGE,
                f"파일이 상한을 넘는다: {size:,}B > {limit:,}B",
                fix="정상 워크북이 이 크기라면 io/safety.py의 상한을 실측 근거와 함께 올린다.",
            )
        )
    return problems


def safe_extract_path(dest_root: Path, entry_name: str) -> Path | None:
    """ZIP 엔트리를 풀 안전한 경로. 목적지 밖으로 나가면 None (zip slip 차단).

    `zipfile.extractall`은 절대경로·`..`를 걸러주지만 심볼릭 링크 엔트리와
    드라이브 지정(`C:\\...`)까지 보장하지는 않는다. 목적지 하위인지를 **해석된 경로로**
    직접 확인한다.

    아래 절대경로 조기 반환은 **중복 방어(defense in depth)** 다. `resolve()` +
    `relative_to()`가 이미 세 경우(`/abs`·`C:\\abs`·`../`)를 전부 차단하는 것을 확인했다.
    지워도 동작이 같아서 테스트로는 구분되지 않지만, 의도를 코드로 남기고 `resolve()`
    동작이 플랫폼에 따라 달라질 때를 대비해 유지한다.
    """
    if entry_name.startswith("/") or entry_name.startswith("\\"):
        return None
    candidate = (dest_root / entry_name).resolve()
    root = dest_root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def check_zip_entry(
    name: str, compressed_size: int, file_size: int, running_total: int
) -> InputProblem | None:
    """ZIP 엔트리 하나가 해제 정책을 만족하는지. 문제가 없으면 None.

    `running_total`은 이 엔트리를 **포함하지 않은** 지금까지의 해제 누계다.
    """
    if running_total + file_size > MAX_UNPACKED_BYTES:
        return InputProblem(
            ProblemKind.UNSAFE_ARCHIVE,
            f"해제 총량이 상한을 넘는다: {running_total + file_size:,}B > {MAX_UNPACKED_BYTES:,}B",
        )
    if compressed_size > 0 and file_size / compressed_size > MAX_COMPRESSION_RATIO:
        return InputProblem(
            ProblemKind.UNSAFE_ARCHIVE,
            f"엔트리 '{name}'의 압축비가 비정상이다: "
            f"{file_size / compressed_size:.0f}배 > {MAX_COMPRESSION_RATIO}배",
        )
    return None
