import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources import filter_charts, search, download


class SearchTests(unittest.TestCase):
    @patch("sources.request_json")
    def test_artist_search_returns_sorted_songs_and_filters_other_artists(self, request):
        def chart(name, artist, digest, instrument="drums"):
            return {"name": name, "artist": artist, "md5": digest * 32,
                    "notesData": {"instruments": [instrument]}}
        holiday = chart("HOLIDAY", "Turnstile", "a")
        birds = chart("BIRDS", "Turnstile", "b")
        request.return_value = {"found": 5, "data": [
            holiday, birds, birds, chart("BIRDS", "Other", "c"),
            chart("Guitar only", "Turnstile", "d", "guitar")]}
        self.assertEqual(search(None, "Turnstile"), [birds, holiday])
        self.assertEqual(request.call_args.args[1]["search"], "Turnstile")

    def test_rejects_wrong_artist_and_guitar_only_results(self):
        base = {"name": "BIRDS", "artist": "Turnstile", "md5": "a" * 32,
                "notesData": {"instruments": ["drums"]}}
        rows = [base, base, dict(base, artist="Someone Else", md5="b" * 32),
                dict(base, notesData={"instruments": ["guitar"]}, md5="c" * 32)]
        self.assertEqual(filter_charts(rows, "birds", "TURNSTILE"), [base])

    def test_missing_drum_metadata_does_not_claim_drums(self):
        self.assertEqual(filter_charts([{"name": "X", "artist": "Y", "md5": "a"*32}], "X", "Y"), [])

    def test_invalid_download_hash_rejected(self):
        with self.assertRaises(ValueError):
            download({"md5": "../bad"}, Path("unused"))

    @patch("sources.request_json", side_effect=URLError("offline"))
    def test_network_failure_is_not_reported_as_no_matches(self, request):
        with self.assertRaises(URLError):
            search("BIRDS", "Turnstile")

    @patch("sources.request_json")
    def test_search_reads_later_pages(self, request):
        chart = {"name": "BIRDS", "artist": "Turnstile", "md5": "a"*32,
                 "notesData": {"instruments": ["drums"]}}
        request.side_effect = [{"found": 251, "data": [{}] * 250},
                               {"found": 251, "data": [chart]}]
        self.assertEqual(search("BIRDS", "Turnstile"), [chart])


if __name__ == "__main__":
    unittest.main()
