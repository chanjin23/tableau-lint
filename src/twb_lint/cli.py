"""twb-lint CLI — 순수 코어를 얇게 감싼 명령줄 게이트.

`twb-lint validate <path>` → 검증 후 ERROR 있으면 종료코드 1 (mandatory gate).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from twb_lint import __version__, recipe_requests
from twb_lint.validation import engine


def _force_utf8_output() -> None:
    """콘솔 인코딩과 무관하게 출력이 깨지지 않게 한다.

    Windows 기본 콘솔은 cp949다. 메시지에 `—`나 한글 조합이 들어가면 출력 시점에
    `UnicodeEncodeError`로 **검증 결과가 통째로 사라진다** — 게이트가 판정을 내놓고도
    말을 못 하는 상태가 된다. `errors="replace"`까지 두는 이유는 인코딩 문제로
    종료코드가 뒤집히면 안 되기 때문이다.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _cmd_validate(path: str) -> int:
    report = engine.validate(path)
    for f in report.findings:
        line = f"{f.severity.value.upper()}: [{f.rule_id}] {f.location} — {f.message}"
        print(line, file=sys.stderr if f.severity.value == "error" else sys.stdout)
    if report.passed:
        print(f"PASS: {path}")
        return 0
    print(f"FAIL: {path} ({len(report.errors)} error)", file=sys.stderr)
    return 1


def _cmd_recipe_requests(
    resolve: str | None, recipe: str, show_all: bool, kind: str | None = None
) -> int:
    """건의함 목록(빈도순, `--kind`로 종류 거르기) 또는 `--resolve`로 한 건 닫기."""
    try:
        if resolve is not None:
            req = recipe_requests.resolve(resolve, recipe)
            print(
                f"닫음: {req.id} {req.task}" + (f" → {req.resolved_by}" if req.resolved_by else "")
            )
            return 0
    except recipe_requests.RequestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    shown = [
        r for r in recipe_requests.load()
        if (show_all or r.resolved_by is None) and (kind is None or r.kind == kind)
    ]
    if not shown:
        print("열린 건의가 없다.")
        return 0
    for r in shown:
        state = "닫힘" if r.resolved_by is not None else "열림"
        target = f" [{r.recipe}]" if r.recipe else ""
        layer = f" ({r.layer})" if r.layer else ""
        rules = f" rules={','.join(r.rule_ids)}" if r.rule_ids else ""
        print(f"{r.id}  x{r.count}  {state}  {r.kind}{layer}{target}  {r.task}{rules}")
        if r.symptom:
            print(f"    ▶ {r.symptom}")
        for note in r.notes:
            print(f"    · {note}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="twb-lint", description="Tableau 파일 검증 게이트")
    parser.add_argument("--version", action="version", version=f"twb-lint {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_val = sub.add_parser("validate", help="파일을 2계층 검증한다")
    p_val.add_argument("path", help=".twb 또는 .twbx 경로")
    p_req = sub.add_parser("suggestion-box", help="건의함(레시피·검사기 문제)을 빈도순으로 본다")
    p_req.add_argument("--all", action="store_true", help="닫힌 건도 보인다")
    p_req.add_argument("--resolve", metavar="ID", help="건의 한 건을 닫는다")
    p_req.add_argument("--recipe", default="", help="--resolve와 함께: 메운 레시피 번호·파일명")
    p_req.add_argument(
        "--kind", choices=recipe_requests.KINDS, help="이 종류만 보인다 (예: lint_false_alarm)"
    )

    args = parser.parse_args(argv)
    _force_utf8_output()
    if args.cmd == "validate":
        return _cmd_validate(args.path)
    if args.cmd == "suggestion-box":
        return _cmd_recipe_requests(args.resolve, args.recipe, args.all, args.kind)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
