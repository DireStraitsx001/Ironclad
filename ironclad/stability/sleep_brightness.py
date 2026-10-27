#!/usr/bin/env python3
"""RG353V suspend/resume brightness guard.

Invoked only by the RG353V sleep hook. This helper does not touch ROMs,
save states, emulators, power policy, or the second SD card.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

BACKLIGHT = Path('/sys/class/backlight/backlight')
STATE = Path('/run/ironclad/brightness-before-suspend')


def read_level(path: Path) -> int | None:
    try:
        value = path.read_text(encoding='ascii').strip()
        if not value.isdecimal():
            return None
        return int(value)
    except (OSError, UnicodeError, ValueError):
        return None


def write_level(path: Path, value: int) -> bool:
    try:
        path.write_text(str(value) + '\n', encoding='ascii')
        return True
    except OSError as exc:
        print(f'[IRONCLAD] Cannot set brightness: {exc}', file=sys.stderr)
        return False


def save_state(state: Path, value: int) -> bool:
    """Write an atomic private state file on tmpfs; do not dim on failure."""
    try:
        state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.brightness-', dir=state.parent)
        try:
            with os.fdopen(fd, 'w', encoding='ascii') as stream:
                stream.write(f'{value}\n')
            os.replace(temporary, state)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return True
    except OSError as exc:
        print(f'[IRONCLAD] Cannot save brightness: {exc}', file=sys.stderr)
        return False


def fallback(maximum: int) -> int:
    # Conservative visible level without setting the screen to full brightness.
    return max(1, maximum // 4)


def guard(phase: str, backlight: Path = BACKLIGHT, state: Path = STATE) -> bool:
    """Return True when a brightness change was made; failures are nonfatal."""
    max_level = read_level(backlight / 'max_brightness')
    current = read_level(backlight / 'brightness')
    if max_level is None or max_level < 1 or current is None or not 0 <= current <= max_level:
        print('[IRONCLAD] Invalid backlight reading; leaving brightness untouched', file=sys.stderr)
        return False

    if phase == 'pre':
        # A currently blank screen must not be stored as a future wake value.
        target = current if current > 0 else fallback(max_level)
        if not save_state(state, target):
            return False
        return write_level(backlight / 'brightness', 0)

    if phase == 'post':
        saved = read_level(state)
        try:
            state.unlink(missing_ok=True)
        except OSError as exc:
            print(f'[IRONCLAD] Cannot discard brightness state: {exc}', file=sys.stderr)
        if saved is not None and 1 <= saved <= max_level:
            return write_level(backlight / 'brightness', saved)
        # When no valid state is available, do not override a lit display.
        if current > 0:
            return False
        print('[IRONCLAD] Wake brightness state missing; restoring safe visible level', file=sys.stderr)
        return write_level(backlight / 'brightness', fallback(max_level))

    raise ValueError('Expected pre or post')


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ('pre', 'post'):
        print('Usage: sleep_brightness.py pre|post', file=sys.stderr)
        return 2
    try:
        guard(argv[1])
    except OSError as exc:
        print(f'[IRONCLAD] Brightness guard error: {exc}', file=sys.stderr)
    # Suspend/resume must never be blocked by diagnostic/recovery code.
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
