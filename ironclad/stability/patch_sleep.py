#!/usr/bin/env python3
"""Replace only the unsafe brightness operations in the staged RG353V sleep hook.

Fail closed if upstream changes: never silently replace unrelated code.
"""

from __future__ import annotations

from pathlib import Path
import sys

PRE_ORIGINAL = (
    '    echo $(cat /sys/class/backlight/backlight/brightness) | sudo tee /var/local/cur_bright.state\n'
    '    echo 0 | sudo tee /sys/class/backlight/backlight/brightness\n'
)
POST_ORIGINAL = (
    '    echo $(cat /var/local/cur_bright.state) | sudo tee /sys/class/backlight/backlight/brightness\n'
)
PRE_SAFE = '    /usr/bin/python3 /usr/local/lib/ironclad/sleep_brightness.py pre || true\n'
POST_SAFE = '    /usr/bin/python3 /usr/local/lib/ironclad/sleep_brightness.py post || true\n'


def patch(contents: str) -> str:
    if contents.count(PRE_ORIGINAL) != 1 or contents.count(POST_ORIGINAL) != 1:
        raise ValueError('Unexpected upstream RG353V sleep hook: brightness patch not applied')
    if 'case $1 in' not in contents or 'sleep_governors.sh' not in contents:
        raise ValueError('Missing expected system-sleep handling')
    return contents.replace(PRE_ORIGINAL, PRE_SAFE).replace(POST_ORIGINAL, POST_SAFE)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('Usage: patch_sleep.py <staged RG353V sleep hook>', file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        before = path.read_text(encoding='utf-8')
        after = patch(before)
        path.write_text(after, encoding='utf-8')
    except (OSError, ValueError) as exc:
        print(f'[IRONCLAD] Sleep guard installation aborted: {exc}', file=sys.stderr)
        return 1
    print('[IRONCLAD] RG353V brightness guard installed into suspend/resume hook')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
