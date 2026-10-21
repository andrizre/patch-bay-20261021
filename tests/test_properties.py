import random
from pathlib import Path
import tempfile
import unittest

from patchbay import build_plan, parse_spec
from patchbay.exporters import write_outputs


class GeometryAndOutputTests(unittest.TestCase):
    def test_fifty_seeded_specs_respect_independent_geometry_checks(self):
        for seed in range(50):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                width, height = rng.randint(80, 200), rng.randint(80, 200)
                margin, gap, seam = rng.randint(0, 6), rng.randint(0, 8), rng.randint(0, 5)
                pieces = [
                    {"id": f"p{index}", "width": rng.randint(5, width - 2 * margin - 2 * seam),
                     "height": rng.randint(5, height - 2 * margin - 2 * seam),
                     "quantity": rng.randint(1, 5), "rotate": rng.choice([True, False])}
                    for index in range(rng.randint(1, 6))
                ]
                spec = parse_spec({"title": "Random geometry", "stock": {"width": width, "height": height, "margin": margin, "gap": gap}, "seam": seam, "pieces": pieces})
                plan = build_plan(spec)
                self.assertEqual(len(plan["placements"]), sum(item["quantity"] for item in pieces))
                for index, left in enumerate(plan["placements"]):
                    self.assertGreaterEqual(left["x"], margin)
                    self.assertGreaterEqual(left["y"], margin)
                    self.assertLessEqual(left["x"] + left["width"], width - margin)
                    self.assertLessEqual(left["y"] + left["height"], height - margin)
                    for right in plan["placements"][index + 1:]:
                        if left["sheet"] == right["sheet"]:
                            x_separation = max(right["x"] - left["x"] - left["width"], left["x"] - right["x"] - right["width"])
                            y_separation = max(right["y"] - left["y"] - left["height"], left["y"] - right["y"] - right["height"])
                            self.assertGreaterEqual(max(x_separation, y_separation), gap)

    def test_gap_is_not_required_outside_sheet(self):
        for gap, size in [(0, 100), (1, 101)]:
            spec = parse_spec({"title": "Edges", "stock": {"width": size, "height": size, "gap": gap}, "pieces": [{"id": "square", "width": 50, "height": 50, "quantity": 4}]})
            self.assertEqual(build_plan(spec)["summary"]["sheets"], 1)

    def test_failed_second_output_removes_first_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blocker = root / "blocker"
            blocker.write_text("keep me")
            first = root / "first.json"
            with self.assertRaises(OSError):
                write_outputs([(first, "{}\n"), (blocker / "cuts.csv", "csv")])
            self.assertFalse(first.exists())
            self.assertEqual(blocker.read_text(), "keep me")

    def test_same_output_path_is_rejected_without_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "same"
            with self.assertRaises(ValueError):
                write_outputs([(path, "json"), (path, "csv")])
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
