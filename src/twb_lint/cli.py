"""twb-lint CLI — 순수 코어를 얇게 감싼 명령줄 게이트.

`twb-lint validate <path>` → 검증 후 ERROR 있으면 종료코드 1 (mandatory gate).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from twb_lint import __version__
from twb_lint.validation import engine


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="twb-lint", description="Tableau 파일 검증 게이트")
    parser.add_argument("--version", action="version", version=f"twb-lint {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_val = sub.add_parser("validate", help="파일을 2계층 검증한다")
    p_val.add_argument("path", help=".twb 또는 .twbx 경로")

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return _cmd_validate(args.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
