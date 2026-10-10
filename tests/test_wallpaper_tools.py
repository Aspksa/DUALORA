import tempfile
import unittest
from pathlib import Path
from wallpaper_tools import wallpaper_candidate, refresh_explanation

class WallpaperTests(unittest.TestCase):
    def test_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"wallpaper.png"
            p.write_bytes(b"test")
            self.assertEqual(wallpaper_candidate(p), p.resolve())
    def test_reject_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"file.exe"
            p.write_bytes(b"test")
            with self.assertRaises(ValueError):
                wallpaper_candidate(p)
    def test_fps_distinction(self):
        self.assertIn("не FPS", refresh_explanation(144))
