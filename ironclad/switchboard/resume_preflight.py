#!/usr/bin/env python3
"""IRONCLAD safe-resume preflight: inspect TF2 RetroArch states; never launch.

Preview only. A 'reviewable' candidate has a plausible state filename and a
present core, NOT a guarantee that the state is binary-compatible or playable.
Optional copies go to a separate private directory on TF1 after confirmation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

HISTORY_LIMIT = 2 * 1024 * 1024
STATE_LIMIT = 128 * 1024 * 1024
ENTRY_LIMIT = 30
SNAPSHOT_RESERVE = 16 * 1024 * 1024
SAFE_SUFFIX = re.compile(r"\.state(?:\.auto|[0-9]{1,2})?$", re.I)
SAFE_LABEL = re.compile(r"[\x00-\x1f\x7f]")
BACKUP_ROOT = Path("/home/ark/.local/share/ironclad/safe-resume-previews")


@dataclass(frozen=True)
class Review:
    label: str
    rom: str
    core: str
    state: str | None
    verdict: str
    reasons: list[str]


def no_symlink_components(path: Path, stop: Path) -> bool:
    """Reject symlinks under a trusted directory; don't resolve untrusted paths."""
    try:
        rel = path.relative_to(stop)
        if not rel.parts or ".." in rel.parts:
            return False
        current = stop
        if current.is_symlink():
            return False
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                return False
        return True
    except (ValueError, OSError):
        return False


def regular_under(path: Path, root: Path) -> bool:
    try:
        return (
            path.is_absolute()
            and no_symlink_components(path, root)
            and path.is_file()
            and path.resolve(strict=True).is_relative_to(root.resolve(strict=True))
        )
    except (OSError, RuntimeError, ValueError):
        return False


def validate_tf2(tf2: Path, require_mount: bool = True) -> bool:
    try:
        if not tf2.is_dir() or tf2.is_symlink():
            return False
        if not require_mount:
            return True
        if tf2 != Path("/roms2"):
            return False
        lines = Path("/proc/self/mountinfo").read_text().splitlines()
        if not any(len(parts) > 5 and parts[4] == "/roms2"
                   for parts in (line.split() for line in lines)):
            return False
        return (tf2.stat().st_dev != Path("/").stat().st_dev
                and tf2.stat().st_dev != Path("/roms").stat().st_dev)
    except (OSError, ValueError):
        return False


def parse_cfg(path: Path) -> dict[str, str]:
    """Minimal parser for the RetroArch key = "value" configuration format."""
    out: dict[str, str] = {}
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > HISTORY_LIMIT:
            return out
        for line in path.read_text(encoding="utf-8").splitlines():
            matched = re.fullmatch(r'\s*([a-z_]+)\s*=\s*"([^"\r\n]*)"\s*', line)
            if matched:
                out[matched.group(1)] = matched.group(2)
    except (OSError, UnicodeError, ValueError):
        return {}
    return out


def state_matches(state_dir: Path, rom: Path, tf2: Path) -> list[Path]:
    """Find only exact conventional RetroArch state names in configured TF2 dir."""
    if not state_dir.is_dir() or not no_symlink_components(state_dir, tf2):
        return []
    # A state might be named for the ROM's stem or for its full filename.
    prefixes = (rom.stem + ".state", rom.name + ".state")
    found = []
    try:
        for path in state_dir.iterdir():
            if not any(path.name.startswith(p) for p in prefixes):
                continue
            suffix = next((path.name[len(p)-6:] for p in prefixes
                           if path.name.startswith(p)), "")
            if not SAFE_SUFFIX.fullmatch(suffix):
                continue
            if regular_under(path, tf2):
                size = path.stat().st_size
                if 0 < size <= STATE_LIMIT:
                    found.append(path)
    except (OSError, ValueError):
        return []
    return sorted(set(found))


def inspect(history_item: dict, home: Path, tf2: Path) -> Review | None:
    raw = history_item.get("path")
    if not isinstance(raw, str) or "\n" in raw or "\x00" in raw:
        return None
    if raw.startswith("/roms/"):
        raw = str(tf2) + raw[len("/roms"):]
    rom = Path(raw)
    if not regular_under(rom, tf2):
        return None
    label = history_item.get("label")
    if not isinstance(label, str):
        label = rom.stem
    label = SAFE_LABEL.sub(" ", label).strip()[:64] or rom.stem[:64]
    core = history_item.get("core_path")
    issues: list[str] = []
    core_path = Path(core) if isinstance(core, str) else Path("")
    which_config = None
    for name in ("retroarch", "retroarch32"):
        root = home / ".config" / name / "cores"
        if core_path.suffix == ".so" and regular_under(core_path, root):
            which_config = home / ".config" / name / "retroarch.cfg"
            break
    if which_config is None:
        issues.append("RetroArch core path missing or not verified")
    config = parse_cfg(which_config) if which_config else {}
    state = None
    if which_config:
        state_directory = config.get("savestate_directory", "")
        # Refuse guessed directories, 'default', TF1 state locations and
        # core/content sorting schemes until explicitly supported.
        if not state_directory.startswith(str(tf2) + "/"):
            issues.append("Explicit TF2 savestate_directory not configured")
        elif (config.get("sort_savestates_by_core_enable") == "true"
              or config.get("sort_savestates_by_content_enable") == "true"):
            issues.append("Sorted save-state directories not supported")
        else:
            options = state_matches(Path(state_directory), rom, tf2)
            if len(options) == 1:
                state = options[0]
            elif not options:
                issues.append("No unambiguous conventional TF2 save state found")
            else:
                issues.append("Multiple save-state candidates; manual review required")
    if state is not None and not issues:
        # Format or core-version compatibility cannot be proven from filename.
        issues.append("Core version and state compatibility still require hardware review")
        verdict = "reviewable"
    else:
        verdict = "blocked"
    return Review(label, str(rom), str(core) if isinstance(core, str) else "",
                  str(state) if state else None, verdict, issues)


def scan(home: Path, tf2: Path, require_mount: bool = True) -> list[Review]:
    if not validate_tf2(tf2, require_mount=require_mount):
        raise ValueError("TF2 is unavailable or not a distinct mounted /roms2")
    results: list[Review] = []
    seen: set[str] = set()
    history = [
        home / ".config" / "retroarch" / "content_history.lpl",
        home / ".config" / "retroarch32" / "content_history.lpl",
        home / ".config" / "retroarch" / "playlists" / "content_history.lpl",
    ]
    for file in history:
        try:
            if file.is_symlink() or not file.is_file() or file.stat().st_size > HISTORY_LIMIT:
                continue
            document = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or not isinstance(document.get("items"), list):
                continue
        except (OSError, ValueError, UnicodeError):
            continue
        for item in document["items"]:
            if not isinstance(item, dict):
                continue
            review = inspect(item, home, tf2)
            if review and review.rom not in seen:
                seen.add(review.rom)
                results.append(review)
                if len(results) >= ENTRY_LIMIT:
                    return results
    return results


def make_snapshot(review: Review, tf2: Path, destination: Path) -> Path:
    """Never overwrite a TF2 save. Make a limited, exclusive private TF1 copy."""
    if review.verdict != "reviewable" or not review.state:
        raise ValueError("Only reviewable states can be snapshotted")
    source = Path(review.state)
    if not regular_under(source, tf2):
        raise ValueError("Unsafe or missing TF2 state")
    if destination.is_relative_to(tf2) or destination == tf2:
        raise ValueError("Snapshot destination must not be on TF2")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.is_symlink() or destination.stat().st_mode & 0o077:
        raise ValueError("Snapshot directory must be private and not a symlink")
    if not destination.resolve(strict=True).is_relative_to(BACKUP_ROOT.parent.parent.parent.parent.resolve(strict=True)):
        # Caller-specific destination is primarily used for isolated tests.
        raise ValueError("Snapshot directory outside permitted home root")
    handle = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    target: Path | None = None
    try:
        with os.fdopen(handle, "rb") as original:
            first = os.fstat(original.fileno())
            if not stat.S_ISREG(first.st_mode) or not 0 < first.st_size <= STATE_LIMIT:
                raise ValueError("Invalid state file type or size")
            if shutil.disk_usage(destination).free < first.st_size + SNAPSHOT_RESERVE:
                raise ValueError("Not enough free space on TF1")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            source_id = hashlib.sha256(str(source).encode()).hexdigest()[:12]
            target = destination / f"{stamp}-{source_id}.state.preview"
            dest_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                digest = hashlib.sha256()
                total = 0
                with os.fdopen(dest_fd, "wb") as out:
                    while block := original.read(1024 * 1024):
                        total += len(block)
                        if total > STATE_LIMIT:
                            raise ValueError("State grew beyond size limit")
                        digest.update(block)
                        out.write(block)
                    out.flush()
                    os.fsync(out.fileno())
                after = os.fstat(original.fileno())
                if (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
                ) or total != first.st_size:
                    raise ValueError("State changed during snapshot")
                with target.open("rb") as check:
                    copied_hash = hashlib.file_digest(check, "sha256").hexdigest()
                if copied_hash != digest.hexdigest():
                    raise ValueError("Snapshot verification failed")
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            return target
    except BaseException:
        if target is not None:
            target.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Review TF2 save-state candidates; never launches games")
    parser.add_argument("--json", action="store_true", help="Machine-readable candidate report")
    parser.add_argument("--snapshot", type=int, metavar="N", help="Create opt-in TF1 copy of 1-based candidate")
    args = parser.parse_args()
    try:
        entries = scan(Path("/home/ark"), Path("/roms2"))
    except ValueError as exc:
        print(f"Safe Resume unavailable: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([asdict(entry) for entry in entries], indent=2))
        return 0
    if args.snapshot is None:
        if not entries:
            print("No TF2 RetroArch history available.")
        for number, entry in enumerate(entries, 1):
            print(f"{number}. {entry.label}: {entry.verdict}")
            for reason in entry.reasons:
                print(f"   - {reason}")
        print("\nNo game or save-state was launched, modified, or loaded.")
        return 0
    if args.snapshot < 1 or args.snapshot > len(entries):
        print("Unknown entry index", file=sys.stderr)
        return 2
    entry = entries[args.snapshot - 1]
    if entry.verdict != "reviewable":
        print("Blocked: missing required preflight checks.", file=sys.stderr)
        return 2
    print(f"Game: {entry.label}\nROM: {entry.rom}\nCore: {entry.core}\nState: {entry.state}")
    print("This makes a separate TF1 copy only. It does NOT resume the game.")
    print("Save-state compatibility has NOT been confirmed.")
    try:
        if input("Type SNAPSHOT to authorize copying this state: ").strip() != "SNAPSHOT":
            print("Cancelled; no files changed.")
            return 0
        output = make_snapshot(entry, Path("/roms2"), BACKUP_ROOT)
        print(f"Verified private copy: {output}")
        return 0
    except (OSError, ValueError, EOFError) as exc:
        print(f"Snapshot not created: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
