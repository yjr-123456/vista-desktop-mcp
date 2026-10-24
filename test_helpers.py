import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from memory_store import VisualMemory
from server import helpers


class HelperTests(unittest.TestCase):
    def test_preview_and_crop_coordinates(self):
        point = helpers.map_point(800, 450, 1600, 900, 3840, 2160)
        self.assertEqual((point["x"], point["y"]), (1920, 1080))
        point = helpers.map_point(800, 400, 1600, 800, 3840, 2160,
                                  {"x": 100, "y": 200, "width": 400, "height": 200})
        self.assertEqual((point["x"], point["y"]), (300, 300))

    def test_invalid_coordinates_and_boundary(self):
        for point in [(-1, 0), (1600, 0), (float("nan"), 1)]:
            with self.assertRaises(ValueError):
                helpers.map_point(*point, 1600, 900, 100, 100)
        result = helpers.map_point(1599, 899, 1600, 900, 100, 100)
        self.assertEqual((result["x"], result["y"]), (99, 99))

    def test_exact_comparison_and_tolerance(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "a.png", Path(temp) / "b.png"
            first = Image.new("RGB", (10, 10))
            first.save(a)
            second = first.copy()
            second.putpixel((3, 4), (5, 0, 0))
            second.save(b)
            result = helpers.compare_frames(a, b)
            self.assertEqual(result["changed_pixels"], 1)
            self.assertEqual(result["changed_bounds"], [3, 4, 4, 5])
            self.assertEqual(result["changed_fraction"], 0.01)
            self.assertTrue(helpers.compare_frames(a, b, tolerance=5)["identical"])
            self.assertTrue(helpers.compare_frames(a, b, {"x": 0, "y": 0, "width": 2, "height": 2})["identical"])
            Image.new("RGB", (20, 10)).save(b)
            with self.assertRaises(ValueError):
                helpers.compare_frames(a, b)
            with self.assertRaises(OSError):
                helpers.compare_frames(a, Path(temp) / "missing.png")

    def test_audit_valid_and_tampered_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = VisualMemory(Path(temp))
            metadata = memory.archive(Image.new("RGB", (5, 5)), {"action": "test"})
            memory.remember("verified", [0], [])
            result = helpers.audit_session(Path(temp))
            self.assertTrue(result["ok"])
            self.assertEqual(result["checked_references"], 2)
            Image.new("RGB", (5, 5), "red").save(metadata["path"])
            self.assertFalse(helpers.audit_session(Path(temp))["ok"])

    def test_audit_rejects_external_paths_and_empty_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(helpers.audit_session(root)["ok"])
            (root / "history.jsonl").write_text(json.dumps({"relative_path": "../outside.png"}) + "\n")
            result = helpers.audit_session(root)
            self.assertFalse(result["ok"])
            self.assertIn("leaves session", result["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
