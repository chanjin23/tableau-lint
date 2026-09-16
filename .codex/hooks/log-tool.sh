#!/usr/bin/env bash
# PreToolUse hook: append tool/MCP invocation to logs/tools.jsonl
# MCP tools arrive as tool_name "mcp__<server>__<tool>"; flagged with is_mcp.
#
# 외부 의존 없음 (python만 — 이 프로젝트 런타임). 로그 디렉토리는 자동 생성.
# 어떤 실패도 exit 0 — 로깅 훅이 툴 호출을 막으면 안 된다.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$DIR/logs/tools.jsonl"
mkdir -p "$DIR/logs" 2>/dev/null || exit 0

PY="$(command -v python || command -v py || command -v python3 || true)"
[ -n "$PY" ] || exit 0

"$PY" -c '
import datetime, json, sys

# stdin은 반드시 바이트로 읽어 UTF-8 디코드한다.
# Windows에서 sys.stdin은 locale(cp949) 인코딩이라 한글 입력이 UnicodeDecodeError로 유실된다.
try:
    d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
except Exception:
    sys.exit(0)

name = d.get("tool_name") or ""
rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "session": d.get("session_id"),
    "tool": name,
    "is_mcp": name.startswith("mcp__"),
    "input": d.get("tool_input"),
}
with open(sys.argv[1], "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
' "$LOG" 2>/dev/null || exit 0
