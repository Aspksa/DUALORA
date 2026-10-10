import unittest
from unittest.mock import patch
from display_engine import available_modes, apply_video_mode, validate, position_snapshot

class NewModesTests(unittest.TestCase):
    def test_invalid_platform_mode_enumeration(self):
        with patch("display_engine.platform.system", return_value="Linux"):
            with self.assertRaises(RuntimeError):
                available_modes("DISPLAY1")

    def test_no_active_display_mode_change(self):
        with patch("display_engine.enumerate_displays", return_value=[]):
            with self.assertRaises(ValueError):
                apply_video_mode("DISPLAY1", {"width": 1920, "height": 1080, "hz": 60})

    def test_reposition_accepts_valid_coordinates(self):
        displays = [{"device":"DISPLAY1","x":0,"y":0,"width":1920,"height":1080}]
        proposed = position_snapshot(displays)
        proposed[0]["x"] = -1920
        validate(proposed, displays)
