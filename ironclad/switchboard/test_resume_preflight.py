#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import resume_preflight as rp


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.tf2 = base / "roms2"
        (self.tf2 / "gba").mkdir(parents=True)
        self.rom = self.tf2 / "gba" / "Example.gba"
        self.rom.write_bytes(b"rom")
        self.home = base / "home"
        self.core_dir = self.home / ".config" / "retroarch" / "cores"
        self.core_dir.mkdir(parents=True)
        self.core = self.core_dir / "mgba_libretro.so"
        self.core.write_bytes(b"core")
        self.cfg = self.home / ".config" / "retroarch" / "retroarch.cfg"
        self.cfg.write_text('savestate_directory = "' + str(self.tf2 / "gba") + '"\n')
        self.state = self.tf2 / "gba" / "Example.state"
        self.state.write_bytes(b"state")
        self.item = {"path": str(self.rom), "core_path": str(self.core), "label": "Example"}

    def test_reviewable_not_proven_compatible(self):
        result = rp.inspect(self.item, self.home, self.tf2)
        self.assertEqual(result.verdict, "reviewable")
        self.assertIn("compatibility", " ".join(result.reasons))
        self.assertEqual(result.state, str(self.state))

    def test_missing_core_blocked(self):
        self.core.unlink()
        self.assertEqual(rp.inspect(self.item, self.home, self.tf2).verdict, "blocked")

    def test_multiple_states_blocked(self):
        (self.tf2 / "gba" / "Example.state.auto").write_bytes(b"two")
        self.assertEqual(rp.inspect(self.item, self.home, self.tf2).verdict, "blocked")

    def test_no_state_blocked(self):
        self.state.unlink()
        self.assertEqual(rp.inspect(self.item, self.home, self.tf2).verdict, "blocked")

    def test_state_symlink_not_used(self):
        self.state.unlink()
        self.state.symlink_to(self.rom)
        self.assertEqual(rp.inspect(self.item, self.home, self.tf2).verdict, "blocked")

    def test_tf1_rom_rejected(self):
        item = dict(self.item, path=str(self.home / "elsewhere.gba"))
        self.assertIsNone(rp.inspect(item, self.home, self.tf2))

    def test_corrupt_history_skipped(self):
        history = self.home / ".config" / "retroarch" / "content_history.lpl"
        history.write_text("{unreadable")
        self.assertEqual(rp.scan(self.home, self.tf2, require_mount=False), [])

    def test_valid_history(self):
        history = self.home / ".config" / "retroarch" / "content_history.lpl"
        history.write_text(json.dumps({"items": [self.item]}))
        self.assertEqual(len(rp.scan(self.home, self.tf2, require_mount=False)), 1)

    def test_unconfigured_state_dir_blocked(self):
        self.cfg.write_text("")
        self.assertEqual(rp.inspect(self.item, self.home, self.tf2).verdict, "blocked")


if __name__ == "__main__":
    unittest.main()
