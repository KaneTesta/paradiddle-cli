import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from selection import parse_selection


class SelectionTests(unittest.TestCase):
    def test_multiple_ranges_and_duplicates(self):
        self.assertEqual(parse_selection("1, 3-5,3,2", 6), [1, 3, 4, 5, 2])

    def test_all(self):
        self.assertEqual(parse_selection(" ALL ", 3), [1, 2, 3])

    def test_invalid_selections(self):
        for value in ("", "0", "4", "3-1", "1,", "-1", "x", "1-999999999"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_selection(value, 3)
