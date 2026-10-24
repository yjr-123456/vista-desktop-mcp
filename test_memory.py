import tempfile
import unittest
from pathlib import Path

from PIL import Image
from server import VisualMemory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = VisualMemory(Path(self.temp.name))
        self.memory.archive(Image.new("RGB", (200, 100), (12, 34, 56)), {"action": "test"})

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_pixels(self):
        result = self.memory.pixels(0, None, 2, 3)
        self.assertEqual(result["rgb"], [[(12, 34, 56)] * 3] * 2)

    def test_upstream_crop_and_coordinate_metadata(self):
        result = self.memory._inspect({"question": "control", "views": [
            {"label": "button", "turn": 0, "region": {"x": 10, "y": 20, "width": 40, "height": 20}}]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["views"][0]["image_size"], {"width": 1600, "height": 800})
        self.assertEqual(result["images"][0]["mime_type"], "image/png")

    def test_old_resolution_after_display_change(self):
        self.memory.archive(Image.new("RGB", (300, 200)), {"action": "resized"})
        result = self.memory._inspect({"question": "compare", "views": [
            {"label": "old", "turn": 0}, {"label": "new", "turn": 1}]})
        self.assertTrue(result["ok"])
        self.assertEqual([v["region"]["width"] for v in result["metadata"]["views"]], [200, 300])

    def test_out_of_bounds_crop_rejected(self):
        result = self.memory._inspect({"question": "bad", "views": [
            {"label": "bad", "turn": 0, "region": {"x": 190, "y": 0, "width": 30, "height": 20}}]})
        self.assertFalse(result["ok"])

    def test_reopen_preserves_original_frame(self):
        reopened = VisualMemory(Path(self.temp.name))
        self.assertEqual(reopened.turn, 0)
        reopened.archive(Image.new("RGB", (10, 10)), {"action": "new"})
        self.assertEqual(reopened.turn, 1)
        self.assertEqual(reopened.pixels(0, None, 1, 1)["rgb"], [[(12, 34, 56)]])


if __name__ == "__main__":
    unittest.main()
