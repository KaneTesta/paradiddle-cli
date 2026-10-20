"""Paradiddle conversion using official MIDI mappings and drum layout (GPLv3).

Timing is evaluated across merged tracks, including tempo changes and INI delay.
"""
import configparser
import json
import math
import re
import shutil
import subprocess
import tempfile
from itertools import groupby
from pathlib import Path

import mido
import imageio_ffmpeg
import soundfile as sf
import yaml

from packages import RESERVED

ASSETS = Path(__file__).resolve().parent / "vendor/PDUtilities"
DIFFICULTIES = ("Easy", "Medium", "Hard", "Expert")
AUDIO = {".ogg", ".opus", ".wav", ".flac", ".mp3"}


def clean(value: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "", re.sub(r"<[^>]*>", "", value)).strip()


def folder_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "_", clean(value))[:120].strip(". ") or "Song"
    return "_" + value if RESERVED.match(value) else value


def drum_events(mid, track, mapping, delay):
    """Return per-difficulty events, with same-tick toggles resolved first."""
    if mid.type == 2:
        raise ValueError("Asynchronous type-2 MIDI is unsupported")
    tempos = mido.MidiTrack()
    # Keep tempo events from all tracks at their absolute tick positions.
    absolute_tempos = []
    for source in mid.tracks:
        tick = 0
        for msg in source:
            tick += msg.time
            if msg.type == "set_tempo":
                absolute_tempos.append((tick, msg))
    previous = 0
    for tick, msg in sorted(absolute_tempos, key=lambda x: x[0]):
        tempos.append(msg.copy(time=tick - previous))
        previous = tick
    merged = mido.merge_tracks([tempos, track])
    absolute, tick = [], 0
    for msg in merged:
        tick += msg.time
        absolute.append((tick, msg))
    active, tempo, last_tick, seconds = set(), 500000, 0, 0.0
    events = {d: [] for d in DIFFICULTIES}
    bpm_events = [{"time": max(0.0, delay), "bpm": 120.0}]
    for tick, group in groupby(absolute, key=lambda x: x[0]):
        seconds += mido.tick2second(tick - last_tick, mid.ticks_per_beat, tempo)
        last_tick = tick
        messages = [msg for _, msg in group]
        for msg in messages:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                bpm_events.append({"time": max(0.0, seconds + delay), "bpm": mido.tempo2bpm(tempo)})
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                active.discard(getattr(msg, "note", -1))
        active.update(msg.note for msg in messages if msg.type == "note_on" and msg.velocity > 0)
        for msg in messages:
            if msg.type != "note_on" or msg.velocity <= 0:
                continue
            for difficulty in DIFFICULTIES:
                normal, toggled = [], []
                for drum, rule in mapping[difficulty.lower()].items():
                    notes = rule if isinstance(rule, list) else rule.get("notes", [])
                    # Both bundled rhythm-game maps use explicit integer notes.
                    if msg.note in notes:
                        if isinstance(rule, dict) and rule.get("toggle_note") in active:
                            toggled.append(drum)
                        elif isinstance(rule, list):
                            normal.append(drum)
                if seconds + delay < 0 and (toggled or normal):
                    raise ValueError("Negative delay places drum hits before audio; adjust the source offset")
                for drum in toggled or normal:
                    events[difficulty].append({
                        "class": f"BP_{drum}_C", "vel": msg.velocity, "loc": 0,
                        "time": round(seconds + delay, 6)})
    return events, bpm_events


def convert_song(source: Path, output: Path, mapping_kind="auto", provenance=None) -> Path:
    source, output = source.resolve(), output.resolve()
    ini = configparser.ConfigParser(interpolation=None, strict=False)
    ini.read(source / "song.ini", encoding="utf-8-sig")
    meta = dict(ini["song"]) if ini.has_section("song") else {}
    title, artist = clean(meta.get("name", source.name)), clean(meta.get("artist", "Unknown Artist"))
    target = output / folder_name(title)
    if target.exists():
        raise FileExistsError(f"Output already exists: {target}. Choose another --output folder.")
    midi_paths = [p for p in source.iterdir() if p.suffix.lower() in {".mid", ".midi"}]
    if not midi_paths:
        raise ValueError("No MIDI chart found. Convert .chart or Rock Band packages to a Clone Hero MIDI folder first.")
    midi_path = next((p for p in midi_paths if p.name.lower() == "notes.mid"), midi_paths[0])
    # Chart-authoring tools use nonstandard SysEx bytes; match official converter tolerance.
    mid = mido.MidiFile(midi_path, clip=True)
    tracks = [t for t in mid.tracks if t.name.strip().upper() == "PART DRUMS"]
    if len(tracks) != 1:
        raise ValueError("Expected exactly one PART DRUMS track in the MIDI")
    audio = sorted(p for p in source.iterdir() if p.suffix.lower() in AUDIO)
    audio = [p for p in audio if p.stem.lower() not in {"preview", "song_preview"}]
    if not audio:
        raise ValueError("No playable audio tracks found")
    if mapping_kind == "auto":
        mapping_kind = "guitarhero" if meta.get("five_lane_drums", "").lower() in {"true", "1"} else "rockband"
    map_name = "rhythm_ game_mapping_gh.yaml" if mapping_kind == "guitarhero" else "rhythm_ game_mapping.yaml"
    mapping = yaml.safe_load((ASSETS / "midi_maps" / map_name).read_text())
    delay = float(meta.get("delay", "0") or 0) / 1000
    if not math.isfinite(delay):
        raise ValueError("Invalid song.ini delay")
    events, bpms = drum_events(mid, tracks[0], mapping, delay)
    if not any(events.values()):
        raise ValueError("No supported drum notes found in any difficulty")
    instruments = json.loads((ASSETS / "drum_sets/defaultset.rlrr").read_text())["instruments"]
    names = {i["class"]: i["name"] for i in instruments}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".converting-", dir=output) as tmp:
        stage = Path(tmp) / "song"
        stage.mkdir()
        song_tracks, drum_tracks, length, used = [], [], 0.0, set()
        for path in audio:
            name = folder_name(path.stem) + ".ogg"
            if name.casefold() in used:
                raise ValueError("Audio files have colliding output names")
            used.add(name.casefold())
            result = subprocess.run(
                [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-xerror",
                 "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "2",
                 "-c:a", "libvorbis", "-q:a", "6", str(stage / name)],
                capture_output=True, text=True, timeout=600,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise ValueError(f"Audio conversion failed for {path.name}: {result.stderr[-500:]}")
            with sf.SoundFile(stage / name) as converted:
                if converted.frames == 0:
                    raise ValueError(f"Empty audio: {path.name}")
                length = max(length, len(converted) / converted.samplerate)
            (drum_tracks if re.match(r"drums?(?:_\d+)?$", path.stem, re.I) else song_tracks).append(name)
        if len(song_tracks) > 5 or len(drum_tracks) > 4:
            raise ValueError("Too many audio stems: Paradiddle supports 5 song and 4 drum tracks; downmix first")
        cover = next((p for p in source.iterdir() if p.stem.lower() in {"album", "cover"}
                      and p.suffix.lower() in {".png", ".jpg", ".jpeg"}), None)
        cover_name = "album" + cover.suffix.lower() if cover else ""
        if cover:
            shutil.copyfile(cover, stage / cover_name)
        counts = {}
        for difficulty, hits in events.items():
            if not hits:
                continue
            for hit in hits:
                hit["name"] = names[hit.pop("class")]
            counts[difficulty] = len(hits)
            data = {
                "version": 0.7, "authoringTool": "ParadiddleCLI (official ParadiddleUtilities maps)",
                "recordingMetadata": {
                    "title": title, "artist": artist,
                    "creator": clean(meta.get("charter", meta.get("frets", ""))),
                    "description": "Converted from an existing rhythm-game drum chart.",
                    "coverImagePath": cover_name, "length": max(length, hits[-1]["time"]),
                    "complexity": max(1, min(5, int(float(meta.get("diff_drums", "1")))))},
                "audioFileData": {"songTracks": song_tracks, "drumTracks": drum_tracks,
                                  "songPreview": "", "calibrationOffset": 0},
                "instruments": instruments, "events": hits, "bpmEvents": bpms}
            (stage / f"{folder_name(title)}_{difficulty}.rlrr").write_text(
                json.dumps(data, indent=2), encoding="utf-8")
        report = {"title": title, "artist": artist, "mapping": mapping_kind,
                  "delay_seconds_applied_to_notes": delay, "difficulties": counts,
                  "source": provenance or str(source),
                  "warnings": [] if drum_tracks else ["No isolated drum audio; backing track includes drums."]}
        (stage / "conversion-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        stage.rename(target)
    return target


