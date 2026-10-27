#!/usr/bin/env python3
"""Log unexpected EmulationStation systemd unit exits on TF1 only.

Called by ExecStopPost. SERVICE_RESULT/EXIT_CODE/EXIT_STATUS are supplied by
systemd. Logging is deliberately best-effort and never changes restart policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import sys

LOG_PATH = Path('/var/lib/ironclad/launcher-events.log')
MAX_LOG_BYTES = 64 * 1024


def clean_field(value: str) -> str:
    """Keep each untrusted status field printable and single-line."""
    return ''.join(c if c.isascii() and (c.isalnum() or c in '-_.') else '_' for c in value)[:40]


def record_failure(log_path: Path, service_result: str, exit_code: str,
                   exit_status: str, now: datetime | None = None) -> bool:
    """Return True if a failure was written; never record clean stops."""
    if not service_result or service_result == 'success':
        return False
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    event = (f'{timestamp.isoformat(timespec="seconds")} '
             f'result={clean_field(service_result)} '
             f'exit_code={clean_field(exit_code)} '
             f'exit_status={clean_field(exit_status)}\n')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Two generations, approximately 128 KiB total at most. Rotation does not
    # depend on logrotate (which may not be installed on the device).
    if log_path.is_file() and log_path.stat().st_size + len(event.encode()) > MAX_LOG_BYTES:
        log_path.replace(log_path.with_name(log_path.name + '.1'))
    with log_path.open('a', encoding='utf-8') as log:
        log.write(event)
    return True


def main() -> int:
    result = os.environ.get('SERVICE_RESULT', '')
    if not result or result == 'success':
        return 0
    try:
        record_failure(LOG_PATH, result,
                       os.environ.get('EXIT_CODE', 'unknown'),
                       os.environ.get('EXIT_STATUS', 'unknown'))
    except OSError as exc:
        # A logging failure must never prevent shutdown or recovery.
        print(f'[IRONCLAD] Launcher diagnostic logging unavailable: {exc}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
