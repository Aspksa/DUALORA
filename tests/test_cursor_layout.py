import unittest
from cursor_layout import arrange_side_by_side

class CursorLayoutTests(unittest.TestCase):
    def setUp(self):
        self.screens = [
            {"device":"LAPTOP","x":0,"y":0,"width":1920,"height":1080},
            {"device":"AQ32H3","x":4000,"y":-300,"width":2560,"height":1440},
        ]

    def test_right_no_gap(self):
        p = arrange_side_by_side(self.screens, "right")
        self.assertEqual((p[1]["x"], p[1]["y"]), (1920,0))

    def test_left_no_gap(self):
        p = arrange_side_by_side(self.screens, "left")
        self.assertEqual((p[1]["x"], p[1]["y"]), (-2560,0))

    def test_invalid_count(self):
        with self.assertRaises(ValueError):
            arrange_side_by_side(self.screens[:1], "right")

    def test_preserves_device_and_resolution(self):
        p = arrange_side_by_side(self.screens, "left")
        self.assertEqual([(d["device"],d["width"],d["height"]) for d in p],
                         [(d["device"],d["width"],d["height"]) for d in self.screens])

    def test_reversed_input(self):
        p = arrange_side_by_side(list(reversed(self.screens)), "right")
        self.assertEqual(p[0]["x"], 1920)

    def test_reject_bad_side(self):
        with self.assertRaises(ValueError):
            arrange_side_by_side(self.screens, "up")
