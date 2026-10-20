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

from convert import clean, convert_song, folder_name
from install import configured_songs_dir, copy_song
from packages import unpack_sng, unpack_zip
from sources import download, search
from selection import parse_selection

ROOT = Path(__file__).resolve().parent
CONVERSION_ERRORS = (OSError, ValueError, RuntimeError, URLError, configparser.Error,
                     zipfile.BadZipFile, subprocess.TimeoutExpired)


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
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--choice", help="Chart number(s), e.g. 1,3,5 or 2-6 or all")
    selection.add_argument("--all", action="store_true", help="Process all listed charts; skip existing song folders")
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
        choice = "all" if args.all else args.choice
        if choice is None and len(charts) == 1 and song is not None:
            choice = "1"
        while choice is None:
            value = input("Choose chart numbers (1,3,5 or 2-6), all, or q to cancel: ").strip()
            if value.lower() == "q":
                return 2
            try:
                parse_selection(value, len(charts))
                choice = value
            except ValueError as exc:
                print(exc)
        selected = parse_selection(choice, len(charts))
        completed = skipped = failed = 0
        for index, number in enumerate(selected, 1):
            chart = charts[number - 1]
            title = clean(chart.get("name") or "")
            print(f"\n[{index}/{len(selected)}] {title}", flush=True)
            target = args.output.resolve() / folder_name(title)
            if target.exists():
                print(f"Skipped: output already exists at {target}")
                skipped += 1
                continue
            provenance = {"provider": "Enchor", "chart": f"https://www.enchor.us/chart/{chart['md5']}",
                          "md5": chart["md5"], "charter": chart.get("charter")}
            try:
                print("Downloading chart ...", flush=True)
                source = download(chart, cache)
                status = convert_input(source, cache, args, songs_dir, provenance)
                if status:
                    failed += 1
                else:
                    completed += 1
            except FileExistsError as exc:
                print(f"Skipped: {exc}")
                skipped += 1
            except CONVERSION_ERRORS as exc:
                print(f"Failed: {title}: {exc}")
                failed += 1
        print(f"\nSummary: {completed} completed, {skipped} skipped, {failed} failed.")
        return 1 if failed else 0
    return convert_input(source, cache, args, songs_dir, provenance)


def convert_input(source, cache, args, songs_dir, provenance):
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
    except CONVERSION_ERRORS as exc:
        print(f"\nCould not create song: {exc}", file=sys.stderr)
        raise SystemExit(1)
