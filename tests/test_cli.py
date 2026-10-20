import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cli import main
from test_core import fixture


class CliTests(unittest.TestCase):
    def test_local_input_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["--input", str(root / "input"), "--output", str(root / "out")])
            self.assertEqual(result, 0)
            self.assertEqual(len(list((root / "out").rglob("*.rlrr"))), 1)

    @patch("cli.search", return_value=[])
    def test_no_match_returns_nonzero(self, search):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--song", "Missing", "--artist", "Someone"]), 2)

    @patch("cli.search")
    def test_multiple_matches_require_selection(self, search):
        search.return_value = [{"name": "X", "artist": "Y", "md5": str(i)*32} for i in (1, 2)]
        with patch("builtins.input", return_value="q"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--song", "X", "--artist", "Y"]), 2)


if __name__ == "__main__":
    unittest.main()
