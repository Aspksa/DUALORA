import unittest
from unittest.mock import patch
import dualora


class CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(dualora.APP_VERSION, "0.6.0")

    def test_enumeration_non_windows(self):
        with patch("dualora.platform.system", return_value="Linux"):
            self.assertEqual(dualora.active_displays(), [])

    def test_identifiers_non_windows(self):
        with patch("dualora.platform.system", return_value="Linux"):
            self.assertEqual(dualora.monitor_identifiers(), [])

    def test_switch_rejects_non_windows(self):
        with patch("dualora.platform.system", return_value="Linux"):
            with self.assertRaises(RuntimeError):
                dualora.switch_display("extend")

    def test_switch_rejects_invalid_mode(self):
        with patch("dualora.platform.system", return_value="Windows"):
            with self.assertRaises(ValueError):
                dualora.switch_display("anything")


if __name__ == "__main__":
    unittest.main()
