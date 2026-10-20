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
    def test_artist_selection_converts_selected_chart(self):
        charts = [{"name": name, "artist": "Artist", "md5": digest * 32}
                  for name, digest in [("First", "a"), ("Example", "b")]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            with patch("cli.ROOT", root), patch("cli.search", return_value=charts), \
                    patch("cli.download", return_value=root / "input") as download, \
                    patch("builtins.input", return_value="2"), contextlib.redirect_stdout(io.StringIO()):
                result = main(["--artist", "Artist", "--output", str(root / "out")])
            self.assertEqual(result, 0)
            self.assertEqual(download.call_args.args[0], charts[1])
            self.assertTrue((root / "out/Example/Example_Expert.rlrr").exists())

    @patch("cli.search")
    def test_artist_flag_lists_songs_without_prompting(self, search):
        search.return_value = [{"name": "BIRDS", "artist": "Turnstile", "md5": "a"*32}]
        output = io.StringIO()
        with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")), contextlib.redirect_stdout(output):
            self.assertEqual(main(["--artist", "Turnstile", "--list"]), 0)
        search.assert_called_once_with(None, "Turnstile")
        self.assertIn("BIRDS", output.getvalue())

    @patch("cli.search")
    def test_blank_song_enters_artist_browse_and_allows_cancel(self, search):
        search.return_value = [{"name": "BIRDS", "artist": "Turnstile", "md5": "a"*32}]
        with patch("builtins.input", side_effect=["", "Turnstile", "q"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 2)
        search.assert_called_once_with(None, "Turnstile")

    def test_local_input_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            with patch("cli.ROOT", root), contextlib.redirect_stdout(io.StringIO()):
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
