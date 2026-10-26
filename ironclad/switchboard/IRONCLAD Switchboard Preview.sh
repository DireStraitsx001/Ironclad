#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
python3 "$ROOT/switchboard.py"
result=$?
printf '\\nIRONCLAD Switchboard exited %s\\n' "$result"
read -r -t 20 -p 'Press Enter to return...' _ </dev/tty 2>/dev/null || true
exit "$result"
