"""Interactive song search -> download -> Paradiddle conversion."""
import argparse
import configparser
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import URLError

from convert import clean, convert_song
from install import configured_songs_dir, copy_song
from packages import unpack_sng, unpack_zip
from sources import download, search

ROOT = Path(__file__).resolve().parent


def song_folder(root):
    if (root / "notes.mid").is_file():
        return root
    folders = sorted({p.parent for p in root.rglob("*") if p.suffix.lower() in {".mid", ".midi"}})
    if len(folders) != 1:
        raise ValueError("Expected one song containing MIDI. Use --input with an individual song folder.")
    return folders[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find an existing drum chart and convert it to Paradiddle.")
    parser.add_argument("--song", help="Exact song title (case/punctuation insensitive)")
    parser.add_argument("--artist", help="Artist name; omit --song to browse their drum charts")
    parser.add_argument("--input", type=Path, help="Local Clone Hero folder, .sng, or .zip")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--mapping", choices=["auto", "rockband", "guitarhero"], default="auto")
    parser.add_argument("--choice", type=int, help="Select a numbered search result without prompting")
    parser.add_argument("--list", action="store_true", help="List matches without downloading")
    args = parser.parse_args(argv)
    songs_dir = None if args.list else configured_songs_dir(ROOT)
    print("Paradiddle Song CLI\n", flush=True)
    cache = ROOT / "cache"
    cache.mkdir(exist_ok=True)
    provenance = None
    source = args.input
    if source is None:
        if args.song is not None:
            song = args.song.strip() or None
        elif args.artist is not None:
            song = None
        else:
            song = input("Song name (leave blank to browse by artist): ").strip() or None
        artist = (args.artist or input("Artist: ")).strip()
        description = f"{clean(artist)} - {clean(song)}" if song else f"drum charts by {clean(artist)}"
        print(f"\nSearching for {description} ...", flush=True)
        charts = search(song, artist)
        if not charts:
            print("No matching downloadable drum chart found on Enchor.")
            print("Check the full title/artist spelling, or find a chart at https://rhythmverse.co/songfiles/game")
            print("Rock Band packages need C3 Tools/Nautilus conversion first; then use --input with that folder.")
            return 2
        for i, chart in enumerate(charts, 1):
            counts = (chart.get("notesData") or {}).get("noteCounts") or []
            levels = sorted({c.get("difficulty", "?") for c in counts if c.get("instrument") == "drums"
                             and c.get("count", 0) > 0})
            print(f"{i}. {clean(chart.get('artist') or '')} - {clean(chart.get('name') or '')}"
                  f" | Charter: {clean(chart.get('charter') or 'Unknown')}"
                  f" | Drums: {', '.join(levels) or 'verify after download'}")
        if args.list:
            return 0
        choice = args.choice
        if choice is None and len(charts) == 1 and song is not None:
            choice = 1
        while choice is None:
            value = input("Choose a chart number (q to cancel): ").strip()
            if value.lower() == "q":
                return 2
            if value.isdigit() and 1 <= int(value) <= len(charts):
                choice = int(value)
            else:
                print("Enter one of the displayed chart numbers.")
        if not 1 <= choice <= len(charts):
            raise ValueError("--choice is outside the displayed result range")
        chart = charts[choice - 1]
        provenance = {"provider": "Enchor", "chart": f"https://www.enchor.us/chart/{chart['md5']}",
                      "md5": chart["md5"], "charter": chart.get("charter")}
        print("\nDownloading chart ...", flush=True)
        source = download(chart, cache)
    source = source.resolve()
    if not source.exists():
        raise ValueError(f"Input does not exist: {source}")
    with tempfile.TemporaryDirectory(prefix="extract-", dir=cache) as tmp:
        if source.is_file():
            folder = Path(tmp) / "song"
            print("Unpacking chart ...", flush=True)
            if source.suffix.lower() == ".sng":
                unpack_sng(source, folder)
            elif source.suffix.lower() == ".zip":
                unpack_zip(source, folder)
            else:
                raise ValueError("Use a .sng, .zip, or extracted Clone Hero folder. Rock Band CON needs conversion first.")
            source = song_folder(folder)
        print("Converting drum charts and audio ...", flush=True)
        result = convert_song(source, args.output, args.mapping, provenance)
    report = json.loads((result / "conversion-report.json").read_text())
    print(f"\nCreated: {result}")
    for difficulty, count in report["difficulties"].items():
        print(f"  {difficulty}: {count:,} drum hits")
    for warning in report["warnings"]:
        print(f"  Note: {warning}")
    if songs_dir:
        try:
            destination = copy_song(result, songs_dir)
        except OSError as exc:
            print(f"\nSong created at {result}, but auto-copy failed: {exc}", file=sys.stderr)
            print("Your converted output is preserved. Copy it manually after resolving the issue.",
                  file=sys.stderr)
            return 1
        print(f"\nCopied to Paradiddle: {destination}")
    else:
        print("\nCopy this entire song folder into Paradiddle's Songs folder.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, URLError, configparser.Error,
            zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"\nCould not create song: {exc}", file=sys.stderr)
        raise SystemExit(1)
