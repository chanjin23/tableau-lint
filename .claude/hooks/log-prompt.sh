#!/usr/bin/env bash
# UserPromptSubmit hook: append submitted prompt to logs/prompts.jsonl
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$DIR/logs/prompts.jsonl"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -c --arg ts "$TS" '{ts:$ts, session:.session_id, cwd:.cwd, prompt:.prompt}' >> "$LOG"
