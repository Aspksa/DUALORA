import tempfile
import unittest
from pathlib import Path
from history import add_event, read_history, event_record

class HistoryTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            add_event("scan", "2 screens", path)
            add_event("connection", "AQ32H3", path)
            self.assertEqual([e["type"] for e in read_history(path)], ["scan", "connection"])

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            event_record("unsafe", "bad")

    def test_length_limit(self):
        self.assertEqual(len(event_record("scan", "x" * 700)["detail"]), 400)
