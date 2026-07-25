#!/usr/bin/env bash
# PreToolUse hook: append tool/MCP invocation to logs/tools.jsonl
# MCP tools arrive as tool_name "mcp__<server>__<tool>"; flagged with is_mcp.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$DIR/logs/tools.jsonl"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -c --arg ts "$TS" '
  {
    ts: $ts,
    session: .session_id,
    tool: .tool_name,
    is_mcp: (.tool_name | startswith("mcp__")),
    input: .tool_input
  }' >> "$LOG"
