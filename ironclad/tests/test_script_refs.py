#!/usr/bin/env python3
"""Verify static files referenced by the RG353V firmware integration exist.

This is a build-input audit, not proof that runtime assets or firmware work.
Run from anywhere; all paths are relative to the repository root.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BuildInputReferences(unittest.TestCase):
    def test_rg353v_sourced_shell_scripts_exist(self):
        build = (ROOT / "build_rg353v.sh").read_text(encoding="utf-8")
        refs = re.findall(r'(?m)^\s*source\s+\./([\w./-]+\.sh)\b', build)
        self.assertGreater(len(refs), 40, "Unexpectedly few RG353V build stages")
        missing = sorted({name for name in refs if not (ROOT / name).is_file()})
        self.assertEqual(missing, [], "Missing build-time source files")

    def test_integrated_feature_sources_exist(self):
        expected = [
            "ironclad/prepare-branding.sh",
            "ironclad/integrate-image.sh",
            "ironclad/rename-image.sh",
            "ironclad/stability/report_es_exit.py",
            "ironclad/stability/sleep_brightness.py",
            "ironclad/stability/patch_sleep.py",
            "ironclad/stability/View IRONCLAD Launcher Errors.sh",
            "scripts/sleep.rk3566",
            "Emulationstation/emulationstation.service",
        ]
        missing = [name for name in expected if not (ROOT / name).is_file()]
        self.assertEqual(missing, [], "Missing integration source assets")

    def test_optional_branding_not_required(self):
        script = (ROOT / "ironclad/prepare-branding.sh").read_text(encoding="utf-8")
        self.assertIn('[[ -f "$a" && -f "$b" ]]', script)
        self.assertIn("keeping upstream visuals", script)

    def test_command_wrappers_have_targets(self):
        wrappers = [
            ("ironclad/switchboard/IRONCLAD Switchboard Preview.sh",
             "ironclad/switchboard/switchboard.py"),
            ("ironclad/tests/test_integration_staging.sh",
             "ironclad/integrate-image.sh"),
        ]
        for wrapper, target in wrappers:
            with self.subTest(wrapper=wrapper):
                self.assertTrue((ROOT / wrapper).is_file())
                self.assertTrue((ROOT / target).is_file())


if __name__ == "__main__":
    unittest.main()
