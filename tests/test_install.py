import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cli import main
from install import configured_songs_dir, copy_song
from test_core import fixture


class InstallTests(unittest.TestCase):
    def test_missing_or_blank_setting_disables_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(configured_songs_dir(root))
            (root / ".env").write_text("PARADIDDLE_SONGS_DIR=\n")
            self.assertIsNone(configured_songs_dir(root))

    def test_quoted_path_with_spaces_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            songs = root / "My Songs #1"
            songs.mkdir()
            (root / ".env").write_text(f'# settings\nPARADIDDLE_SONGS_DIR="{songs}"\n')
            self.assertEqual(configured_songs_dir(root), songs.resolve())

    def test_nonexistent_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(f"PARADIDDLE_SONGS_DIR={root / 'missing'}\n")
            with self.assertRaisesRegex(ValueError, "existing"):
                configured_songs_dir(root)

    def test_existing_song_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output/Artist - Example"
            source.mkdir(parents=True)
            (source / "song.ogg").write_bytes(b"new")
            destination = root / "Songs"
            existing = destination / source.name
            existing.mkdir(parents=True)
            (existing / "song.ogg").write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                copy_song(source, destination)
            self.assertEqual((existing / "song.ogg").read_bytes(), b"original")

    def test_cli_copies_complete_song_and_keeps_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            songs = root / "Songs"
            songs.mkdir()
            (root / ".env").write_text(f"PARADIDDLE_SONGS_DIR={songs}\n")
            fixture(root / "input")
            with patch("cli.ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                result = main(["--input", str(root / "input"), "--output", str(root / "out")])
            self.assertEqual(result, 0)
            original = root / "out/Artist - Example"
            copied = songs / original.name
            self.assertEqual(sorted(p.name for p in original.iterdir()),
                             sorted(p.name for p in copied.iterdir()))
            for path in original.iterdir():
                self.assertEqual(path.read_bytes(), (copied / path.name).read_bytes())

    def test_failed_copy_does_not_publish_partial_song(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, destination = root / "Example", root / "Songs"
            source.mkdir()
            destination.mkdir()
            with patch("install.shutil.copytree", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    copy_song(source, destination)
            self.assertEqual(list(destination.iterdir()), [])
