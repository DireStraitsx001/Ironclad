#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from report_es_exit import MAX_LOG_BYTES, clean_field, record_failure

class LauncherLogTests(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'launcher-events.log'
            self.assertFalse(record_failure(p,'success','exited','0'))
            self.assertFalse(p.exists())
    def test_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'launcher-events.log'
            self.assertTrue(record_failure(p,'exit-code','exited','1',datetime(2026,10,26,12,30,tzinfo=timezone.utc)))
            self.assertIn('result=exit-code exit_code=exited exit_status=1',p.read_text())
    def test_sanitize(self):
        self.assertEqual(clean_field('9\nFAKE=success'),'9_FAKE_success')
    def test_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'launcher-events.log'
            p.write_text('x'*(MAX_LOG_BYTES-8))
            record_failure(p,'signal','killed','SEGV')
            self.assertTrue(p.with_name(p.name+'.1').exists())
            self.assertLess(p.stat().st_size,MAX_LOG_BYTES)
if __name__=='__main__':unittest.main()
