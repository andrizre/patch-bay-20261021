import csv
import io
import unittest

from patchbay import build_plan, parse_spec
from patchbay.exporters import to_csv


class CsvNewlineTests(unittest.TestCase):
    def test_csv_has_lf_only_and_round_trips(self):
        spec = parse_spec({"title": "Newline", "stock": {"width": 100, "height": 100}, "pieces": [{"id": "patch", "width": 25, "height": 25}]})
        content = to_csv(build_plan(spec))
        self.assertNotIn("\r", content)
        self.assertTrue(content.endswith("\n"))
        rows = list(csv.DictReader(io.StringIO(content)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["piece_id"], "patch")


if __name__ == "__main__":
    unittest.main()
