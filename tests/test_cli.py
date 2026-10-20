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
    def test_multiple_selected_songs_are_converted_and_copied(self):
        charts = [{"name": name, "artist": "Artist", "md5": digest * 32}
                  for name, digest in [("Unselected", "a"), ("Second", "b"), ("Third", "c")]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Songs").mkdir()
            (root / ".env").write_text(f"PARADIDDLE_SONGS_DIR={root / 'Songs'}\n")
            for title in ("Second", "Third"):
                fixture(root / title)
                ini = root / title / "song.ini"
                ini.write_text(ini.read_text().replace("name=Example", f"name={title}"))
            output = io.StringIO()
            with patch("cli.ROOT", root), patch("cli.search", return_value=charts), \
                    patch("cli.download", side_effect=[root / "Second", root / "Third"]), \
                    contextlib.redirect_stdout(output):
                status = main(["--artist", "Artist", "--choice", "2,3",
                               "--output", str(root / "out")])
            self.assertEqual(status, 0)
            self.assertEqual(sorted(p.name for p in (root / "Songs").iterdir()), ["Second", "Third"])
            self.assertEqual(sorted(p.name for p in (root / "out").iterdir()), ["Second", "Third"])
            self.assertIn("2 completed, 0 skipped, 0 failed", output.getvalue())

    def test_batch_continues_after_failure_and_skips_existing_output(self):
        charts = [{"name": name, "artist": "Artist", "md5": digest * 32}
                  for name, digest in [("Broken", "a"), ("Example", "b"), ("Example", "c")]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            output = io.StringIO()
            with patch("cli.ROOT", root), patch("cli.search", return_value=charts), \
                    patch("cli.download", side_effect=[OSError("offline"), root / "input"]) as download, \
                    contextlib.redirect_stdout(output):
                status = main(["--artist", "Artist", "--all", "--output", str(root / "out")])
            self.assertEqual(status, 1)
            self.assertEqual(download.call_count, 2)
            self.assertTrue((root / "out/Example/Example_Expert.rlrr").exists())
            self.assertIn("1 completed, 1 skipped, 1 failed", output.getvalue())

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
