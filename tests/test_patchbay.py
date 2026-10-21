import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from patchbay.exporters import to_csv
from patchbay.model import parse_spec
from patchbay.packing import build_plan, validate_plan


ROOT = Path(__file__).resolve().parents[1]


class PatchBayTests(unittest.TestCase):
    def spec(self, **overrides):
        data = {
            "title": "Test Quilt",
            "stock": {"width": 100, "height": 100},
            "seam": 0,
            "pieces": [{"id": "a", "width": 20, "height": 10}],
        }
        data.update(overrides)
        return parse_spec(data)

    def test_defaults_and_frozen_shape(self):
        spec = self.spec()
        self.assertEqual(spec.stock.margin, 0)
        self.assertEqual(spec.stock.gap, 0)
        self.assertEqual(spec.seam, 0)
        self.assertEqual(spec.pieces[0].quantity, 1)
        self.assertTrue(spec.pieces[0].rotate)
        with self.assertRaises((AttributeError, TypeError)):
            spec.seam = 2

    def test_bad_boolean_flags_are_rejected(self):
        for key, value in (("seam", True), ("stock", {"width": 100, "height": 100, "margin": False}),):
            data = {"title": "Q", "stock": {"width": 100, "height": 100}, "pieces": [{"id": "a", "width": 5, "height": 5}]}
            if key == "stock":
                data["stock"] = value
            else:
                data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_spec(data)
        with self.assertRaises(ValueError):
            parse_spec({"title": "Q", "stock": {"width": 100, "height": 100}, "pieces": [{"id": "a", "width": 5, "height": 5, "rotate": 1}]})

    def test_invalid_dimensions_and_ranges_are_rejected(self):
        for stock in ({"width": 0, "height": 20}, {"width": 10001, "height": 20}, {"width": 20, "height": 20, "gap": 101}):
            with self.subTest(stock=stock), self.assertRaises(ValueError):
                parse_spec({"title": "Q", "stock": stock, "pieces": [{"id": "a", "width": 5, "height": 5}]})
        with self.assertRaises(ValueError):
            parse_spec({"title": "Q", "stock": {"width": 20, "height": 20}, "seam": -1, "pieces": [{"id": "a", "width": 5, "height": 5}]})

    def test_duplicate_and_invalid_piece_ids_are_rejected(self):
        base = {"title": "Q", "stock": {"width": 100, "height": 100}}
        for pieces in ([{"id": "a", "width": 5, "height": 5}, {"id": "a", "width": 5, "height": 5}], [{"id": "A", "width": 5, "height": 5}], []):
            with self.subTest(pieces=pieces), self.assertRaises(ValueError):
                parse_spec({**base, "pieces": pieces})

    def test_oversize_piece_is_rejected_even_when_rotated(self):
        with self.assertRaises(ValueError):
            parse_spec({"title": "Q", "stock": {"width": 100, "height": 60}, "pieces": [{"id": "wide", "width": 101, "height": 90, "rotate": True}]})

    def test_rotation_required_is_allowed(self):
        spec = parse_spec({"title": "Q", "stock": {"width": 100, "height": 60}, "pieces": [{"id": "turn", "width": 50, "height": 90, "rotate": True}]})
        plan = build_plan(spec)
        self.assertTrue(plan["placements"][0]["rotated"])
        validate_plan(spec, plan)

    def test_rotation_disabled_is_rejected_when_only_rotation_fits(self):
        with self.assertRaises(ValueError):
            parse_spec({"title": "Q", "stock": {"width": 100, "height": 60}, "pieces": [{"id": "turn", "width": 50, "height": 90, "rotate": False}]})

    def test_seam_and_margins_are_reflected_in_placement_dimensions(self):
        spec = parse_spec({"title": "Q", "stock": {"width": 100, "height": 100, "margin": 8}, "seam": 6, "pieces": [{"id": "a", "width": 20, "height": 10}]})
        placement = build_plan(spec)["placements"][0]
        self.assertEqual((placement["x"], placement["y"]), (8, 8))
        self.assertEqual((placement["width"], placement["height"]), (32, 22))

    def test_gap_is_respected(self):
        spec = self.spec(stock={"width": 100, "height": 40, "gap": 3}, pieces=[{"id": "a", "width": 20, "height": 10}, {"id": "b", "width": 20, "height": 10}])
        placements = build_plan(spec)["placements"]
        a, b = placements
        horizontal = abs((a["x"] + a["width"]) - b["x"])
        vertical = abs((a["y"] + a["height"]) - b["y"])
        self.assertTrue(horizontal >= 3 or vertical >= 3)
        validate_plan(spec, build_plan(spec))

    def test_no_overlap(self):
        spec = self.spec(pieces=[{"id": "a", "width": 40, "height": 40}, {"id": "b", "width": 40, "height": 40}])
        plan = build_plan(spec)
        for i, first in enumerate(plan["placements"]):
            for second in plan["placements"][i + 1 :]:
                self.assertTrue(first["x"] + first["width"] <= second["x"] or second["x"] + second["width"] <= first["x"] or first["y"] + first["height"] <= second["y"] or second["y"] + second["height"] <= first["y"])

    def test_multisheet_and_counts(self):
        spec = self.spec(stock={"width": 30, "height": 30}, pieces=[{"id": "a", "width": 20, "height": 20, "quantity": 5}])
        plan = build_plan(spec)
        self.assertGreater(plan["summary"]["sheets"], 1)
        self.assertEqual(plan["summary"]["placements"], 5)
        self.assertEqual(sorted(p["instance"] for p in plan["placements"]), [1, 2, 3, 4, 5])

    def test_deterministic_plan(self):
        spec = self.spec(pieces=[{"id": "a", "width": 20, "height": 10, "quantity": 3}, {"id": "b", "width": 12, "height": 9, "quantity": 2}])
        self.assertEqual(build_plan(spec), build_plan(spec))

    def test_tampered_plan_validation(self):
        spec = self.spec()
        plan = build_plan(spec)
        plan["placements"][0]["x"] = 999
        with self.assertRaises(ValueError):
            validate_plan(spec, plan)

    def test_csv_header_and_rows(self):
        plan = build_plan(self.spec())
        rows = list(csv.reader(to_csv(plan).splitlines()))
        self.assertEqual(rows[0], ["sheet", "piece_id", "instance", "x_mm", "y_mm", "width_mm", "height_mm", "rotated"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1:3], ["a", "1"])

    def test_cli_validate_and_plan_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "input.json"
            output = directory / "nested" / "plan.json"
            csv = directory / "nested" / "plan.csv"
            source.write_text(json.dumps({"title": "CLI", "stock": {"width": 100, "height": 100}, "pieces": [{"id": "a", "width": 10, "height": 10}]}))
            validate = subprocess.run([sys.executable, "-m", "patchbay", "validate", str(source)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(validate.returncode, 0, validate.stderr)
            self.assertEqual(json.loads(validate.stdout)["title"], "CLI")
            planned = subprocess.run([sys.executable, "-m", "patchbay", "plan", str(source), "--output", str(output), "--csv", str(csv)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertTrue(output.exists())
            self.assertTrue(csv.exists())
            refused = subprocess.run([sys.executable, "-m", "patchbay", "plan", str(source), "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(refused.returncode, 2)
            same_path = subprocess.run([sys.executable, "-m", "patchbay", "plan", str(source), "--output", str(directory / "same.json"), "--csv", str(directory / "same.json")], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(same_path.returncode, 2)


if __name__ == "__main__":
    unittest.main()
