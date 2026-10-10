import unittest
from gaming_advisor import assess_display

class GamingTests(unittest.TestCase):
    def test_frequency_at_same_resolution(self):
        result = assess_display({"device":"AQ32H3", "width":1920, "height":1080, "hz":60},
            [{"width":1920,"height":1080,"hz":144},{"width":1280,"height":720,"hz":165}])
        self.assertEqual(result["max_at_current_resolution"],144)
        self.assertEqual(result["max_available_hz"],165)
        self.assertEqual(result["vrr_status"],"не проверено")
    def test_no_fps_claim(self):
        result = assess_display({"device":"DISPLAY1","width":1920,"height":1080,"hz":60},[])
        self.assertTrue(any("не увеличивает" in tip for tip in result["tips"]))
