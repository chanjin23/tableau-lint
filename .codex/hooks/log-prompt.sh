#!/usr/bin/env bash
# UserPromptSubmit hook: append submitted prompt to logs/prompts.jsonl
#
# 외부 의존 없음 (python만). 로그 디렉토리 자동 생성. 실패해도 exit 0.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$DIR/logs/prompts.jsonl"
mkdir -p "$DIR/logs" 2>/dev/null || exit 0

PY="$(command -v python || command -v py || command -v python3 || true)"
[ -n "$PY" ] || exit 0

"$PY" -c '
import datetime, json, sys

# stdin은 반드시 바이트로 읽어 UTF-8 디코드한다.
# Windows에서 sys.stdin은 locale(cp949) 인코딩이라 한글 프롬프트가 UnicodeDecodeError로 유실된다.
try:
    d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
except Exception:
    sys.exit(0)

rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "session": d.get("session_id"),
    "cwd": d.get("cwd"),
    "prompt": d.get("prompt"),
}
with open(sys.argv[1], "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
' "$LOG" 2>/dev/null || exit 0
