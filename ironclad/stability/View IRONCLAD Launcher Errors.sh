#!/usr/bin/env bash
# Read-only diagnostics from TF1. No TF2 access.
set -u
logdir=/var/lib/ironclad
tmp=$(mktemp /tmp/ironclad-errors.XXXXXX) || exit 1
trap 'rm -f -- "$tmp"' EXIT
{
  printf 'IRONCLAD — EmulationStation launcher errors (UTC)\n\n'
  any=0
  for file in "$logdir/launcher-events.log.1" "$logdir/launcher-events.log"; do
    if [[ -f "$file" && -r "$file" ]]; then
      tail -n 120 -- "$file"
      any=1
    fi
  done
  if [[ "$any" -eq 0 ]]; then
    printf 'No recorded EmulationStation service failures.\n'
    printf 'This does not rule out errors inside emulators or games.\n'
  fi
} > "$tmp"
if command -v dialog >/dev/null 2>&1 && [[ -t 1 ]]; then
  dialog --title 'IRONCLAD Launcher Diagnostics' --textbox "$tmp" 20 76
else
  cat -- "$tmp"
fi
