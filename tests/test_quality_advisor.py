import unittest
from quality_advisor import recommend
class QualityTests(unittest.TestCase):
    def test_modes(self):
        result = recommend([{"width":2560,"height":1440,"hz":60},{"width":1920,"height":1080,"hz":144}])
        self.assertEqual(result["sharp"]["width"], 2560)
        self.assertEqual(result["smooth"]["hz"], 144)
        self.assertEqual(result["balanced"]["height"], 1440)
    def test_empty(self):
        self.assertEqual(recommend([]), {})
