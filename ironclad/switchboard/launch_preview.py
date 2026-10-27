#!/usr/bin/env python3
"""IRONCLAD opt-in RetroArch launcher (experimental, TF1 private sessions).

No games are launched on import or during scan. Interactive confirmation is
mandatory. Resume is a *manual* RetroArch Quick Menu -> Load State operation:
we never silently inject a state into an emulator.

Only RetroArch cores listed in history are supported. This script deliberately
does not manage EmulationStation, suspend, in-game saves, or other emulators.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

import resume_preflight as pf

HOME = Path("/home/ark")
TF2 = Path("/roms2")
SESSION_ROOT = HOME / ".local/share/ironclad/launch-sessions"
SPACE_RESERVE = 16 * 1024 * 1024


@dataclass(frozen=True)
class Plan:
    rom: Path
    core: Path
    retroarch: Path
    state: Path | None
    mode: str  # launch | resume


def executable_for_core(core: Path, home: Path = HOME) -> Path:
    for name in ("retroarch", "retroarch32"):
        cores = home / ".config" / name / "cores"
        if (core.suffix == ".so" and pf.regular_under(core, cores)
                and core.name.endswith("_libretro.so")):
            return Path("/usr/local/bin") / name
    raise ValueError("Core path not verified within this user's RetroArch cores")


def plan_for(review: pf.Review, mode: str, home: Path = HOME,
             tf2: Path = TF2) -> Plan:
    if mode not in ("launch", "resume"):
        raise ValueError("Unknown launch mode")
    rom = Path(review.rom)
    if not pf.regular_under(rom, tf2):
        raise ValueError("ROM is not a regular TF2 file")
    core = Path(review.core)
    exe = executable_for_core(core, home)
    state = None
    if mode == "resume":
        if review.verdict != "reviewable" or review.state is None:
            raise ValueError("Resume is blocked by preflight checks")
        state = Path(review.state)
        if not state.name.endswith(".state"):
            raise ValueError("Only unnumbered .state saves are supported initially")
        if not pf.regular_under(state, tf2):
            raise ValueError("State is missing, symlinked or not on TF2")
        if state.stat().st_size == 0 or state.stat().st_size > pf.STATE_LIMIT:
            raise ValueError("Save state exceeds safety limits")
    return Plan(rom, core, exe, state, mode)


def assert_no_live_emulator() -> None:
    """Do not start a second game over EmulationStation or another RetroArch."""
    commands = (
        ("systemctl", "is-active", "--quiet", "emulationstation.service"),
        ("pgrep", "-x", "emulationstation"),
        ("pgrep", "-x", "retroarch"),
        ("pgrep", "-x", "retroarch32"),
    )
    for command in commands:
        try:
            result = subprocess.run(command, check=False,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise RuntimeError(f"Cannot verify active processes: {exc}") from exc
        if result.returncode == 0:
            raise RuntimeError(f"Running process detected ({command[0]}): launch refused")
        if result.returncode not in (1, 3):
            raise RuntimeError(f"Cannot verify active processes ({command[0]}): launch refused")


def private_root(root: Path) -> None:
    # No root/sudo involved: the user running this owns all session files.
    parent = root.parent
    if parent.is_symlink():
        raise ValueError("Session parent is a symlink")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink():
        raise ValueError("Session parent is a symlink")
    root.mkdir(exist_ok=True, mode=0o700)
    if root.is_symlink() or (root.stat().st_mode & 0o077):
        raise ValueError("Session root is not private")


def copy_unchanged(source: Path, destination: Path, tf2: Path) -> None:
    """Copy one state read-only, verifying bytes and rejecting a modified source."""
    if not pf.regular_under(source, tf2):
        raise ValueError("Unsafe state path")
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    destination_created = False
    try:
        with os.fdopen(fd, "rb") as src:
            before = os.fstat(src.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= pf.STATE_LIMIT:
                raise ValueError("Invalid state type or size")
            if shutil.disk_usage(destination.parent).free < before.st_size + SPACE_RESERVE:
                raise ValueError("Insufficient space for an isolated state copy")
            dst = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            destination_created = True
            with os.fdopen(dst, "wb") as out:
                original_hash = hashlib.sha256()
                count = 0
                while chunk := src.read(1024 * 1024):
                    count += len(chunk)
                    if count > pf.STATE_LIMIT:
                        raise ValueError("State changed or grew beyond safety limit")
                    original_hash.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            after = os.fstat(src.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError("Original state changed during copying")
            if count != before.st_size:
                raise ValueError("Incomplete state copy")
            with destination.open("rb") as check:
                if hashlib.file_digest(check, "sha256").digest() != original_hash.digest():
                    raise ValueError("State copy verification failed")
    except BaseException:
        if destination_created:
            destination.unlink(missing_ok=True)
        raise


def prepare_session(plan: Plan, root: Path = SESSION_ROOT, tf2: Path = TF2) -> tuple[Path, list[str]]:
    """Create TF1-only isolated state/SRAM paths and a command; never execute."""
    private_root(root)
    session = Path(tempfile.mkdtemp(prefix="game-", dir=root))
    try:
        saved_state = session / "resume.state"
        saved_ram = session / "session.srm"
        if plan.state:
            copy_unchanged(plan.state, saved_state, tf2)
        config = session / "safety.cfg"
        config.write_text(
            'savestate_auto_load = "false"\n'
            'savestate_auto_save = "false"\n'
            'savestate_auto_index = "false"\n'
            'state_slot = "0"\n',
            encoding="utf-8",
        )
        config.chmod(0o600)
        argv = [
            str(plan.retroarch), "--config",
            str((HOME if root == SESSION_ROOT else root.parent) / ".config/retroarch"
                / "retroarch.cfg") if plan.retroarch.name == "retroarch"
            else str((HOME if root == SESSION_ROOT else root.parent) / ".config/retroarch32/retroarch.cfg"),
            "--appendconfig", str(config), "-L", str(plan.core),
            "--save", str(saved_ram), "--savestate", str(saved_state),
            str(plan.rom),
        ]
        return session, argv
    except BaseException:
        shutil.rmtree(session)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="IRONCLAD opt-in standalone RetroArch preview")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--launch", type=int, metavar="N", help="Start recent game N without loading state")
    group.add_argument("--resume", type=int, metavar="N", help="Start recent game N, then manually load copied state")
    args = parser.parse_args()
    try:
        reviews = pf.scan(HOME, TF2)
    except ValueError as exc:
        print(f"Safe Resume unavailable: {exc}", file=sys.stderr)
        return 1
    if args.launch is None and args.resume is None:
        for i, entry in enumerate(reviews, 1):
            print(f"{i}. {entry.label} — {entry.verdict}")
        print("Preview only. Use --launch N or --resume N from a separate text session.")
        return 0

    mode = "resume" if args.resume is not None else "launch"
    index = args.resume if args.resume is not None else args.launch
    if index is None or not (1 <= index <= len(reviews)):
        print("Invalid game number", file=sys.stderr)
        return 2
    try:
        plan = plan_for(reviews[index - 1], mode)
        if not plan.retroarch.is_file() or not os.access(plan.retroarch, os.X_OK):
            raise ValueError("RetroArch executable not installed at expected dArkOS path")
        assert_no_live_emulator()
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError("Interactive terminal required: no automatic launches")
        print(f"Mode: {mode.upper()}\nROM: {plan.rom}\nCore: {plan.core}")
        if plan.state:
            print(f"State to COPY: {plan.state}")
            print("Compatibility NOT guaranteed. Quick Menu -> Load State required.")
        print("Saves made during this preview stay in a private TF1 session.")
        print("They are NOT automatically synchronized back to TF2.")
        answer = input(f"Type {mode.upper()} to proceed: ").strip()
        if answer != mode.upper():
            print("Cancelled; no files changed.")
            return 0
        # Re-check immediately before building the private session.
        if not pf.validate_tf2(TF2):
            raise ValueError("TF2 became unavailable")
        assert_no_live_emulator()
        plan = plan_for(reviews[index - 1], mode)
        session, command = prepare_session(plan)
        print(f"Session: {session}")
        print("Original TF2 ROM and state were not copied back or modified by this helper.")
        print("If resuming, open Quick Menu -> Load State after RetroArch starts.")
        print("Starting RetroArch; this is NOT yet integrated into EmulationStation.")
        return subprocess.run(command, check=False).returncode
    except (OSError, ValueError, RuntimeError, EOFError) as exc:
        print(f"Launch cancelled: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
