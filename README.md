# Paradiddle Song CLI

Search Chorus Encore for drum charts and convert them into Paradiddle songs.
You can also convert local Clone Hero folders, SNG files, and ZIP files.

## Setup

1. Install Python 3.12 with the Windows Python launcher.
2. Clone this repository and run `Setup.cmd` to install dependencies.
3. Double-click `Start.cmd`.

Enter a song name and artist, or leave the song name blank to browse an artist's
songs. Results show the chart author and available drum difficulties.

Select a chart by number, enter several numbers (`1,3,5`), use a range (`2-6`),
or type `all`. You can combine numbers and ranges, such as `1,3-5`.
Type `q` to cancel.

After the downloads finish, press **Enter** to search again or **Q** to quit.

Songs are saved to `output\SongName` inside the CLI folder. Copy the whole song
folder into Paradiddle's `Songs` folder, or set up automatic copying below.
Each song includes its audio and the difficulties available in the source chart.

Existing output folders are skipped. If several charts have the same song name,
only the first successful conversion is saved. Choose a specific chart number
if you want a particular version. Failed downloads or conversions won't stop
the remaining songs.

## Automatic copying

Copy `.env.example` to `.env` beside `Start.cmd` and set your Paradiddle
`Songs` folder:

```dotenv
PARADIDDLE_SONGS_DIR="C:\Users\YourName\Documents\Paradiddle\Songs"
```

Use an existing folder and keep the path in quotes. `%USERPROFILE%` and `~`
are supported. Leave the setting blank to turn off automatic copying.

Converted songs stay in `output` as well. Existing songs in the destination
are never overwritten. If copying fails, the CLI shows where to find the
converted folder so you can copy it yourself.

## Commands

Run these from PowerShell inside the CLI folder:

```powershell
# Find a song
.\Start.cmd --song "BIRDS" --artist "Turnstile"

# Browse an artist, select several charts, or download all matches
.\Start.cmd --artist "Turnstile"
.\Start.cmd --artist "Turnstile" --choice "1,3,5-8"
.\Start.cmd --artist "Turnstile" --all

# List results without downloading
.\Start.cmd --artist "Turnstile" --list

# Convert a local folder or archive
.\Start.cmd --input "C:\Path\To\SongFolder"
.\Start.cmd --input "C:\Path\To\chart.sng"
.\Start.cmd --input "C:\Path\To\chart.zip" --output "C:\Path\To\Converted"

.\Start.cmd --help
```

Use a different `--output` folder to reconvert a song. Downloads are cached in
`cache`. The restart prompt is skipped for `--list`, `--help`, and piped input.

## Supported charts

- Searches use **Chorus Encore**. Enter the full title, including suffixes such
  as `(Live)`. Matching ignores case, punctuation, spaces, and accents.
- Each song needs a MIDI file with one `PART DRUMS` track and playable audio.
  `.chart`-only songs and raw Rock Band CON files need conversion first.
- For Rock Band files, follow the [conversion guide](https://www.reddit.com/r/paradiddle/comments/1aebr9p/guide_how_to_convert_songs_for_paradiddle/)
  to create a Clone Hero folder, then use `--input`. RhythmVerse downloads
  must be obtained manually.
- Audio is converted to stereo OGG/Vorbis. Paradiddle supports up to five
  backing tracks and four drum tracks.
- Drum mapping is selected from the chart's `five_lane_drums` setting.
  Use `--mapping guitarhero` or `--mapping rockband` to override it.
- MIDI tempo changes and the delay in `song.ini` are applied. Delays that put
  drum hits before the audio starts are rejected.
- Songs need an existing drum chart; the CLI cannot create one from audio alone.
- Searches are limited to 5,000 results. Downloads and extracted files have a
  1 GiB size limit.

## Troubleshooting

- **No matching chart:** check the full song title and artist, or look on
  [RhythmVerse](https://rhythmverse.co/songfiles/game).
- **No MIDI / PART DRUMS:** choose another chart or convert the source format first.
- **Output already exists:** choose another output folder with `--output`.
- **Audio conversion failed:** try another chart; the audio may be corrupt or unsupported.
- **Network error:** check your connection and retry.

Each song's `conversion-report.json` records its source, drum mapping, timing
offset, note counts, and any warnings. A copy failure is counted as failed in
the batch summary, even though the converted song remains in `output`.

## Development

Run `Setup.cmd`, then:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q cli.py convert.py packages.py sources.py install.py selection.py
```

The launcher also accepts a portable Python installation in `runtime`.
Tests use temporary folders; set `TEMP` and `TMP` if the default location
isn't writable.

## Sources and licensing

Licensed under GPL-3.0. See `LICENSE` and `NOTICE.md` for details and third-party credits.

- [Conversion guide](https://www.reddit.com/r/paradiddle/comments/1aebr9p/guide_how_to_convert_songs_for_paradiddle/)
- [ParadiddleUtilities mappings, drum layout, and reference converter](https://github.com/emretanirgan/ParadiddleUtilities)
- [paradiddleTools Windows wrapper](https://github.com/rrtrytcg/paradiddleTools)
- [SNG file format](https://github.com/mdsitton/SngFileFormat)
- [Chorus Encore](https://www.enchor.us/)
