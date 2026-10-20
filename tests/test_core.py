import json
import struct
import zipfile
import sys
import tempfile
import unittest
from pathlib import Path

import mido
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from convert import convert_song
from packages import safe_target, unpack_sng


def fixture(root, delay=0, drums=True):
    root.mkdir()
    (root / "song.ini").write_text(
        f"[song]\nname=Example\nartist=Artist\ncharter=Tester\ndelay={delay}\n",
        encoding="utf-8")
    mid = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.MidiTrack()
    tempo.extend([mido.MetaMessage("set_tempo", tempo=500000),
                  mido.MetaMessage("set_tempo", tempo=1000000, time=480)])
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name="PART DRUMS" if drums else "PART GUITAR"))
    track.extend([mido.Message("note_on", note=96, velocity=100, time=480),
                  mido.Message("note_off", note=96, time=1),
                  mido.Message("note_on", note=97, velocity=100, time=479)])
    mid.tracks.extend([tempo, track])
    mid.save(root / "notes.mid")
    sf.write(root / "song.wav", np.zeros((96000, 2)), 48000)


class ConversionTests(unittest.TestCase):
    def test_nonstandard_chart_sysex_does_not_block_drums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            path = root / "input/notes.mid"
            mid = mido.MidiFile(path)
            mid.tracks[0].append(mido.Message("sysex", data=[1, 2, 3]))
            mid.save(path)
            path.write_bytes(path.read_bytes().replace(b"\xf0\x04\x01\x02\x03\xf7",
                                                       b"\xf0\x04\x01\xff\x03\xf7"))
            result = convert_song(root / "input", root / "output")
            self.assertTrue(list(result.glob("*.rlrr")))

    def test_tempo_changes_delay_and_final_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input", delay=125)
            out = convert_song(root / "input", root / "output")
            self.assertEqual(out.name, "Artist - Example")
            charts = list(out.glob("*.rlrr"))
            self.assertEqual(len(charts), 1)
            data = json.loads(charts[0].read_text())
            self.assertEqual([float(e["time"]) for e in data["events"]], [0.625, 1.625])
            self.assertEqual(data["recordingMetadata"]["creator"], "Tester")
            self.assertTrue((out / data["audioFileData"]["songTracks"][0]).is_file())
            with self.assertRaises(FileExistsError):
                convert_song(root / "input", root / "output")

    def test_missing_drums_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input", drums=False)
            with self.assertRaisesRegex(ValueError, "PART DRUMS"):
                convert_song(root / "input", root / "output")

    def test_missing_audio_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root / "input")
            (root / "input/song.wav").unlink()
            with self.assertRaisesRegex(ValueError, "audio"):
                convert_song(root / "input", root / "output")


class PackageTests(unittest.TestCase):
    def test_sng_known_payload_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b"known payload" * 100000
            mask = bytes(range(16))
            metadata = struct.pack("<Q", 1) + struct.pack("<i", 4) + b"name" + struct.pack("<i", 4) + b"Test"
            filename = b"notes.mid"
            index_size = 8 + 1 + len(filename) + 16
            offset = 26 + 8 + len(metadata) + 8 + index_size + 8
            index = struct.pack("<Q", 1) + bytes([len(filename)]) + filename + struct.pack("<QQ", len(payload), offset)
            masked = bytes(b ^ mask[i % 16] ^ (i & 255) for i, b in enumerate(payload))
            data = (b"SNGPKG" + struct.pack("<I", 1) + mask +
                    struct.pack("<Q", len(metadata)) + metadata +
                    struct.pack("<Q", len(index)) + index +
                    struct.pack("<Q", len(payload)) + masked)
            path = root / "test.sng"
            path.write_bytes(data)
            unpack_sng(path, root / "out")
            self.assertEqual((root / "out/notes.mid").read_bytes(), payload)
            self.assertIn("name = Test", (root / "out/song.ini").read_text())

    def test_zip_traversal_does_not_write_outside_destination(self):
        from packages import unpack_zip
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                archive.writestr("../escape.txt", "bad")
            with self.assertRaises(ValueError):
                unpack_zip(root / "bad.zip", root / "out")
            self.assertFalse((root / "escape.txt").exists())

    def test_windows_archive_paths_rejected(self):
        for name in ["../x", "/x", "C:/x", "a\\..\\x", "CON", "a:stream", "x./y"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_target(Path("safe"), name)

    def test_truncated_sng_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.sng"
            path.write_bytes(b"SNGPKG")
            with self.assertRaises(ValueError):
                unpack_sng(path, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()

