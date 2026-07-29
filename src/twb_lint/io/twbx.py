"""`.twbx` unpack/pack [C1].

`.twbx` = ZIP(`.twb` XML + `.hyper`/기타 바이너리). unpack/pack 시 `.hyper`
바이너리는 **무손실 보존**해야 한다 (재압축·재인코딩 금지 — docs/07 G6).

해제 정책은 전부 `io.safety`가 소유한다. 여기서는 정책을 **적용**만 한다 —
zip slip은 `safe_extract_path()`, zip bomb은 `check_zip_entry()`다 (docs/03-design.md D9).
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from twb_lint.io import safety

_CHUNK = 1024 * 1024
"""해제 시 한 번에 읽는 크기. 통째로 `read()`하면 zip bomb이 상한 검사 전에 메모리를 먹는다."""

_FIXED_TIME = (1980, 1, 1, 0, 0, 0)
"""pack이 모든 엔트리에 쓰는 타임스탬프 (ZIP의 최소값).

**같은 디렉토리를 두 번 묶으면 바이트가 같아야 한다** (결정론 — 02 S1-5). 파일 mtime을
쓰면 매번 달라진다. 원본 타임스탬프는 어차피 unpack 시점에 사라지므로(추출된 파일의
mtime은 추출 시각이다) 보존할 정보가 아니라, 재현성을 택했다."""


class ArchiveError(safety.InputError):
    """`.twbx`를 열 수 없거나 해제 정책을 위반했다. 계약은 `safety.InputError` (03 D9.1)."""


@dataclass(slots=True)
class Unpacked:
    """unpack 결과."""

    twb_path: Path
    """추출된 .twb 경로."""

    root: Path
    """추출 루트 디렉토리 (.hyper 등 포함)."""


def unpack(path: Path, dest: Path) -> Unpacked:
    """`.twbx`를 dest에 풀어 `.twb`와 부속 파일을 얻는다.

    `.twb` 입력이면 그대로 감싸 반환한다 (`root`는 그 파일이 있는 디렉토리다 —
    `.twb`는 부속 파일이 없으므로 pack 대상이 아니다).

    Raises:
        ArchiveError: ZIP이 깨졌거나, 엔트리가 목적지 밖을 가리키거나(zip slip),
            해제 정책 상한을 넘을 때(zip bomb). 예외를 던지는 이유는 이 함수가
            MCP `twb_unpack`에서도 직접 쓰이기 때문이다 — 검증 경로에서는
            `load_context()`가 잡아 finding으로 번역한다.
    """
    if path.suffix.lower() != ".twbx":
        return Unpacked(twb_path=path, root=path.parent)

    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path) as zf:
            extracted = _extract_all(zf, dest)
    except zipfile.BadZipFile as exc:
        raise ArchiveError(
            safety.InputProblem(
                safety.ProblemKind.CORRUPT_ARCHIVE,
                f"`.twbx` ZIP을 열 수 없다: {exc}",
                fix="Tableau에서 다시 저장하거나, 파일이 전송 중 잘리지 않았는지 확인한다.",
            )
        ) from exc
    except OSError as exc:
        # 파일이 없거나 권한이 없으면 `zipfile.ZipFile`이 BadZipFile이 아니라 OSError를
        # 던진다. 이걸 흘려보내면 io 계층의 실패 계약(D9.1)이 깨져서, 호출자가
        # `safety.InputError` 하나로 잡던 것을 놓친다 (MCP 도구에서 실측으로 드러났다).
        raise ArchiveError(
            safety.InputProblem(
                safety.ProblemKind.UNREADABLE,
                f"`.twbx`를 열 수 없다: {exc}",
                fix="경로를 확인한다. 상대경로면 작업 디렉토리 기준으로 해석된다.",
            )
        ) from exc

    twb_path = _pick_twb(extracted)
    if twb_path is None:
        raise ArchiveError(
            safety.InputProblem(
                safety.ProblemKind.CORRUPT_ARCHIVE,
                f"`.twbx` 안에 `.twb`가 없다 (엔트리 {len(extracted)}개)",
                fix="정상 `.twbx`는 최상위에 `.twb` 1개를 담는다. 다른 ZIP이 아닌지 확인한다.",
            )
        )
    return Unpacked(twb_path=twb_path, root=dest)


def pack(root: Path, out: Path) -> Path:
    """디렉토리를 `.twbx`로 다시 묶는다 (`.hyper` 무손실). 반환은 쓴 경로.

    `.hyper`는 **무압축(ZIP_STORED)** 으로 넣는다. 내부적으로 이미 압축된 포맷이라
    deflate가 얻는 것이 거의 없고, 바이트를 그대로 흘려보내는 경로가 "재압축하지
    않는다"(07 G6)를 코드로 보장한다. 나머지는 deflate — `.twb` XML은 잘 줄어든다.

    `.twb`를 **첫 엔트리로** 둔다 (실파일 배치와 같다). 나머지는 경로 정렬이라
    같은 디렉토리는 항상 같은 순서로 묶인다.

    Raises:
        ArchiveError: `.twb`가 없을 때. `.twb` 없는 `.twbx`는 Tableau가 열지 못하므로
            조용히 만들어 내보내면 안 된다.
    """
    files = sorted(
        (p for p in root.rglob("*") if p.is_file()),
        key=lambda p: (p.suffix.lower() != ".twb", p.relative_to(root).as_posix()),
    )
    if not any(p.suffix.lower() == ".twb" for p in files):
        raise ArchiveError(
            safety.InputProblem(
                safety.ProblemKind.CORRUPT_ARCHIVE,
                f"묶을 `.twb`가 없다: {root}",
                fix="unpack한 디렉토리를 그대로 넘긴다.",
            )
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as zf:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=_FIXED_TIME)
            info.compress_type = (
                zipfile.ZIP_STORED if path.suffix.lower() == ".hyper" else zipfile.ZIP_DEFLATED
            )
            with path.open("rb") as src, zf.open(info, "w") as dst:
                shutil.copyfileobj(src, dst, _CHUNK)
    return out


def _extract_all(zf: zipfile.ZipFile, dest: Path) -> list[Path]:
    """정책을 통과한 엔트리만 dest 아래로 푼다. 반환은 실제로 쓴 파일 경로들."""
    infos = zf.infolist()
    if len(infos) > safety.MAX_ZIP_ENTRIES:
        raise ArchiveError(
            safety.InputProblem(
                safety.ProblemKind.UNSAFE_ARCHIVE,
                f"엔트리 수가 상한을 넘는다: {len(infos):,}개 > {safety.MAX_ZIP_ENTRIES:,}개",
            )
        )

    written: list[Path] = []
    total = 0
    for info in infos:
        target = safety.safe_extract_path(dest, info.filename)
        if target is None:
            raise ArchiveError(
                safety.InputProblem(
                    safety.ProblemKind.UNSAFE_ARCHIVE,
                    f"엔트리 '{info.filename}'가 해제 디렉토리 밖을 가리킨다 (zip slip)",
                )
            )
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        problem = safety.check_zip_entry(
            info.filename, info.compress_size, info.file_size, total
        )
        if problem is not None:
            raise ArchiveError(problem)

        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as out:
            # 상한을 **선언 크기가 아니라 실제로 읽은 바이트**로도 건다. ZIP 헤더의
            # file_size는 아카이브 제작자가 쓰는 값이라 거짓말할 수 있고, 그러면
            # check_zip_entry()의 사전 검사만으로는 폭탄이 그대로 통과한다.
            total += _copy_bounded(src, out, safety.MAX_UNPACKED_BYTES - total, info.filename)
        written.append(target)
    return written


def _copy_bounded(src: IO[bytes], out: IO[bytes], remaining: int, name: str) -> int:
    """엔트리 하나를 `remaining` 바이트까지만 복사한다. 넘으면 ArchiveError."""
    copied = 0
    while True:
        chunk = src.read(_CHUNK)
        if not chunk:
            return copied
        copied += len(chunk)
        if copied > remaining:
            raise ArchiveError(
                safety.InputProblem(
                    safety.ProblemKind.UNSAFE_ARCHIVE,
                    f"엔트리 '{name}'의 실제 해제 크기가 선언값보다 크다 — "
                    f"총량 상한 {safety.MAX_UNPACKED_BYTES:,}B를 넘었다",
                )
            )
        out.write(chunk)


def _pick_twb(extracted: list[Path]) -> Path | None:
    """해제 결과에서 `.twb`를 고른다. 최상위에 있는 것을 우선한다.

    정상 `.twbx`는 최상위에 `.twb` 1개다. 하위 디렉토리에도 `.twb`가 있는 아카이브를
    만났을 때 깊은 쪽을 집으면 엉뚱한 워크북을 검증하게 되므로 깊이로 정렬한다.
    """
    candidates = [p for p in extracted if p.suffix.lower() == ".twb"]
    if not candidates:
        return None
    return min(candidates, key=lambda p: (len(p.parts), p.name))
