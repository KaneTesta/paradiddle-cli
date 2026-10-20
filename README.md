# Paradiddle Song CLI

## Installation

Install Python 3.12 with the Windows Python launcher, clone this repository,
and run `Setup.cmd` from the project folder. This creates a private `.venv`
and installs the pinned dependencies, including FFmpeg.

Double-click `Start.cmd`.
Enter the **song name**, then the **artist**. When several charts match, choose
the number beside the version you want. A single matching chart is selected automatically.
To browse an artist's songs, leave the song name blank and enter the artist.
Choose numbered songs/charts from the alphabetically sorted list. Enter `1,3,5`,
a range such as `2-6`, a combination such as `1,3-5`, or `all`. Enter `q` to cancel. Multiple
versions of a song are shown separately with their charter and drum difficulties.

After an interactive run, press **Enter** to start a fresh search or **Q** to
quit. The new search clears the previous artist, song, and selection arguments.
For batches, this prompt appears after the whole selection finishes.
`--list`, `--help`, and piped/non-interactive runs exit without a restart prompt.

Selections are processed sequentially, with a completed/skipped/failed summary.
`all` attempts every displayed chart. Once a song's output folder exists,
later versions with that folder name are skipped; choose specific chart numbers
if you prefer a particular charter. Existing output is never overwritten.
Failures do not stop the rest of the batch. Auto-copy applies to each completed
song; copy failures preserve the output and count as failed in the summary.

Finished songs appear under `ParadiddleCLI\output\SongName`.
Copy the **entire folder** into your Paradiddle `Songs` directory; audio is
required alongside the `.rlrr` chart files. The converter preserves available
difficulties and credits the original chart author.

## Automatic copying to Paradiddle

Copy `.env.example` to `.env` beside `Start.cmd`, then set your existing
Paradiddle **Songs** folder:

```dotenv
PARADIDDLE_SONGS_DIR="C:\Users\YourName\Documents\Paradiddle\Songs"
```

The CLI reads this file from its own directory, regardless of where you launch it.
Windows `%USERPROFILE%` and `~` are supported. Quotes preserve paths with spaces
or `#`. Use an absolute path; the destination must already exist.

After conversion, the complete `SongName` folder is copied there.
The original remains in `output`. Existing songs are never overwritten.
If copying fails, the CLI reports the saved output location so you can copy
it manually. A missing `.env` or an empty setting disables automatic copying.
Your `.env` is ignored by Git; only the blank `.env.example` is committed.

Tested with a separately downloaded **Turnstile - BIRDS** chart containing
Medium, Hard, and Expert difficulties. No songs, audio, or downloaded charts
are included in this repository. Files and timing were validated, but playback
in Paradiddle itself has not been tested.

## Commands

Run these from PowerShell inside the CLI folder:

```powershell
.\Start.cmd --song "BIRDS" --artist "Turnstile"
.\Start.cmd --artist "Turnstile"
.\Start.cmd --artist "Turnstile" --list
.\Start.cmd --artist "Turnstile" --choice "1,3,5-8"
.\Start.cmd --artist "Turnstile" --all
.\Start.cmd --song "HOLIDAY" --artist "Turnstile" --list
.\Start.cmd --song "HOLIDAY" --artist "Turnstile" --choice 1
.\Start.cmd --input "C:\Path\To\SongFolder"
.\Start.cmd --input "C:\Path\To\chart.sng"
.\Start.cmd --input "C:\Path\To\chart.zip" --output "C:\Path\To\Converted"
.\Start.cmd --help
```

Existing output folders are never overwritten. To reconvert a song, select
a different `--output` directory. Downloaded SNG files are cached under `cache`;
temporary extraction folders are removed when conversion finishes.

## Supported inputs and limits

- Automatic search/download: **Enchor** (public Clone Hero/YARG drum charts).
  Title and artist matching ignores case, punctuation, spaces, and accents.
  Use the full title; include version suffixes such as `(Live)` when applicable.
- Local inputs: SNG, ZIP, or a single extracted song folder containing a MIDI
  with exactly one `PART DRUMS` track and playable audio.
- `.chart`-only files and raw Rock Band CON packages are not converted directly.
  For Rock Band downloads from RhythmVerse, use the guide's C3 Tools/Nautilus
  step to produce a Clone Hero folder, then pass that folder to `--input`.
  RhythmVerse search/download is not automated in this release.
- Audio is converted to stereo OGG/Vorbis with private FFmpeg.
  Up to five song stems and four drum stems are supported.
- Automatic mapping uses `five_lane_drums` metadata to select Guitar Hero;
  otherwise the official Rock Band rhythm-game mapping is used.
  Override with `--mapping guitarhero` or `--mapping rockband` when needed.
- MIDI tempo changes and `song.ini` delay are applied. Negative delays that
  place hits before the start of audio are rejected.
- Charts can only be created when a suitable existing drum chart is available.
  This tool does not transcribe drum parts from arbitrary audio.
- Search is bounded to 5,000 results; downloads/extraction to 1 GiB.
  Website changes or inaccessible files can require adapter updates.

## Troubleshooting

- **No matching chart:** verify exact spelling and title suffixes, or obtain
  a chart manually from https://rhythmverse.co/songfiles/game.
- **No MIDI / PART DRUMS:** choose another chart or convert its source format first.
- **Output already exists:** use another output directory.
- **Audio conversion failed:** the file may be corrupt or unsupported; try another chart.
- **Network error:** check connectivity and retry. Cached downloads are retained.

Each completed song includes `conversion-report.json` with its source, mapping,
applied offset, event counts, and warnings.

## Development

Use Python 3.12 and run `Setup.cmd` before testing. The launcher also supports
an optional portable Python installation under `runtime`; this is not committed.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q cli.py convert.py packages.py sources.py install.py selection.py
```

For a fresh development environment, use Python 3.12 and
`python -m pip install -r requirements.txt`.
Tests use temporary folders; restricted environments can set `TEMP` and `TMP`
to a writable folder.

To uninstall, first preserve any wanted songs from `output`, then remove the
project folder.

## Sources and licensing

Project source is GPL-3.0; see `LICENSE` and `NOTICE.md`.

- Conversion guide: https://www.reddit.com/r/paradiddle/comments/1aebr9p/guide_how_to_convert_songs_for_paradiddle/
- Official mappings/layout and reference converter: https://github.com/emretanirgan/ParadiddleUtilities
- Windows wrapper reference: https://github.com/rrtrytcg/paradiddleTools
- SNG specification: https://github.com/mdsitton/SngFileFormat
- Chart search: https://www.enchor.us/


