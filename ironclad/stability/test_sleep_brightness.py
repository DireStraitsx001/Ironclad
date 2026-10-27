#!/usr/bin/env python3
from pathlib import Path
import tempfile
import unittest

from sleep_brightness import fallback, guard, read_level
from patch_sleep import patch, PRE_ORIGINAL, POST_ORIGINAL, PRE_SAFE, POST_SAFE


class BrightnessGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backlight = self.root / 'backlight'
        self.backlight.mkdir()
        self.state = self.root / 'run' / 'ironclad' / 'brightness-before-suspend'
        (self.backlight / 'max_brightness').write_text('255\n')
        (self.backlight / 'brightness').write_text('80\n')

    def brightness(self):
        return read_level(self.backlight / 'brightness')

    def test_normal_cycle(self):
        self.assertTrue(guard('pre', self.backlight, self.state))
        self.assertEqual(self.brightness(), 0)
        self.assertEqual(read_level(self.state), 80)
        self.assertTrue(guard('post', self.backlight, self.state))
        self.assertEqual(self.brightness(), 80)
        self.assertFalse(self.state.exists())

    def test_zero_brightness_before_suspend_recovers_to_visible(self):
        (self.backlight / 'brightness').write_text('0\n')
        guard('pre', self.backlight, self.state)
        guard('post', self.backlight, self.state)
        self.assertEqual(self.brightness(), fallback(255))

    def test_no_state_and_black_screen_uses_fallback(self):
        (self.backlight / 'brightness').write_text('0\n')
        self.assertTrue(guard('post', self.backlight, self.state))
        self.assertEqual(self.brightness(), fallback(255))

    def test_no_state_does_not_override_lit_display(self):
        self.assertFalse(guard('post', self.backlight, self.state))
        self.assertEqual(self.brightness(), 80)

    def test_corrupt_state(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text('not-a-number\n')
        (self.backlight / 'brightness').write_text('0\n')
        guard('post', self.backlight, self.state)
        self.assertEqual(self.brightness(), fallback(255))

    def test_invalid_device_value_skips_dim(self):
        (self.backlight / 'max_brightness').write_text('invalid\n')
        self.assertFalse(guard('pre', self.backlight, self.state))
        self.assertEqual(self.brightness(), 80)
        self.assertFalse(self.state.exists())

    def test_out_of_range_saved_level_uses_fallback(self):
        (self.backlight / 'brightness').write_text('0\n')
        self.state.parent.mkdir(parents=True)
        self.state.write_text('9000\n')
        guard('post', self.backlight, self.state)
        self.assertEqual(self.brightness(), fallback(255))


class PatchTests(unittest.TestCase):
    def test_upstream_brightness_replacement(self):
        original = '#!/bin/bash\ncase $1 in\npre)\n' + PRE_ORIGINAL + '  sleep_governors.sh\npost)\n' + POST_ORIGINAL + ';;\nesac\n'
        result = patch(original)
        self.assertIn(PRE_SAFE, result)
        self.assertIn(POST_SAFE, result)
        self.assertNotIn('/var/local/cur_bright.state', result)
        self.assertIn('sleep_governors.sh', result)

    def test_unexpected_upstream_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected upstream'):
            patch('case $1 in\nsleep_governors.sh\n')


if __name__ == '__main__':
    unittest.main()
