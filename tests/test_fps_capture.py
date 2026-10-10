import unittest
import tempfile
from pathlib import Path
from fps_capture import load_presentmon,summary
class TestFrames(unittest.TestCase):
    def test_metrics(self):
        report=summary([10]*100)
        self.assertEqual(report["fps"],100)
        self.assertEqual(report["one_percent_low"],100)
    def test_stutter(self):
        self.assertEqual(summary([10]*99+[100])["stutters"],1)
    def test_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"frames.csv"
            p.write_text("MsBetweenPresents\\n16.67\\n33.33\\n",encoding="utf-8")
            self.assertEqual(len(load_presentmon(p)),2)
    def test_empty(self):
        self.assertIsNone(summary([])["fps"])
