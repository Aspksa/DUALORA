import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from display_engine import position_snapshot, validate, save_profile, read_profiles, enumerate_displays

SCREENS = [{"device": "DISPLAY1", "x": 0, "y": 0, "width": 1920, "height": 1080},
           {"device": "DISPLAY2", "x": 1920, "y": 0, "width": 2560, "height": 1440}]

class ProfileTests(unittest.TestCase):
    def test_save_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "profiles.json"
            save_profile("Работа", SCREENS, p)
            self.assertEqual(read_profiles(p)["Работа"], position_snapshot(SCREENS))

    def test_missing_monitor(self):
        p = position_snapshot(SCREENS)
        p[1]["device"] = "unknown"
        with self.assertRaises(ValueError):
            validate(p, SCREENS)

    def test_resolution_mismatch(self):
        p = position_snapshot(SCREENS)
        p[0]["width"] = 800
        with self.assertRaises(ValueError):
            validate(p, SCREENS)

    def test_invalid_coordinate(self):
        p = position_snapshot(SCREENS)
        p[0]["x"] = 999999999
        with self.assertRaises(ValueError):
            validate(p, SCREENS)

    def test_windows_only(self):
        with patch("display_engine.platform.system", return_value="Linux"):
            with self.assertRaises(RuntimeError):
                enumerate_displays()
