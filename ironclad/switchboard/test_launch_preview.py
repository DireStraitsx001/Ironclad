#!/usr/bin/env python3
"""Offline tests: no emulator processes are launched."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import launch_preview as lp
import resume_preflight as pf


class LaunchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        base = Path(self.t.name)
        self.home = base / "home"
        self.tf2 = base / "roms2"
        self.rom = self.tf2 / "gba" / "Example.gba"
        self.rom.parent.mkdir(parents=True)
        self.rom.write_bytes(b"rom")
        core = self.home / ".config/retroarch/cores/mgba_libretro.so"
        core.parent.mkdir(parents=True)
        core.write_bytes(b"binary")
        self.core = core
        self.state = self.tf2 / "gba" / "Example.state"
        self.state.write_bytes(b"state")
        self.entry = pf.Review("Example", str(self.rom), str(core), str(self.state),
                               "reviewable", ["core compatibility unverified"])
        self.root = base / "sessions"

    def test_normal_launch_requires_no_state(self):
        p = lp.plan_for(self.entry, "launch", self.home, self.tf2)
        self.assertIsNone(p.state)
        self.assertEqual(p.retroarch, Path("/usr/local/bin/retroarch"))

    def test_resume_uses_existing_state(self):
        p = lp.plan_for(self.entry, "resume", self.home, self.tf2)
        self.assertEqual(p.state, self.state)

    def test_missing_state_fails(self):
        self.state.unlink()
        with self.assertRaises(ValueError):
            lp.plan_for(self.entry, "resume", self.home, self.tf2)

    def test_ambiguous_or_blocked_never_resumes(self):
        blocked = pf.Review("Example",str(self.rom),str(self.core),str(self.state),
                             "blocked",["multiple states"])
        with self.assertRaises(ValueError):
            lp.plan_for(blocked, "resume", self.home, self.tf2)

    def test_symlink_state_fails(self):
        self.state.unlink()
        self.state.symlink_to(self.rom)
        with self.assertRaises(ValueError):
            lp.plan_for(self.entry, "resume", self.home, self.tf2)

    def test_copy_creates_private_isolated_state(self):
        p = lp.plan_for(self.entry, "resume", self.home, self.tf2)
        with patch.object(lp, "HOME", self.home):
            folder, argv = lp.prepare_session(p, self.root, self.tf2)
        self.assertEqual((folder / "resume.state").read_bytes(), b"state")
        self.assertEqual(self.state.read_bytes(), b"state")
        self.assertEqual(folder.stat().st_mode & 0o077, 0)
        self.assertIn("--savestate", argv)
        self.assertNotIn("savestate_auto_load = \"true\"",
                         (folder / "safety.cfg").read_text())

    def test_session_copy_rejects_symlink(self):
        self.state.unlink()
        self.state.symlink_to(self.rom)
        with self.assertRaises(ValueError):
            lp.copy_unchanged(self.state, self.root / "state", self.tf2)

    def test_existing_destination_refused(self):
        dest = self.root / "state"
        self.root.mkdir()
        dest.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            lp.copy_unchanged(self.state, dest, self.tf2)
        self.assertEqual(dest.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
